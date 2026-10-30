# TelecomDocQA

A production-style Retrieval-Augmented Generation (RAG) system for 5G technical
documentation (3GPP specifications), with hybrid retrieval, reranking, cited
answers and an evaluation harness.

> Work in progress. The full README with benchmarks comes in the final step.

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Step 1: Ingestion and chunking

1. Download the spec PDFs into `data/raw/` (see `data/raw/README.md`).
2. Run from the project root:

```bash
python -m telecomdocqa.chunking --show 2
```

This reads every PDF listed in `data/manifest.json`, removes headers, footers
and the table of contents, splits the text at 3GPP section headings, and writes
overlapping ~200-word chunks to `data/processed/chunks.jsonl`. Each chunk keeps
its document, spec number, topic, section and page range for citations and
filtering.
