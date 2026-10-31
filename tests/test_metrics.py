"""Step 5: evaluation metrics. If these are wrong, every reported number is wrong."""

import pytest

from telecomdocqa.metrics import (
    citation_precision,
    first_relevant_rank,
    is_relevant,
    mean,
    parse_json_reply,
    percentile,
    recall_at_k,
    reciprocal_rank,
)

GOLD = [["ts_23501", "6.2"]]


def chunk(doc_id, section):
    return {"doc_id": doc_id, "section_number": section}


RESULTS = [chunk("ts_23501", "5.1"), chunk("ts_23501", "6.2.1"), chunk("ts_23501", "6.20")]


def test_is_relevant_covers_subsections_only():
    assert is_relevant(chunk("ts_23501", "6.2.1"), GOLD)
    assert not is_relevant(chunk("ts_23501", "6.20"), GOLD)    # 6.20 is not under 6.2
    assert not is_relevant(chunk("ts_38300", "6.2"), GOLD)     # right section, wrong spec


def test_recall_and_reciprocal_rank():
    assert first_relevant_rank(RESULTS, GOLD) == 2
    assert recall_at_k(RESULTS, GOLD, 1) == 0.0
    assert recall_at_k(RESULTS, GOLD, 5) == 1.0
    assert reciprocal_rank(RESULTS, GOLD) == 0.5
    assert reciprocal_rank(RESULTS[:1], GOLD) == 0.0


def test_citation_precision():
    citations = [chunk("ts_23501", "6.2.4"), chunk("ts_33501", "6.2")]
    assert citation_precision(citations, GOLD) == 0.5
    assert citation_precision([], GOLD) is None   # no citations is reported separately


def test_percentile_and_mean():
    assert percentile([5, 1, 3, 2, 4], 50) == 3
    assert percentile(list(range(1, 101)), 95) == pytest.approx(95.05)
    assert percentile([], 95) is None
    assert mean([1.0, None, 0.0]) == 0.5


def test_parse_json_reply_handles_messy_llm_output():
    reply = '<think>let me check</think>Here you go:\n```json\n{"grade": "correct"}\n```'
    assert parse_json_reply(reply) == {"grade": "correct"}
    with pytest.raises(ValueError):
        parse_json_reply("no json here")
