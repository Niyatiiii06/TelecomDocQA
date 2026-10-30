"""Step 5b: evaluate the full system's answers (uses the LLM and the judge).

For every question it records:
- answerable questions: answer correctness, faithfulness, citation
  precision, invalid citations, and whether it wrongly said "not found"
- unanswerable questions: whether it correctly said "not found"
- end-to-end latency (p50 / p95)

Free API tiers have daily limits, so results are saved after EVERY question.
If the run stops, re-run with --resume and it continues where it stopped.

Run from the project root:
    python -m telecomdocqa.eval_answers --limit 5     # quick test first
    python -m telecomdocqa.eval_answers               # full run
    python -m telecomdocqa.eval_answers --resume      # continue a stopped run
"""

import argparse
import json
import time
from datetime import datetime

from telecomdocqa import config
from telecomdocqa.eval_retrieval import load_questions
from telecomdocqa.metrics import citation_precision, mean, percentile

RESULTS_PATH = config.EVAL_RESULTS_DIR / "answers.jsonl"


def evaluate_question(q, generator, judge):
    """Answer one question and grade it. Returns one result row."""
    result = generator.answer(q["question"])
    row = {
        "id": q["id"],
        "topic": q["topic"],
        "answerable": q["answerable"],
        "answer": result["answer"],
        "found_answer": result["found_answer"],
        "citations": [f"{c['spec']} §{c['section_number']}" for c in result["citations"]],
        "invalid_citations": result["invalid_citations"],
        "seconds": result["total_seconds"],
    }

    if not q["answerable"]:
        row["correct_refusal"] = not result["found_answer"]
        return row

    if not result["found_answer"]:
        # It said "not found" for a question the specs DO answer.
        row.update({"correctness": 0.0, "grade": "refused", "faithfulness": None, "citation_precision": None})
        return row

    row["citation_precision"] = citation_precision(result["citations"], q["gold"])
    faith = judge.faithfulness(result["answer"], result["sources"])
    row["faithfulness"] = faith["score"]
    row["claims"] = f"{faith['supported']}/{faith['total']}"
    grade = judge.correctness(q["question"], q["reference_answer"], result["answer"])
    row["correctness"] = grade["score"]
    row["grade"] = grade["grade"]
    row["grade_reason"] = grade["reason"]
    return row


def load_done_rows():
    if not RESULTS_PATH.exists():
        return []
    with open(RESULTS_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def summarize(rows):
    answerable = [r for r in rows if r["answerable"] and "error" not in r]
    unanswerable = [r for r in rows if not r["answerable"] and "error" not in r]
    answered = [r for r in answerable if r["found_answer"]]
    grades = [r["grade"] for r in answerable]

    return {
        "questions": len(rows),
        "errors": sum(1 for r in rows if "error" in r),
        "answer_correctness": mean([r["correctness"] for r in answerable]),
        "fully_correct": grades.count("correct"),
        "partial": grades.count("partial"),
        "incorrect": grades.count("incorrect"),
        "wrongly_refused": grades.count("refused"),
        "n_answerable": len(answerable),
        "faithfulness": mean([r["faithfulness"] for r in answered]),
        "citation_precision": mean([r["citation_precision"] for r in answered]),
        "answers_without_citations": sum(1 for r in answered if not r["citations"]),
        "invalid_citations": sum(len(r["invalid_citations"]) for r in answered),
        "refusal_accuracy": mean([1.0 if r["correct_refusal"] else 0.0 for r in unanswerable]),
        "n_unanswerable": len(unanswerable),
        "p50_seconds": percentile([r["seconds"] for r in rows if "seconds" in r], 50),
        "p95_seconds": percentile([r["seconds"] for r in rows if "seconds" in r], 95),
    }


def fmt(value, digits=2):
    return "n/a" if value is None else f"{value:.{digits}f}"


def format_report(s):
    return "\n".join([
        f"# Answer evaluation ({s['n_answerable']} answerable + {s['n_unanswerable']} unanswerable questions)",
        "",
        f"Generated {datetime.now():%Y-%m-%d %H:%M}. Answer model: `{config.LLM_MODEL}`, "
        f"judge model: `{config.JUDGE_MODEL}`.",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Answer correctness (correct = 1, partial = 0.5) | {fmt(s['answer_correctness'])} |",
        f"| Correct / partial / incorrect / wrongly refused | {s['fully_correct']} / {s['partial']} / {s['incorrect']} / {s['wrongly_refused']} |",
        f"| Faithfulness (claims supported by sources) | {fmt(s['faithfulness'])} |",
        f"| Citation precision (citations to gold sections, strict) | {fmt(s['citation_precision'])} |",
        f"| Answers with no citations | {s['answers_without_citations']} |",
        f"| Invalid (made-up) citation numbers | {s['invalid_citations']} |",
        f"| Refusal accuracy on unanswerable questions | {fmt(s['refusal_accuracy'])} |",
        f"| End-to-end latency p50 / p95 | {fmt(s['p50_seconds'], 1)} s / {fmt(s['p95_seconds'], 1)} s |",
        f"| Questions that errored | {s['errors']} |",
    ]) + "\n"


def main():
    from telecomdocqa.answer import load_answer_generator
    from telecomdocqa.judge import load_judge

    parser = argparse.ArgumentParser(description="Evaluate answers with an LLM judge.")
    parser.add_argument("--limit", type=int, help="only run the first N questions (for a quick test)")
    parser.add_argument("--resume", action="store_true", help="skip questions already in answers.jsonl")
    parser.add_argument("--delay", type=float, default=2.0, help="seconds to wait between questions (rate limits)")
    args = parser.parse_args()

    questions = load_questions()
    if args.limit:
        questions = questions[: args.limit]

    config.EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    done = load_done_rows() if args.resume else []
    done_ids = {r["id"] for r in done if "error" not in r}
    if not args.resume and RESULTS_PATH.exists():
        RESULTS_PATH.unlink()  # fresh run
    rows = [r for r in done if "error" not in r]

    generator = load_answer_generator()
    judge = load_judge()

    todo = [q for q in questions if q["id"] not in done_ids]
    print(f"{len(todo)} questions to evaluate ({len(done_ids)} already done)\n")
    for i, q in enumerate(todo, start=1):
        try:
            row = evaluate_question(q, generator, judge)
        except Exception as error:  # keep going; the row is retried on --resume
            row = {"id": q["id"], "topic": q["topic"], "answerable": q["answerable"],
                   "error": f"{type(error).__name__}: {error}"}
        rows.append(row)
        with open(RESULTS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

        status = row.get("error") or row.get("grade") or ("refused OK" if row.get("correct_refusal") else "answered (should refuse)")
        print(f"[{i}/{len(todo)}] {q['id']}: {status}")
        time.sleep(args.delay)

    summary = summarize(rows)
    report = format_report(summary)
    print("\n" + report)
    (config.EVAL_RESULTS_DIR / "answers_report.md").write_text(report, encoding="utf-8")
    if summary["errors"]:
        print("Some questions errored (often rate limits). Run again with --resume to retry them.")


if __name__ == "__main__":
    main()
