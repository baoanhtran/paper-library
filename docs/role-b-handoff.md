# Role B handoff

Role B's local implementation, tests, PDF inspection and two-model comparison are complete. The interface contract in [ROADMAP.md](../ROADMAP.md#6-interface-contract-final) is unchanged. The remaining team actions are posting the recommendation, placing the report sections in Prism and merging the code.

## Delivered files

| File | Purpose |
|---|---|
| [pdf_to_md.py](../dags/paper_lib/pdf_to_md.py) | PyMuPDF4LLM conversion, text checks, clear errors and atomic UTF-8 output. |
| [llm_metadata.py](../dags/paper_lib/llm_metadata.py) | Prompt, bounded input, local API request, JSON validation, one content retry, cleanup and targeted schema fallback. |
| [test_pdf_to_md.py](../tests/test_pdf_to_md.py), [test_llm_metadata.py](../tests/test_llm_metadata.py) | PDF tests and fake-client/real-SDK HTTP mock tests. |
| [README: LLM setup](../README.md#llm-setup) | Ollama and LM Studio setup and a plain-Python smoke example. |
| [process_paper.py](scripts/process_paper.py) | Standalone PDF-to-metadata command using the real helper functions and local configuration. |
| [benchmark_llm.py](scripts/benchmark_llm.py) | Reproducible model timings and saved metadata/errors. |
| [role-b-evaluation.md](role-b-evaluation.md) | Actual conversion results, benchmark method, quality checks and recommendation. |
| [pdf-conversion.json](examples/pdf-conversion.json) | Portable source hashes, conversion counts, timings and visual observations. |
| [model-comparison.json](examples/model-comparison.json) | Portable results for all 18 actual helper calls. |
| [qwen3b-real-metadata.json](examples/qwen3b-real-metadata.json) | Two actual 3B outputs from the real-paper comparison. |
| [4-pdf-llm.tex](sections/4-pdf-llm.tex), [7-limitations.tex](sections/7-limitations.tex) | Report sections ready to copy into Prism. |
| [sample-paper.md](examples/sample-paper.md), [gemma-metadata.json](examples/gemma-metadata.json) | Synthetic smoke fixture and historical raw-HTTP diagnostic; neither is the real-paper comparison. |
| [role-b-pr.md](role-b-pr.md) | Prepared PR title and description; no PR has been published. |
| [role-b-handoff.md](role-b-handoff.md) | Current evidence, reproduction commands and remaining team steps. |

Only the LLM setup section of the shared README was edited. A's and C's implementation files, shared requirements and the roadmap were not changed for this work. PDFs, converted Markdown, local settings and scratch benchmark files remain under the existing ignore rules.

## Results and recommendation

The full local suite reports **74 passed, 1 skipped** in 23.20 seconds. All **16 PDF tests passed**; only Airflow DAG tests were skipped. Three supplied PDFs were converted and selected pages were inspected against the originals:

| Paper | Pages | Conversion time | Markdown characters |
|---|---:|---:|---:|
| CiteArXiv, WWW 2025 | 4 | 29.5463 s | 25,391 |
| Scientific summarisation, EMNLP 2025 | 13 | 57.3645 s | 59,388 |
| LRT, SIGIR 2026 | 4 | 3.7137 s | 25,162 |

The first conversion includes library/layout-engine initialisation; all include text checks and atomic writes. Titles and complete abstracts were retained in each 8,000-character input prefix. Inspection found column interleaving, fragmented merged table headers and flattened formulas. Some EMNLP figure text describes another paper, so it can distract the summariser.

The model comparison used the actual `extract_metadata` helper and OpenAI client, three repetitions on each real-paper prefix, Q4_K_M models, an 8,192-token context and one request at a time. The laptop has an Intel i7-13620H and RTX 3050 Laptop GPU with 4 GB VRAM. Models were preloaded outside the timer, with automatic GPU offloading. Timings include client setup and the observed LM Studio schema fallback; the first also includes lazy SDK import.

| Model | Valid metadata / calls | Exact titles | All-call mean | Rounds 2-3 mean |
|---|---:|---:|---:|---:|
| Qwen 2.5 3B Instruct | 9/9 | 9/9 | 10.86 s | 8.16 s |
| Qwen 2.5 1.5B Instruct | 9/9 | 9/9 | 9.21 s | 7.24 s |

**Recommendation for this laptop: Qwen 2.5 3B Instruct Q4_K_M.** It retained CiteArXiv's dataset and graph-model contributions, which 1.5B omitted in all three runs. Agreement with the preferred NLP category was 8/9 versus 6/9; alternative valid categories are not schema errors. The extra mean time in later rounds was approximately 0.92 seconds. Some 3B SIGIR outputs still lost the "trainable" qualifier or used stronger effectiveness wording than the source's applicability claim; the inspected body labels its evaluation an Experimental Plan, so summaries need review. This three-paper NLP-only comparison is not a general ranking. The shared demo default, `qwen2.5:7b`, was not compared and remains A's configuration choice.

## Native Windows reproduction

Run PowerShell from the repository root. The existing `.venv` has the dependencies installed. To reproduce on a fresh checkout, create it first and install the pinned requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Using the environment's Python directly avoids activation and execution-policy changes. Airflow is not needed for role B. A local, ignored `.env` has been prepared with local data directories and the LM Studio endpoint/model. Do not overwrite it with `.env.example`.

Start the local model server and load the configured model, then run the [standalone one-paper command](scripts/process_paper.py) on the supplied CiteArXiv PDF:

```powershell
.\.venv\Scripts\python.exe docs/scripts/process_paper.py data/papers/2025_03_WWW_2025_CiteArxiv.pdf --markdown-dir data/smoke-markdown --output data/metadata/citearxiv.json
```

This exact invocation succeeded using the configured `.env` defaults, without base-URL or model overrides, and saved valid four-field JSON. The separate smoke Markdown directory preserves the measured benchmark files. `--markdown-dir`, `--base-url` and `--model` override `.env` defaults; `--output` is optional. Replace the PDF path to process another paper. The [README](../README.md#llm-setup) also shows the generic invocation.

For LM Studio, start the local server, load a non-thinking Qwen model and use its exact `/v1/models` identifier:

```dotenv
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=<loaded-model-identifier>
```

Do not assume a model or server remains running after the evaluation. To reproduce the measured settings, load one model at a time with an 8,192-token context, parallel requests set to one and automatic GPU offloading. Wait for loading to finish before timing. Replace `YOUR_LOADED_MODEL_ID` below, then run the same command for the other model with a different output filename:

```powershell
.\.venv\Scripts\python.exe docs/scripts/benchmark_llm.py --base-url http://localhost:1234/v1 --model YOUR_LOADED_MODEL_ID --markdown data/markdown/2025_03_WWW_2025_CiteArxiv.md data/markdown/2025_05_EMNLP_2025__Scientific_summarization.md data/markdown/2026_04_SIGIR_2026_LRT.md --runs 3 --output data/benchmarks/model-run.json
```

The script saves results after every call. Conversion and file reads are outside its timed interval. It does not load or unload models or control caching; record those conditions separately. The published comparison uses the normal helper with no extra reasoning parameter. The older Gemma diagnostic needed `reasoning_effort="none"`, which the regular helper does not send, and is not the recommended path.

The default request format is `json_object`. On the tested LM Studio version, the explicit HTTP 400 response-format rejection triggers the strict four-field `json_schema` fallback. This does not consume the one malformed-output retry. Other HTTP and connection errors propagate.

## Prism and remaining team actions

Copy the report sections to C's shared Prism project:

| Local source | Prism destination |
|---|---|
| `docs/sections/4-pdf-llm.tex` | `sections/4-pdf-llm.tex` |
| `docs/sections/7-limitations.tex` | `sections/7-limitations.tex` |

Section 4 contains an actual CiteArXiv output, the benchmark table and model choice. Section 7 records the observed extraction/summary limitations. C owns `main.tex` and the final report PDF; confirm the inputs are included and compile there. No local LaTeX compiler was available, and no Prism upload was performed.

- [x] Implement both modules without changing the shared signatures.
- [x] Pass the module/contract tests and inspect three real PDFs.
- [x] Obtain metadata through the actual helper and OpenAI client.
- [x] Compare two non-thinking models on the same real-paper prefixes and retain actual outputs.
- [x] Complete B's README section and local report-section sources.
- [ ] Post the recommendation in the group chat.
- [ ] Copy the sections into shared Prism and verify the compiled report with C.
- [ ] Commit the owned files, create a PR using the [prepared description](role-b-pr.md) and merge into `main` after checks pass.
- [ ] Announce the merge and hand A the measured model recommendation and integration notes.

The code deadline is **6 November 2026, 23:59**; the report/README deadline is **8 November 2026, 18:00**. The roadmap's definition of done includes merging into `main`, so local completion does not complete those external team steps.

Ready-to-post English group message:

> Role B's local implementation and evaluation are complete: 74 tests passed, with only Airflow tests skipped. Three real PDFs were converted and inspected. I recommend Qwen 2.5 3B Instruct Q4_K_M for the laptop: it retained the main contributions better than 1.5B, while later-round means were 8.16 s versus 7.24 s. Both returned valid metadata and exact titles in 9/9 runs. This does not compare the demo's existing 7B default. Results and actual outputs are in `docs/role-b-evaluation.md` and `docs/examples/`; report sections 4 and 7 are ready for Prism. The changes are not merged yet.
