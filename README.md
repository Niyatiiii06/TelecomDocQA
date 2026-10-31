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

The LLM (`openai/gpt-oss-120b` on Groq's free tier) only sees the top 8
reranked chunks, numbered [1]-[8], and must cite a number after every fact.
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

## Step 6: FastAPI service with streaming

```bash
uvicorn telecomdocqa.api:app --reload
```

Then open http://127.0.0.1:8000 for the demo page, or http://127.0.0.1:8000/docs
for interactive API documentation.

| Endpoint | What it does |
|---|---|
| `GET /health` | Service status and the models in use |
| `POST /search` | Retrieval only (no LLM): the top chunks for a question |
| `POST /ask` | The full answer with checked citations, as one JSON response |
| `GET /ask/stream` | The same answer streamed with Server-Sent Events: sources first, then the answer word by word, then the checked citations |

- **Validation:** Pydantic rejects bad requests with a clear 422 error (question length, unknown spec or topic, malformed section numbers).
- **Models load once** at startup (FastAPI lifespan), not on every request.
- **LLM errors** (e.g. the provider's rate limit) return 429 or 502 with a readable message; in a stream they arrive as an `error` event.

```bash
curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" \
     -d '{"question": "What is the role of the AMF?", "topic": "architecture"}'
curl -N "http://127.0.0.1:8000/ask/stream?question=What%20is%20a%20bandwidth%20part%3F"
```

## Step 7: Tests and continuous integration

```bash
pip install -r requirements-dev.txt
pytest          # 146 tests, about 5 seconds
ruff check .    # linting
```

The tests cover every stage: PDF cleaning and section detection, chunking,
BM25 / dense / hybrid retrieval and filters (on a real ChromaDB index in a
temporary folder), reranking, citation clean-up and checking, the evaluation
metrics, the API (validation, streaming, error handling) and the evaluation
set itself (valid gold labels, unique ids).

They use small fake models with the same interface as the real ones, so they
run in seconds with no API key, no model downloads and no PDFs. GitHub Actions
runs the linter and all tests on every push (`.github/workflows/ci.yml`).

The full evaluation (step 5) needs the PDFs, the real models and LLM API
quota, so it is run manually rather than on every push.

## Step 8: Docker and deployment

**Live demo:** hosted free on Streamlit Community Cloud (`streamlit_app.py`).
**Docker image:** the FastAPI service (`Dockerfile`), built and smoke-tested by GitHub Actions on every push.

### Running on a small free server

Free hosting gives roughly 0.5-1 GB of memory, so the app was slimmed down
without changing what it retrieves:

| Change | Effect |
|---|---|
| Models run on **ONNX Runtime** (fastembed) instead of PyTorch | Same two models; no 800 MB PyTorch install, far less memory |
| **Compact BM25** (inverted index in numpy arrays) instead of `rank_bm25` | Identical rankings on all 68 eval questions; keyword index memory 76 MB -> 23 MB; ~40x faster per query |

The whole app (without the models) peaks at about 230 MB.

### Deploying

1. Rebuild the index with the ONNX models and publish it to a free Hugging Face dataset
   (put a Hugging Face WRITE token in `.env` as `HF_TOKEN=...`):

   ```bash
   python -m telecomdocqa.index_builder
   python deploy/publish_index.py
   ```

2. On [share.streamlit.io](https://share.streamlit.io), create an app from this GitHub repository
   (main file `streamlit_app.py`, Python 3.12) and add the secret `LLM_API_KEY = "..."`.
   On first start the app downloads the index from Hugging Face.

3. To run the FastAPI service in Docker instead:

   ```bash
   docker build -t telecomdocqa .
   docker run -p 7860:7860 --env-file .env telecomdocqa       # then open http://localhost:7860
   ```

### Protecting the free LLM quota

Groq's free tier allows only about 60 questions a day, so both the API and the
demo answer repeated questions from an in-memory LRU cache, and limit new
questions to 10 per visitor per hour and 50 per day in total.
