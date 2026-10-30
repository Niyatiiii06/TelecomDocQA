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

## Step 3: Cross-encoder reranking

```bash
python -m telecomdocqa.search "What is the role of the AMF?"              # hybrid + reranking
python -m telecomdocqa.search "What is the role of the AMF?" --no-rerank  # compare without it
```

Hybrid retrieval returns the top 20 candidates, then a cross-encoder
(`cross-encoder/ms-marco-MiniLM-L-6-v2`) reads the question and each candidate
together and reorders them. It's too slow to run over all chunks, but on 20
candidates it fixes cases where a chunk ranked high only because it shared
keywords with the question. Each result shows its rank before reranking.

## Step 4: Grounded answers with citations

1. Get a free API key at https://console.groq.com/keys
2. Copy `.env.example` to `.env` and paste your key into it.
3. Ask a question:

```bash
python -m telecomdocqa.answer "What is the role of the AMF?"
python -m telecomdocqa.answer "How is the SUPI protected over the air?" --topic security
python -m telecomdocqa.answer "What is the best pizza in Delhi?"   # should say "not found"
```

The LLM (`openai/gpt-oss-120b` on Groq's free tier) only sees the top 5
reranked chunks, numbered [1]-[5], and must cite a number after every fact.
Each citation is checked and mapped back to its spec, section and pages;
citations to sources that don't exist are flagged. If the best chunk's
rerank score is too low, the system answers "not found" without calling the
LLM, so it doesn't guess. Any OpenAI-compatible provider can be used by
changing `LLM_BASE_URL` and `LLM_MODEL` in `.env`.

## Step 5: Evaluation harness

68 questions (58 answerable, 10 unanswerable) with gold spec sections and
reference answers live in `data/eval/questions.jsonl` (see `data/eval/README.md`).

```bash
python -m telecomdocqa.eval_retrieval              # retrieval ablation, no LLM needed
python -m telecomdocqa.eval_answers --limit 5      # quick test of the answer evaluation
python -m telecomdocqa.eval_answers                # full run (use --resume if it stops)
```

| Area | Metrics |
|---|---|
| Retrieval | Recall@1/5/10 and MRR@10 for BM25, dense, hybrid and hybrid + rerank |
| Answers | Answer correctness vs. reference, faithfulness to sources, citation precision, made-up citations |
| Refusals | "Not found" accuracy on unanswerable questions, wrong refusals on answerable ones |
| Speed | p50 / p95 latency for search and end-to-end answers |

Correctness and faithfulness are graded by an LLM judge (`qwen/qwen3.8-27b`)
that is a different model from the answer model, to avoid self-grading bias.
Reports are saved to `data/eval/results/`.
