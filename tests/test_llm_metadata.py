"""Role B: deterministic metadata tests; no local model or Airflow required."""
from copy import deepcopy
import json
import sys
from types import SimpleNamespace

import pytest

from paper_lib import llm_metadata


VALID = {
    "title": "A Research Paper",
    "summary": "The paper presents a data pipeline for research libraries.",
    "keywords": ["data pipelines", "research libraries"],
    "category": "Data Engineering",
}


class FakeBadRequestError(Exception):
    """Relevant public interface of the SDK's HTTP 400 exception."""
    status_code = 400


def completion(content, *, finish_reason="stop"):
    return SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=content), finish_reason=finish_reason,
    )])


@pytest.fixture
def fake_client(monkeypatch):
    """Replace the lazily imported SDK with its relevant context-manager interface."""
    class FakeClient:
        def __init__(self):
            self.responses = []
            self.calls = []
            self.options = None
            self.closed = False
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, **kwargs):
            self.calls.append(deepcopy(kwargs))
            response = self.responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.closed = True

    client = FakeClient()

    def factory(**kwargs):
        client.options = kwargs
        return client

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(
        OpenAI=factory, BadRequestError=FakeBadRequestError,
    ))
    return client


def extract(fake_client, *responses, markdown="# A Research Paper\nAbstract: a data pipeline."):
    fake_client.responses = list(responses)
    return llm_metadata.extract_metadata(markdown, "http://localhost:11434/v1", "qwen2.5:7b")


def test_valid_json_uses_local_endpoint_json_mode_and_low_temperature(fake_client):
    assert extract(fake_client, completion(json.dumps(VALID))) == VALID
    assert fake_client.options == {
        "base_url": "http://localhost:11434/v1", "api_key": "local",
        "timeout": 120.0, "max_retries": 0,
    }
    assert len(fake_client.calls) == 1
    assert fake_client.closed
    call = fake_client.calls[0]
    assert call["model"] == "qwen2.5:7b"
    assert call["response_format"] == {"type": "json_object"}
    assert 0 <= call["temperature"] <= 0.2
    assert all(category in call["messages"][0]["content"] for category in llm_metadata.CATEGORIES)
    assert "untrusted" in call["messages"][0]["content"]


def test_invalid_json_then_valid_retries_once_with_feedback(fake_client):
    assert extract(fake_client, completion("not JSON"), completion(json.dumps(VALID))) == VALID
    assert len(fake_client.calls) == 2
    assert len(fake_client.calls[1]["messages"]) == 3
    assert "previous answer was invalid" in fake_client.calls[1]["messages"][-1]["content"]


def test_invalid_json_twice_raises_value_error_and_closes_client(fake_client):
    with pytest.raises(ValueError, match="invalid after 2 attempts"):
        extract(fake_client, completion("no JSON"), completion("```json\n{}\n```"))
    assert len(fake_client.calls) == 2
    assert fake_client.closed


@pytest.mark.parametrize("field", VALID)
def test_missing_required_field_is_retried(fake_client, field):
    value = {key: item for key, item in VALID.items() if key != field}
    assert extract(fake_client, completion(json.dumps(value)), completion(json.dumps(VALID))) == VALID
    assert len(fake_client.calls) == 2


@pytest.mark.parametrize("changes", [
    {"title": None}, {"summary": 42}, {"category": ["Machine Learning"]},
    {"keywords": "airflow, llm"}, {"keywords": ["airflow", 42]},
    {"title": "  "}, {"summary": ""}, {"category": " "},
])
def test_wrong_types_or_empty_text_fail_after_two_attempts(fake_client, changes):
    response = completion(json.dumps({**VALID, **changes}))
    with pytest.raises(ValueError, match="invalid after 2 attempts"):
        extract(fake_client, response, response)
    assert len(fake_client.calls) == 2


@pytest.mark.parametrize("content", ["[]", "null", "42", '"metadata"', ""])
def test_non_object_or_empty_response_is_retried(fake_client, content):
    assert extract(fake_client, completion(content), completion(json.dumps(VALID))) == VALID
    assert len(fake_client.calls) == 2


@pytest.mark.parametrize("response", [
    completion(None), SimpleNamespace(choices=[]),
    completion(json.dumps(VALID), finish_reason="length"),
])
def test_missing_or_truncated_completion_is_retried(fake_client, response):
    assert extract(fake_client, response, completion(json.dumps(VALID))) == VALID
    assert len(fake_client.calls) == 2


def test_trim_deduplicate_fallback_and_return_only_contract_fields(fake_client):
    value = {
        "title": "  A Research Paper \n", "summary": " A concise summary.  ",
        "keywords": ["  Airflow", "airflow ", "", "  ", "LLM", "llm", "Données"],
        "category": "  Physics ", "filename": "untrusted.pdf",
    }
    assert extract(fake_client, completion(json.dumps(value))) == {
        "title": "A Research Paper", "summary": "A concise summary.",
        "keywords": ["Airflow", "LLM", "Données"], "category": "Other",
    }


@pytest.mark.parametrize("category", llm_metadata.CATEGORIES)
@pytest.mark.parametrize("variant", ["canonical", "mixed_case_with_whitespace"])
def test_category_case_is_normalized_without_retry(fake_client, category, variant):
    supplied_category = category if variant == "canonical" else f" \t{category.swapcase()}\n "
    value = {**VALID, "category": supplied_category}
    assert extract(fake_client, completion(json.dumps(value))) == {**VALID, "category": category}
    assert len(fake_client.calls) == 1


def test_only_first_8000_characters_sent_on_both_attempts(fake_client):
    source = "a" * 8_000 + "PRIVATE_TAIL_MUST_NOT_BE_SENT"
    extract(fake_client, completion("bad"), completion(json.dumps(VALID)), markdown=source)
    for call in fake_client.calls:
        paper_message = call["messages"][1]["content"]
        assert paper_message.endswith("a" * 8_000)
        assert "PRIVATE_TAIL" not in str(call)


def test_backend_error_propagates_without_content_retry(fake_client):
    failure = ConnectionError("local LLM unavailable")
    with pytest.raises(ConnectionError, match="local LLM unavailable"):
        extract(fake_client, failure)
    assert len(fake_client.calls) == 1
    assert fake_client.closed


def test_backend_json_schema_negotiation_preserves_validation_retry(fake_client):
    unsupported = FakeBadRequestError("'response_format.type' must be 'json_schema' or 'text'")
    assert extract(
        fake_client, unsupported, completion("bad JSON"), completion(json.dumps(VALID)),
    ) == VALID
    assert len(fake_client.calls) == 3
    assert [call["response_format"]["type"] for call in fake_client.calls] == [
        "json_object", "json_schema", "json_schema",
    ]
    schema = fake_client.calls[1]["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert schema["schema"]["additionalProperties"] is False
    assert set(schema["schema"]["required"]) == set(VALID)
    assert schema["schema"]["properties"] == {
        "title": {"type": "string"}, "summary": {"type": "string"},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "category": {"type": "string"},
    }
    assert fake_client.calls[0]["messages"] == fake_client.calls[1]["messages"]
    assert len(fake_client.calls[2]["messages"]) == 3
    assert fake_client.closed


def test_schema_backend_invalid_content_twice_still_stops_after_two_contents(fake_client):
    unsupported = FakeBadRequestError("unsupported response_format json_object; use json_schema")
    with pytest.raises(ValueError, match="invalid after 2 attempts"):
        extract(fake_client, unsupported, completion("bad JSON"), completion("bad again"))
    assert len(fake_client.calls) == 3
    assert fake_client.closed


@pytest.mark.parametrize("message", [
    "Model does not exist",
    "Invalid response_format json_schema: a required property is missing",
    "response_format json_object is unsupported",
])
def test_unrelated_bad_request_propagates_without_negotiation(fake_client, message):
    with pytest.raises(FakeBadRequestError, match=message):
        extract(fake_client, FakeBadRequestError(message))
    assert len(fake_client.calls) == 1
    assert fake_client.closed


def test_schema_rejection_propagates_without_further_format_attempts(fake_client):
    unsupported = FakeBadRequestError("'response_format.type' must be 'json_schema' or 'text'")
    rejected_schema = FakeBadRequestError("Model does not support structured outputs")
    with pytest.raises(FakeBadRequestError, match="Model does not support"):
        extract(fake_client, unsupported, rejected_schema)
    assert len(fake_client.calls) == 2
    assert fake_client.closed


@pytest.mark.parametrize("args", [
    ("  ", "http://localhost:11434/v1", "model"),
    (None, "http://localhost:11434/v1", "model"),
    ("paper", "", "model"), ("paper", "http://localhost:11434/v1", "  "),
])
def test_invalid_inputs_fail_before_creating_client(fake_client, args):
    with pytest.raises(ValueError):
        llm_metadata.extract_metadata(*args)
    assert fake_client.options is None


@pytest.fixture
def sdk_transport(monkeypatch):
    """Run the installed SDK and its response/error parsing over an in-memory HTTP transport."""
    openai = pytest.importorskip("openai")
    httpx = pytest.importorskip("httpx")
    real_client = openai.OpenAI
    state = SimpleNamespace(requests=[], responses=[], clients=[], sdk=openai, httpx=httpx)

    def handler(request):
        state.requests.append({
            "method": request.method,
            "url": str(request.url),
            "authorization": request.headers.get("authorization"),
            "body": json.loads(request.content),
        })
        reply = state.responses.pop(0)
        if isinstance(reply, Exception):
            raise reply
        status, body = reply
        return httpx.Response(status, json=body, request=request)

    def factory(**options):
        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        state.clients.append(http_client)
        return real_client(**options, http_client=http_client)

    monkeypatch.setattr(openai, "OpenAI", factory)
    return state


def sdk_completion(content, *, finish_reason="stop"):
    """A wire-format response, parsed into the SDK's actual ChatCompletion model."""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": "local-test-model",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": finish_reason,
        }],
    }


def test_real_sdk_serializes_json_mode_and_parses_completion(sdk_transport):
    value = {**VALID, "keywords": ["données", "LLM"]}
    sdk_transport.responses = [(200, sdk_completion(json.dumps(value, ensure_ascii=False)))]
    result = llm_metadata.extract_metadata(
        "# A Research Paper\nAbstract: données.",
        "http://local-backend.invalid/v1", "local-test-model",
    )
    assert result == value
    assert len(sdk_transport.requests) == 1
    request = sdk_transport.requests[0]
    assert request["url"] == "http://local-backend.invalid/v1/chat/completions"
    assert request["method"] == "POST"
    assert request["authorization"] == "Bearer local"
    assert request["body"]["response_format"] == {"type": "json_object"}
    assert request["body"]["model"] == "local-test-model"
    assert request["body"]["max_tokens"] == 768
    assert request["body"]["messages"][1]["content"].endswith("Abstract: données.")
    assert all(client.is_closed for client in sdk_transport.clients)


def test_real_sdk_lm_studio_error_negotiates_schema_and_keeps_content_retry(sdk_transport):
    sdk_transport.responses = [
        (400, {"error": "'response_format.type' must be 'json_schema' or 'text'"}),
        (200, sdk_completion("not JSON")),
        (200, sdk_completion(json.dumps(VALID))),
    ]
    assert llm_metadata.extract_metadata(
        "# Paper\nAn abstract about data pipelines.", "http://local-backend.invalid/v1", "test-model",
    ) == VALID
    bodies = [request["body"] for request in sdk_transport.requests]
    assert [body["response_format"]["type"] for body in bodies] == [
        "json_object", "json_schema", "json_schema",
    ]
    assert bodies[0]["messages"] == bodies[1]["messages"]
    assert bodies[1]["response_format"] == bodies[2]["response_format"]
    assert "previous answer was invalid" in bodies[2]["messages"][-1]["content"]
    assert all(client.is_closed for client in sdk_transport.clients)


def test_real_sdk_invalid_content_twice_stops_after_two_requests(sdk_transport):
    sdk_transport.responses = [
        (200, sdk_completion("not JSON")),
        (200, sdk_completion(json.dumps({**VALID, "keywords": "one, two"}))),
    ]
    with pytest.raises(ValueError, match="invalid after 2 attempts"):
        llm_metadata.extract_metadata("# Paper", "http://local-backend.invalid/v1", "test-model")
    assert len(sdk_transport.requests) == 2
    assert all(client.is_closed for client in sdk_transport.clients)


@pytest.mark.parametrize("status", [400, 401, 429, 500])
def test_real_sdk_unrelated_http_errors_propagate_without_automatic_retry(sdk_transport, status):
    sdk_transport.responses = [(status, {"error": {"message": "backend failure"}})]
    with pytest.raises(sdk_transport.sdk.APIStatusError) as caught:
        llm_metadata.extract_metadata("# Paper", "http://local-backend.invalid/v1", "test-model")
    assert caught.value.status_code == status
    assert len(sdk_transport.requests) == 1
    assert all(client.is_closed for client in sdk_transport.clients)


def test_real_sdk_timeout_propagates_without_content_retry(sdk_transport):
    sdk_transport.responses = [sdk_transport.httpx.ReadTimeout("local backend timed out")]
    with pytest.raises(sdk_transport.sdk.APITimeoutError):
        llm_metadata.extract_metadata("# Paper", "http://local-backend.invalid/v1", "test-model")
    assert len(sdk_transport.requests) == 1
    assert all(client.is_closed for client in sdk_transport.clients)
