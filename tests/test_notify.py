#Discord webhook notification for a new paper.

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from paper_lib import notify

RECORD = {"filename": "a.pdf", "title": "Graph Databases", "summary": "About graphs.",
          "keywords": ["graph", "neo4j"], "category": "Databases"}


@pytest.fixture
def server():
    """Tiny local HTTP server that plays Discord. Set .status to change its answer."""
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            received.append({"body": json.loads(body), "headers": dict(self.headers)})
            self.send_response(srv.status)
            self.end_headers()
            self.wfile.write(b'{"message": "nope"}' if srv.status >= 400 else b"")

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), Handler)
    srv.status, srv.received = 204, received
    srv.url = f"http://127.0.0.1:{srv.server_port}/webhook"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv
    srv.shutdown()


def test_sends_one_message_with_all_fields(server):
    notify.notify_new_paper(server.url, RECORD)
    assert len(server.received) == 1
    sent = server.received[0]
    assert sent["headers"]["User-Agent"] != "" and "urllib" not in sent["headers"]["User-Agent"].lower()
    embed = sent["body"]["embeds"][0]
    assert "Graph Databases" in embed["title"]
    assert embed["description"] == "About graphs."
    assert {"Category": "Databases", "Keywords": "graph, neo4j"} == {f["name"]: f["value"] for f in embed["fields"]}
    assert embed["footer"]["text"] == "a.pdf"
    assert sent["body"]["allowed_mentions"] == {"parse": []}


def test_http_error_raises_with_discord_message(server):
    server.status = 404
    with pytest.raises(RuntimeError, match="404"):
        notify.notify_new_paper(server.url, RECORD)


def test_limits_respected():
    long = {"filename": "f" * 500, "title": "T" * 1000, "summary": "S " * 5000,
            "keywords": [f"keyword{i}" for i in range(500)], "category": "C" * 1000}
    embed = notify.build_payload(long)["embeds"][0]
    assert len(embed["title"]) <= 256
    assert len(embed["description"]) <= 4096
    assert all(len(f["value"]) <= 1024 and len(f["name"]) <= 256 for f in embed["fields"])
    assert len(embed["footer"]["text"]) <= 2048
    total = sum(len(embed["title"]) + len(embed["description"]) + len(embed["footer"]["text"])
                + len(f["name"]) + len(f["value"]) for f in embed["fields"])
    assert total <= 6000


def test_missing_optional_fields_do_not_crash():
    embed = notify.build_payload({"filename": "a.pdf"})["embeds"][0]
    assert embed["title"] and embed["fields"][1]["value"] == "—"


@pytest.mark.skipif(not os.environ.get("DISCORD_TEST_WEBHOOK"), reason="set DISCORD_TEST_WEBHOOK to send a real message")
def test_real_webhook():
    notify.notify_new_paper(os.environ["DISCORD_TEST_WEBHOOK"], RECORD)
