# Retrieval evaluation (58 answerable questions)

Generated 2026-10-31 00:07. Embeddings: `BAAI/bge-small-en-v1.5`, reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2` (top 20 candidates).

| Setup | Recall@1 | Recall@5 | Recall@10 | MRR@10 | p50 latency | p95 latency |
|---|---|---|---|---|---|---|
| BM25 only | 0.47 | 0.69 | 0.76 | 0.57 | 9 ms | 16 ms |
| Dense only | 0.66 | 0.90 | 0.91 | 0.75 | 20 ms | 35 ms |
| Hybrid (RRF) | 0.57 | 0.81 | 0.90 | 0.66 | 33 ms | 42 ms |
| Hybrid + rerank | 0.72 | 0.93 | 0.97 | 0.81 | 1126 ms | 1565 ms |

**Recall@5 by topic (hybrid + rerank)**

| Topic | Recall@5 | Questions |
|---|---|---|
| architecture | 0.90 | 21 |
| procedures | 1.00 | 5 |
| radio_access | 0.90 | 20 |
| security | 1.00 | 12 |

**"Not found" threshold** (MIN_RERANK_SCORE = -1.0): unanswerable questions refused 10/10, answerable questions wrongly refused 0/58. Lowest answerable score 0.24, highest unanswerable score -2.45.
