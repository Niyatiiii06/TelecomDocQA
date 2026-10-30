"""Step 5: the metrics, as small functions that are easy to test.

Gold labels are spec SECTIONS like ("ts_23501", "6.2.1"), not chunk IDs.
If you change the chunk size, chunk IDs change but sections don't, so the
test set stays valid. A chunk counts as relevant if it is in a gold section
or one of its sub-sections.
"""

import json
import re

from telecomdocqa.retrievers import section_matches


def is_relevant(chunk, gold):
    """True if the chunk comes from one of the gold sections."""
    for doc_id, section in gold:
        if chunk["doc_id"] == doc_id and section_matches(chunk["section_number"], section):
            return True
    return False


def first_relevant_rank(results, gold):
    """Position (1, 2, 3 ...) of the first relevant chunk, or None."""
    for rank, chunk in enumerate(results, start=1):
        if is_relevant(chunk, gold):
            return rank
    return None


def recall_at_k(results, gold, k):
    """1 if a relevant chunk is in the top k results, else 0.
    (With one gold section per question this is also called "hit rate".)"""
    rank = first_relevant_rank(results, gold)
    return 1.0 if rank is not None and rank <= k else 0.0


def reciprocal_rank(results, gold):
    """1/rank of the first relevant chunk (1.0 if it's first, 0.5 if second ...),
    0 if none. Averaged over questions this is MRR."""
    rank = first_relevant_rank(results, gold)
    return 1.0 / rank if rank else 0.0


def citation_precision(citations, gold):
    """Share of the answer's citations that point to a gold section.
    None if the answer cited nothing (we report those separately).

    This is strict: a citation to a relevant section we didn't label counts
    as wrong, so the real precision can only be higher than this number.
    """
    if not citations:
        return None
    correct = sum(1 for c in citations if is_relevant(c, gold))
    return correct / len(citations)


def percentile(values, p):
    """The p-th percentile (e.g. p=95) using linear interpolation.
    p95 latency = 95% of requests were faster than this."""
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * p / 100
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] + (values[upper] - values[lower]) * fraction


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def parse_json_reply(text):
    """Get the JSON object out of an LLM reply.

    Models sometimes wrap JSON in ```json fences or add a <think>...</think>
    block first, so we remove those and take the outermost {...}.
    """
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"No JSON object in reply: {text[:200]!r}")
    return json.loads(text[start:end + 1])
