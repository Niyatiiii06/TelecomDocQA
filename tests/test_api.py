"""Step 6: the FastAPI service, tested with a fake answer generator."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import RateLimitError

from telecomdocqa.answer import AnswerGenerator
from telecomdocqa.api import create_app

from .conftest import FakeLLM


class FakePipeline:
    def __init__(self, chunks):
        self.chunks = chunks
        self.last_filters = None

    def search(self, question, top_k, filters=None, **kwargs):
        self.last_filters = filters
        if "pizza" in question:
            return [dict(self.chunks[0], rerank_score=-11.0)]
        return [dict(c, rerank_score=3.0 - i) for i, c in enumerate(self.chunks[:top_k])]


class RateLimitedLLM(FakeLLM):
    def chat_stream(self, messages, **kwargs):
        request = httpx.Request("POST", "https://llm.example")
        raise RateLimitError("rate limited", response=httpx.Response(429, request=request), body=None)


@pytest.fixture
def pipeline(chunks):
    return FakePipeline(chunks)


@pytest.fixture
def client(pipeline):
    generator = AnswerGenerator(pipeline, FakeLLM("The AMF handles registration【1】 [2]."))
    with TestClient(create_app(generator)) as test_client:
        yield test_client


def parse_sse(body):
    """Turn an SSE response body into a list of (event, data)."""
    events = []
    for block in body.strip().split("\n\n"):
        name_line, data_line = block.split("\n")
        events.append((name_line.removeprefix("event: "), json.loads(data_line.removeprefix("data: "))))
    return events


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and "ts_23501" in body["documents"]


def test_search_passes_filters(client, pipeline):
    response = client.post("/search", json={"question": "What is the AMF?", "top_k": 3, "topic": "architecture", "section": "6.2"})
    assert response.status_code == 200 and len(response.json()) == 3
    assert pipeline.last_filters == {"topic": "architecture", "section": "6.2"}


def test_ask_returns_checked_citations(client):
    body = client.post("/ask", json={"question": "  What does the AMF do?  "}).json()
    assert body["question"] == "What does the AMF do?"   # whitespace trimmed
    assert body["answer"] == "The AMF handles registration[1] [2]."
    assert [c["number"] for c in body["citations"]] == [1, 2]
    assert body["found_answer"] and len(body["sources"]) > 0


def test_ask_refuses_off_topic_questions(client):
    body = client.post("/ask", json={"question": "What is the best pizza in Delhi?"}).json()
    assert body["found_answer"] is False and body["sources"] == []


@pytest.mark.parametrize("bad_request", [
    {"question": "hi"},
    {"question": "x" * 501},
    {"question": "What is the AMF?", "topic": "cooking"},
    {"question": "What is the AMF?", "doc_id": "ts_99999"},
    {"question": "What is the AMF?", "section": "5.2; DROP TABLE"},
    {},
])
def test_bad_requests_are_rejected(client, bad_request):
    assert client.post("/ask", json=bad_request).status_code == 422


def test_stream_sends_sources_tokens_then_done(client):
    response = client.get("/ask/stream", params={"question": "What does the AMF do?"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = parse_sse(response.text)
    names = [name for name, _ in events]
    assert names[0] == "sources" and names[-1] == "done" and names.count("token") >= 2
    assert [c["number"] for c in events[-1][1]["citations"]] == [1, 2]


def test_stream_reports_llm_rate_limit_as_an_event(chunks):
    generator = AnswerGenerator(FakePipeline(chunks), RateLimitedLLM())
    with TestClient(create_app(generator)) as client:
        events = parse_sse(client.get("/ask/stream", params={"question": "What does the AMF do?"}).text)
    assert events[-1][0] == "error" and "rate limit" in events[-1][1]["detail"]


def test_demo_page_is_served(client):
    response = client.get("/")
    assert response.status_code == 200 and "TelecomDocQA" in response.text
