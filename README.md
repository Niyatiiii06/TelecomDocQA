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

## Step 2: Hybrid retrieval (dense + BM25) with metadata filters

```bash
pip install -r requirements.txt
python -m telecomdocqa.index_builder      # embeds all chunks into ChromaDB (one time, ~5-15 min on CPU)
python -m telecomdocqa.search "What is the role of the AMF?"
python -m telecomdocqa.search "How is SUPI concealed?" --topic security
python -m telecomdocqa.search "registration procedure" --doc ts_23502 --section 4.2
python -m telecomdocqa.search "N2 interface" --mode bm25     # compare: --mode dense / hybrid
```

- **Dense retrieval:** `BAAI/bge-small-en-v1.5` embeddings stored in ChromaDB (cosine similarity).
- **BM25 keyword retrieval:** a telecom-aware tokenizer keeps terms like `n2`, `ng-ran` and `s-nssai` intact.
- **Fusion:** Reciprocal Rank Fusion (k = 60) merges the two ranked lists using ranks, not raw scores.
- **Metadata filters:** by document (`--doc`), topic (`--topic`) and section prefix (`--section 5.2` also matches 5.2.1 ...).
