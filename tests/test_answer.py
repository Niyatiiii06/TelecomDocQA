"""Step 4: grounded answers, citation clean-up and citation checking."""

from telecomdocqa import config
from telecomdocqa.answer import AnswerGenerator, build_messages, extract_citations, normalize_citations

from .conftest import FakeLLM


class FakePipeline:
    def __init__(self, results):
        self.results = results

    def search(self, question, top_k, filters=None, **kwargs):
        return self.results[:top_k]


def with_scores(chunks, scores):
    return [dict(c, rerank_score=s) for c, s in zip(chunks, scores)]


def test_normalize_citations():
    assert normalize_citations("A【1】 and B【2†L3-L5】.") == "A[1] and B[2]."
    assert normalize_citations("Both [1, 3].") == "Both [1][3]."


def test_extract_citations(chunks):
    citations, invalid = extract_citations("X [1]. Y [2][1]. Z [9].", chunks[:3])
    assert [c["number"] for c in citations] == [1, 2]
    assert citations[0]["section_number"] == "6.2.1"
    assert invalid == [9]   # we only gave 3 sources


def test_spec_reference_numbers_are_not_citations(chunks):
    # "TS 23.003 [19]" is reference 19 in the spec's own list, not our source 19
    text = "An IMSI as defined in TS 23.003 [19] and RFC 7542 [20] [1]."
    citations, invalid = extract_citations(text, chunks)
    assert [c["number"] for c in citations] == [1] and invalid == []


def test_a_spec_name_before_its_own_source_is_kept(chunks):
    # source 5 IS from TS 38.300, so "TS 38.300 [5]" is a real citation
    citations, _ = extract_citations("As TS 38.300 [5] says.", chunks)
    assert [c["number"] for c in citations] == [5]


def test_prompt_numbers_the_sources(chunks):
    messages = build_messages("What is the AMF?", chunks[:2])
    assert messages[0]["role"] == "system" and "ONLY the numbered sources" in messages[0]["content"]
    assert "[1] TS 23.501 §6.2.1 AMF" in messages[1]["content"]
    assert "[2] TS 23.501 §6.2.2 SMF" in messages[1]["content"]
    assert messages[1]["content"].endswith("Question: What is the AMF?")


def test_answer_with_citations(chunks):
    llm = FakeLLM("The AMF handles registration【1】.")
    result = AnswerGenerator(FakePipeline(with_scores(chunks, [3, 2, 1, 0, 0, 0])), llm).answer("What does the AMF do?")
    assert result["answer"] == "The AMF handles registration[1]."
    assert result["found_answer"] and [c["number"] for c in result["citations"]] == [1]
    assert len(llm.calls) == 1


def test_off_topic_question_is_refused_without_calling_the_llm(chunks):
    llm = FakeLLM()
    low_scores = with_scores(chunks, [config.MIN_RERANK_SCORE - 1] * len(chunks))
    result = AnswerGenerator(FakePipeline(low_scores), llm).answer("What is the best pizza in Delhi?")
    assert result["answer"] == config.NOT_FOUND_MESSAGE
    assert not result["found_answer"] and result["sources"] == []
    assert llm.calls == []   # no API call, so the model can't guess


def test_stream_answer_events(chunks):
    llm = FakeLLM("The AMF handles registration [1].")
    generator = AnswerGenerator(FakePipeline(with_scores(chunks, [3, 2, 1, 0, 0, 0])), llm)
    events = list(generator.stream_answer("What does the AMF do?"))

    names = [name for name, _ in events]
    assert names[0] == "sources" and names[-1] == "done" and "token" in names
    streamed_text = "".join(data for name, data in events if name == "token")
    assert streamed_text.strip() == "The AMF handles registration [1]."
    assert [c["number"] for c in events[-1][1]["citations"]] == [1]


def test_stream_answer_refusal(chunks):
    low_scores = with_scores(chunks, [-20.0] * len(chunks))
    events = list(AnswerGenerator(FakePipeline(low_scores), FakeLLM()).stream_answer("pizza?"))
    assert events[0] == ("sources", [])
    assert events[-1][1]["found_answer"] is False
