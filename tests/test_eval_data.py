"""Checks on the evaluation set itself. A typo in a gold label silently
makes a question impossible to get right, so we test the data like code."""

import json
import re

import pytest

from telecomdocqa import config
from telecomdocqa.chunking import load_manifest

QUESTIONS = [json.loads(line) for line in open(config.EVAL_QUESTIONS_PATH, encoding="utf-8") if line.strip()]
DOC_IDS = {d["doc_id"] for d in load_manifest(config.MANIFEST_PATH)}
SECTION_RE = re.compile(r"^[A-Z0-9]{1,2}(\.\d+)*$")
REQUIRED = {"id", "question", "gold", "reference_answer", "answerable", "topic", "verified"}


def test_question_ids_are_unique():
    ids = [q["id"] for q in QUESTIONS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("q", QUESTIONS, ids=lambda q: q["id"])
def test_question_is_well_formed(q):
    assert REQUIRED <= q.keys()
    assert len(q["question"]) >= 10
    if q["answerable"]:
        assert q["gold"], "an answerable question needs at least one gold section"
        assert len(q["reference_answer"]) >= 20
        for doc_id, section in q["gold"]:
            assert doc_id in DOC_IDS, f"unknown document {doc_id}"
            assert SECTION_RE.match(section), f"bad section number {section!r}"
    else:
        assert q["gold"] == [] and q["reference_answer"] == ""


def test_set_has_both_kinds_of_question():
    assert sum(q["answerable"] for q in QUESTIONS) >= 50
    assert sum(not q["answerable"] for q in QUESTIONS) >= 10
