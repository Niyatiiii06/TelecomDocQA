"""Shared test helpers ("fixtures").

The tests use small FAKE models instead of the real ones, so they:
- run in seconds, with no model downloads and no GPU,
- never call the LLM API (no API key needed, no rate limits, no cost),
- give the same result every time.
The fakes behave like the real classes (same method names), so the code
under test can't tell the difference.
"""

import hashlib
import math

import pytest

from telecomdocqa.retrievers import tokenize


def make_chunk(i, section, text, doc_id="ts_23501", spec="TS 23.501", topic="architecture", title="General"):
    return {
        "chunk_id": f"{doc_id}::{section}::{i}",
        "doc_id": doc_id,
        "spec": spec,
        "doc_title": "Test spec",
        "topic": topic,
        "section_number": section,
        "section_title": title,
        "page_start": 10 + i,
        "page_end": 10 + i,
        "text": text,
        "n_words": len(text.split()),
    }


@pytest.fixture
def chunks():
    """A tiny corpus: three specs, a few sections each."""
    return [
        make_chunk(0, "6.2.1", "The AMF terminates the N1 and N2 interfaces and handles registration and mobility management.", title="AMF"),
        make_chunk(1, "6.2.2", "The SMF handles session management and allocates the UE IP address.", title="SMF"),
        make_chunk(2, "6.2.3", "The UPF is the anchor point for mobility and forwards user plane packets.", title="UPF"),
        make_chunk(3, "5.15.2", "An S-NSSAI identifies a network slice and contains a slice service type.", title="Network slice"),
        make_chunk(4, "6.10", "A bandwidth part is a subset of the total cell bandwidth.", doc_id="ts_38300",
                   spec="TS 38.300", topic="radio_access", title="Bandwidth Adaptation"),
        make_chunk(5, "6.12.2", "The UE conceals the SUPI as a SUCI using the home network public key.", doc_id="ts_33501",
                   spec="TS 33.501", topic="security", title="Subscription concealed identifier"),
    ]


class FakeEmbedder:
    """Bag-of-words vectors: texts sharing words point in similar directions.
    Good enough to test that dense search ranks related text first."""

    model_name = "fake-embedder"
    size = 256

    def _vector(self, text):
        vector = [0.0] * self.size
        for word in tokenize(text):
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.size] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def embed_documents(self, texts, batch_size=32, show_progress=False):
        return [self._vector(t) for t in texts]

    def embed_query(self, query):
        return self._vector(query)


class FakeCrossEncoder:
    """Scores each text by how many words it shares with the question,
    minus 3, so unrelated text gets a negative score like the real model."""

    def rerank(self, query, documents):
        return [len(set(tokenize(query)) & set(tokenize(text))) - 3.0 for text in documents]


class FakeLLM:
    """Returns a fixed reply, and records what it was asked."""

    def __init__(self, reply="The AMF handles registration [1]."):
        self.reply = reply
        self.calls = []

    def chat(self, messages, **kwargs):
        self.calls.append(messages)
        return self.reply

    def chat_stream(self, messages, **kwargs):
        self.calls.append(messages)
        for word in self.reply.split(" "):
            yield word + " "


@pytest.fixture
def fake_embedder():
    return FakeEmbedder()


@pytest.fixture
def fake_cross_encoder():
    return FakeCrossEncoder()
