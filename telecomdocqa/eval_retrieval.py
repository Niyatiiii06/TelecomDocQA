"""Step 5a: evaluate retrieval (no LLM needed, takes a few minutes).

Compares four set-ups on the same questions (an "ablation"):
    BM25 only | dense only | hybrid (RRF) | hybrid + cross-encoder rerank
and reports Recall@1/5/10, MRR@10 and search latency for each.

It also checks the "not found" threshold (MIN_RERANK_SCORE): how well the
best rerank score separates answerable from unanswerable questions.

Run from the project root:
    python -m telecomdocqa.eval_retrieval
    python -m telecomdocqa.eval_retrieval --candidates 20 30 40   # how many chunks to rerank
"""

import argparse
import json
import time
from datetime import datetime

from telecomdocqa import config
from telecomdocqa.metrics import first_relevant_rank, mean, percentile, recall_at_k, reciprocal_rank

# (name in the report, retrieval mode, use reranker?)
SETUPS = [
    ("BM25 only", "bm25", False),
    ("Dense only", "dense", False),
    ("Hybrid (RRF)", "hybrid", False),
    ("Hybrid + rerank", "hybrid", True),
]
TOP_K = 10


def load_questions(path=config.EVAL_QUESTIONS_PATH):
    with open(path, encoding="utf-8") as f:
        questions = [json.loads(line) for line in f if line.strip()]
    unverified = sum(1 for q in questions if not q.get("verified"))
    if unverified:
        print(f"NOTE: {unverified} of {len(questions)} questions are not marked as verified yet.\n")
    return questions


def evaluate_setup(pipeline, questions, mode, rerank, n_candidates=None):
    """Run every answerable question through one set-up."""
    rows = []
    for q in questions:
        start = time.perf_counter()
        results = pipeline.search(q["question"], top_k=TOP_K, mode=mode, rerank=rerank, n_candidates=n_candidates)
        seconds = time.perf_counter() - start
        rows.append({
            "id": q["id"],
            "topic": q["topic"],
            "first_relevant_rank": first_relevant_rank(results, q["gold"]),
            "recall@1": recall_at_k(results, q["gold"], 1),
            "recall@5": recall_at_k(results, q["gold"], 5),
            "recall@8": recall_at_k(results, q["gold"], 8),
            "recall@10": recall_at_k(results, q["gold"], 10),
            "rr": reciprocal_rank(results, q["gold"]),
            "seconds": seconds,
            "top_results": [f"{r['doc_id']} §{r['section_number']}" for r in results[:5]],
        })
    return rows


def summarize(rows):
    return {
        "recall@1": mean([r["recall@1"] for r in rows]),
        "recall@5": mean([r["recall@5"] for r in rows]),
        "recall@8": mean([r["recall@8"] for r in rows]),
        "recall@10": mean([r["recall@10"] for r in rows]),
        "mrr@10": mean([r["rr"] for r in rows]),
        "p50_ms": percentile([r["seconds"] for r in rows], 50) * 1000,
        "p95_ms": percentile([r["seconds"] for r in rows], 95) * 1000,
    }


def check_threshold(pipeline, questions):
    """Best rerank score per question, split by answerable / unanswerable."""
    scores = {"answerable": [], "unanswerable": []}
    for q in questions:
        results = pipeline.search(q["question"], top_k=1, rerank=True)
        best = results[0]["rerank_score"] if results else float("-inf")
        scores["answerable" if q["answerable"] else "unanswerable"].append((q["id"], best))

    threshold = config.MIN_RERANK_SCORE
    correct_refusals = sum(1 for _, s in scores["unanswerable"] if s < threshold)
    false_refusals = sum(1 for _, s in scores["answerable"] if s < threshold)
    return {
        "threshold": threshold,
        "unanswerable_refused": f"{correct_refusals}/{len(scores['unanswerable'])}",
        "answerable_wrongly_refused": f"{false_refusals}/{len(scores['answerable'])}",
        "lowest_answerable_score": min(s for _, s in scores["answerable"]),
        "highest_unanswerable_score": max(s for _, s in scores["unanswerable"]),
        "scores": scores,
    }


def format_report(summaries, topic_recall, threshold_info, n_questions):
    lines = [
        f"# Retrieval evaluation ({n_questions} answerable questions)",
        "",
        f"Generated {datetime.now():%Y-%m-%d %H:%M}. Embeddings: `{config.EMBEDDING_MODEL}`, "
        f"reranker: `{config.RERANKER_MODEL}` (top {config.RERANK_CANDIDATES} candidates).",
        "",
        "| Setup | Recall@1 | Recall@5 | Recall@10 | MRR@10 | p50 latency | p95 latency |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, s in summaries.items():
        lines.append(
            f"| {name} | {s['recall@1']:.2f} | {s['recall@5']:.2f} | {s['recall@10']:.2f} | "
            f"{s['mrr@10']:.2f} | {s['p50_ms']:.0f} ms | {s['p95_ms']:.0f} ms |"
        )
    lines += ["", "**Recall@5 by topic (hybrid + rerank)**", "", "| Topic | Recall@5 | Questions |", "|---|---|---|"]
    for topic, (value, count) in topic_recall.items():
        lines.append(f"| {topic} | {value:.2f} | {count} |")
    t = threshold_info
    lines += [
        "",
        f"**\"Not found\" threshold** (MIN_RERANK_SCORE = {t['threshold']}): "
        f"unanswerable questions refused {t['unanswerable_refused']}, "
        f"answerable questions wrongly refused {t['answerable_wrongly_refused']}. "
        f"Lowest answerable score {t['lowest_answerable_score']:.2f}, "
        f"highest unanswerable score {t['highest_unanswerable_score']:.2f}.",
    ]
    return "\n".join(lines) + "\n"


def compare_candidates(pipeline, answerable, counts):
    """Experiment: how many hybrid results should the reranker see?
    More candidates = more chances to find the right chunk, but slower."""
    lines = [
        "| Chunks reranked | Recall@1 | Recall@5 | Recall@8 | Recall@10 | MRR@10 | p50 latency | p95 latency |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for n in counts:
        print(f"Evaluating: rerank {n} candidates ...")
        s = summarize(evaluate_setup(pipeline, answerable, "hybrid", True, n_candidates=n))
        lines.append(
            f"| {n} | {s['recall@1']:.2f} | {s['recall@5']:.2f} | {s['recall@8']:.2f} | {s['recall@10']:.2f} | "
            f"{s['mrr@10']:.2f} | {s['p50_ms']:.0f} ms | {s['p95_ms']:.0f} ms |"
        )
    return "# Experiment: number of chunks reranked\n\n" + "\n".join(lines) + "\n"


def main():
    from telecomdocqa.pipeline import load_pipeline

    parser = argparse.ArgumentParser(description="Evaluate retrieval.")
    parser.add_argument("--candidates", type=int, nargs="+",
                        help="only run the experiment comparing these numbers of reranked chunks")
    args = parser.parse_args()

    questions = load_questions()
    answerable = [q for q in questions if q["answerable"]]
    pipeline = load_pipeline()

    if args.candidates:
        report = compare_candidates(pipeline, answerable, args.candidates)
        print("\n" + report)
        config.EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        (config.EVAL_RESULTS_DIR / "experiment_candidates.md").write_text(report, encoding="utf-8")
        return

    all_rows, summaries = {}, {}
    for name, mode, rerank in SETUPS:
        print(f"Evaluating: {name} ...")
        rows = evaluate_setup(pipeline, answerable, mode, rerank)
        all_rows[name] = rows
        summaries[name] = summarize(rows)

    # Recall@5 per topic for the full pipeline
    final_rows = all_rows["Hybrid + rerank"]
    topic_recall = {}
    for topic in sorted({r["topic"] for r in final_rows}):
        values = [r["recall@5"] for r in final_rows if r["topic"] == topic]
        topic_recall[topic] = (mean(values), len(values))

    print("Checking the 'not found' threshold ...")
    threshold_info = check_threshold(pipeline, questions)

    report = format_report(summaries, topic_recall, threshold_info, len(answerable))
    print("\n" + report)

    misses = [r for r in final_rows if not r["recall@5"]]
    if misses:
        print("Questions where hybrid + rerank missed the gold section in the top 5:")
        for r in misses:
            print(f"  {r['id']}: got {r['top_results'][:3]}")

    config.EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (config.EVAL_RESULTS_DIR / "retrieval_report.md").write_text(report, encoding="utf-8")
    details = {"summaries": summaries, "threshold": threshold_info, "per_question": all_rows}
    (config.EVAL_RESULTS_DIR / "retrieval_details.json").write_text(json.dumps(details, indent=2), encoding="utf-8")
    print(f"\nSaved to {config.EVAL_RESULTS_DIR}")


if __name__ == "__main__":
    main()
