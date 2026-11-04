# Role B evaluation

Observed on 4 November 2026. The PDF and LLM helpers now run on the three supplied research papers. This evaluation covers role B; the scheduled Airflow workflow and C's storage, HTML and Discord modules require their owners' integration checks.

## Evidence and setup

- [Complete comparison](examples/model-comparison.json): all 18 observed outputs, timings, source hashes, prompt and manual review notes.
- [Two real-paper examples](examples/qwen3b-real-metadata.json): exact Qwen 3B metadata returned through `extract_metadata` and the installed OpenAI Python client.
- [Conversion evidence](examples/pdf-conversion.json): source/file/text hashes, counts, timings and selected-page visual observations.
- [Reproduction script](scripts/benchmark_llm.py) and [handoff commands](role-b-handoff.md).

The development laptop has an Intel Core i7-13620H, RTX 3050 Laptop GPU with 4 GB VRAM, and approximately 40 GB RAM. Software: Windows 11, Python 3.12.6, LM Studio 0.4.26+4, PyMuPDF/PyMuPDF4LLM 2.1 and OpenAI client 2.54.0.

Both models used Q4_K_M weights, an 8,192-token context, automatic GPU placement and one prediction at a time. One model was loaded at a time. Each saw the same first 8,000 characters of the same three Markdown documents, in the same order, for three rounds. Temperature was 0.1 and the completion limit was 768 tokens. The production helper made the requests, including its narrowly targeted `json_object` to `json_schema` negotiation for LM Studio. No reasoning override or alternate inference implementation was used.

PDF conversion and model loading were outside the LLM timing interval. Each model's first timed call includes lazy SDK import and client setup. Later calls still include client setup, HTTP format negotiation and any validation retry. No forced model, OS or prompt-cache reset was performed. The repeated-round mean below uses rounds 2 and 3, six calls per model; it is not an independently controlled warm-GPU benchmark.

## PDF conversion

| Supplied paper | Pages | Conversion seconds | Markdown characters |
|---|---:|---:|---:|
| CiteArXiv, WWW 2025 | 4 | 29.55 | 25,391 |
| Beyond the Scientific Document, EMNLP 2025 | 13 | 57.36 | 59,388 |
| Graph-Enhanced Sentence Retrieval, SIGIR 2026 | 4 | 3.71 | 25,162 |

Each duration includes native-text checks, conversion and atomic UTF-8 output. The first conversion also includes converter/layout-engine startup. The difference between these three timings should not be interpreted as a controlled comparison of PDF layouts.

All three outputs retained their titles and complete abstracts within the 8,000-character prefix. Selected source pages were rendered and visually compared with the Markdown:

- **CiteArXiv, pages 1 and 3:** the first page interleaves two columns, placing introduction text under the Abstract heading. Inspected table labels and numbers survived; complex equations lost layout and some symbols.
- **EMNLP, pages 1, 3 and 5:** the title and abstract order survived. A diagram's illustrative summary of another paper enters the prefix. Table values survived in inspected cells, while spanning headers split into fragments. Fraction, summation and subscript layout degraded.
- **SIGIR, pages 1–3:** the introduction continuation appears before the actual abstract. Algorithm text remains but becomes a flattened table. Equations lose mathematical layout.

There were 8, 10 and 7 replacement glyphs respectively in the full outputs, with none in the prefixes used by the models. This does not establish that every other symbol is correct. Source PDFs and full converted text remain local under `data/`.

## Model comparison

| Model | Validated helper calls | Exact titles | Mean, all 9 calls | Mean, repeated rounds | Preferred NLP category |
|---|---:|---:|---:|---:|---:|
| Qwen2.5 1.5B Instruct | 9/9 | 9/9 | 9.21 s | 7.24 s | 6/9 |
| Qwen2.5 3B Instruct | 9/9 | 9/9 | 10.86 s | 8.16 s | 8/9 |

“Validated” means the helper returned its four-field contract after parsing, validation and cleanup. Raw first-response JSON validity was not instrumented separately. All titles exactly matched the reference titles checked against the supplied papers.

Natural Language Processing was the manually preferred category because all three papers primarily concern summarization. This is a subject-label preference, not an independent gold benchmark. The 3B model's other response used the broader Machine Learning label for EMNLP. The 1.5B model labelled that paper Data Engineering in all three rounds.

Manual review of all 18 summaries found a useful quality difference:

- **1.5B:** every CiteArXiv summary focused on background and omitted both the new citation-enriched dataset and the proposed graph model. Round 2 also turned the stated absence of large citation-enriched datasets into a claim that CL-SciSumm provides such datasets. A SIGIR summary inferred that the model was trained on all five languages more strongly than the prefix establishes.
- **3B:** every CiteArXiv summary captured both contributions. EMNLP summaries retained the graph/citation approach, sometimes including the loss or attention mechanism. However, SIGIR round 2 shortened “3.2M trainable parameters” to “3.2M parameters”, losing a material qualifier. Another summary used stronger effectiveness wording than the prefix's applicability wording; the inspected paper body labels its evaluation an Experimental Plan, so experimental status still needs checking.

WWW and EMNLP performance statements in the 3B outputs are supported by their supplied prefixes. They are paper-reported claims, not independent replications. Both models can return correct JSON while omitting, simplifying or over-interpreting information.

## Recommendation and limits

Use **Qwen2.5-3B-Instruct Q4_K_M for development on this laptop**. It preserved the main contributions more reliably at an observed extra 0.92 seconds per repeated-round call. The local LM Studio model key is `qwen2.5-3b-instruct`; use the exact loaded server identifier in `LLM_MODEL`.

The three inputs are related NLP papers, each repeated three times. They are not nine independent papers, and this small, unblinded check does not establish general accuracy across the category list. Generated metadata still needs review, particularly parameter-count qualifiers, claims of completed experiments and illustrative text embedded in figures. The first-character prefix may omit decisive later sections.

A's shared demo default remains `qwen2.5:7b`; that model and the demo machine were not part of this comparison. A should perform its integration and hardware checks before changing the deployment setting or quoting these laptop timings.

## Verification and remaining team work

The final available suite reports **74 passed, 1 skipped** in 23.20 seconds. The skip is the Airflow DAG test module, which is expected on a role B machine. All 16 PDF tests ran, including source preservation when a valid PDF has the same resolved path as its intended Markdown output. LLM tests include fake-client validation cases and real SDK requests through an HTTP mock transport; the real-paper comparison additionally exercised the live local endpoint. `pip check` reports no broken requirements.

The standalone [process_paper.py](scripts/process_paper.py) also completed the real CiteArXiv PDF-to-metadata chain using the local `.env` configuration. Its JSON is saved locally at `data/metadata/citearxiv.json`. A separate negative check confirmed that asking this CLI to write its JSON over the source PDF is rejected without changing the source bytes.

Role B's local implementation, conversion checks, two-model comparison, README and report-section sources are ready for review. The group-chat recommendation, shared Prism upload/compilation and GitHub commit/PR/merge still need the team's handoff. No external publication or message is claimed here.
