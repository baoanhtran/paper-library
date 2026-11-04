# Suggested PR title

Implement PDF conversion and validated local LLM metadata extraction

# Suggested PR description

Replace role B's two pipeline stubs with PyMuPDF4LLM conversion and metadata extraction through a local OpenAI-compatible endpoint. Textless, corrupt and locked PDFs fail clearly; Markdown output is written atomically. Metadata uses a bounded excerpt, JSON parsing, one invalid-output retry, field validation and light cleanup. A narrowly targeted schema fallback supports LM Studio's explicit JSON-format rejection while other backend errors propagate.

Add module tests, an actual-SDK HTTP test layer, a reproducible model benchmark, observed real-paper outputs, LLM setup instructions and report sections 4 and 7. On three supplied papers, both tested Qwen models completed 9/9 validated calls; Qwen 3B retained contributions better than 1.5B at a repeated-round mean of 8.16 versus 7.24 seconds per call. The evaluation records conversion and summary limitations as well as successful results.

Validation: **74 passed, 1 skipped** (Airflow unavailable); all 16 PDF tests executed; `pip check` passed. The live comparison used the production helper against local LM Studio with matching prefixes and settings. The standalone `process_paper.py` CLI completed a real PDF-to-metadata run, and source/output collision checks preserve the input PDF. See [evaluation evidence](role-b-evaluation.md).

The helper signatures remain those in ROADMAP section 6. Full DAG integration belongs to A, and the shared Prism report still needs the team's upload and compilation.
