# Retrieval evaluation (58 answerable questions)

Generated 2026-10-31 18:24. Embeddings: `BAAI/bge-small-en-v1.5`, reranker: `Xenova/ms-marco-MiniLM-L-6-v2` (top 20 candidates).

| Setup | Recall@1 | Recall@5 | Recall@10 | MRR@10 | p50 latency | p95 latency |
|---|---|---|---|---|---|---|
| BM25 only | 0.47 | 0.69 | 0.76 | 0.57 | 2 ms | 4 ms |
| Dense only | 0.66 | 0.90 | 0.91 | 0.75 | 11 ms | 13 ms |
| Hybrid (RRF) | 0.57 | 0.81 | 0.88 | 0.66 | 14 ms | 18 ms |
| Hybrid + rerank | 0.72 | 0.93 | 0.97 | 0.81 | 1431 ms | 2047 ms |

**Recall@5 by topic (hybrid + rerank)**

| Topic | Recall@5 | Questions |
|---|---|---|
| architecture | 0.90 | 21 |
| procedures | 1.00 | 5 |
| radio_access | 0.90 | 20 |
| security | 1.00 | 12 |

**"Not found" threshold** (MIN_RERANK_SCORE = -1.0): unanswerable questions refused 10/10, answerable questions wrongly refused 0/58. Lowest answerable score 0.24, highest unanswerable score -2.45.
