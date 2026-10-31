"""Step 8: the answer cache and rate limits that protect the demo's LLM quota."""

from fastapi.testclient import TestClient

from telecomdocqa.answer import AnswerGenerator
from telecomdocqa.api import create_app
from telecomdocqa.limits import AnswerCache, RateLimiter

from .conftest import FakeLLM
from .test_api import FakePipeline, parse_sse


class FakeClock:
    def __init__(self, now=1_800_000_000.0):
        self.now = now

    def __call__(self):
        return self.now


def test_cache_key_ignores_case_and_spaces():
    assert AnswerCache.key("What is  the AMF?", None) == AnswerCache.key("what is the amf?", {})
    assert AnswerCache.key("AMF?", {"topic": "security"}) != AnswerCache.key("AMF?", None)


def test_cache_drops_least_recently_used():
    cache = AnswerCache(max_items=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")       # "a" is now more recent than "b"
    cache.put("c", 3)    # full: "b" is dropped
    assert (cache.get("a"), cache.get("b"), cache.get("c")) == (1, None, 3)


def test_rate_limiter_per_client_per_hour():
    clock = FakeClock()
    limiter = RateLimiter(per_client_per_hour=2, per_day=100, clock=clock)
    assert limiter.check("alice") is None
    assert limiter.check("alice") is None
    assert "per hour" in limiter.check("alice")
    assert limiter.check("bob") is None        # other visitors are not affected
    clock.now += 3601                          # an hour later
    assert limiter.check("alice") is None


def test_rate_limiter_daily_cap_resets_next_day():
    clock = FakeClock()
    limiter = RateLimiter(per_client_per_hour=100, per_day=2, clock=clock)
    assert limiter.check("a") is None and limiter.check("b") is None
    assert "daily" in limiter.check("c")
    clock.now += 24 * 3600
    assert limiter.check("c") is None


def make_client(chunks, per_hour=1, llm=None):
    llm = llm or FakeLLM("The AMF handles registration [1].")
    app = create_app(AnswerGenerator(FakePipeline(chunks), llm),
                     limiter=RateLimiter(per_client_per_hour=per_hour, per_day=100))
    return TestClient(app), llm


def test_repeated_question_is_cached_and_not_rate_limited(chunks):
    client, llm = make_client(chunks, per_hour=1)
    with client:
        first = client.post("/ask", json={"question": "What does the AMF do?"}).json()
        second = client.post("/ask", json={"question": "what does the AMF do?"}).json()
        third = client.post("/ask", json={"question": "What does the SMF do?"})
    assert first["cached"] is False and second["cached"] is True
    assert second["answer"] == first["answer"]
    assert len(llm.calls) == 1                 # the LLM was called only once
    assert third.status_code == 429            # a NEW question is over the limit


def test_cache_is_shared_between_ask_and_stream(chunks):
    client, llm = make_client(chunks, per_hour=5)
    with client:
        client.post("/ask", json={"question": "What does the AMF do?"})
        events = parse_sse(client.get("/ask/stream", params={"question": "What does the AMF do?"}).text)
        events_again = parse_sse(client.get("/ask/stream", params={"question": "What does the AMF do?"}).text)
    assert events[-1][0] == "done" and events[-1][1]["cached"] is True
    assert events[-1][1]["answer"] == "The AMF handles registration [1]."
    assert events_again[-1][1]["cached"] is True
    assert len(llm.calls) == 1


def test_stream_reports_rate_limit_as_an_event(chunks):
    client, _ = make_client(chunks, per_hour=1)
    with client:
        client.get("/ask/stream", params={"question": "What does the AMF do?"})
        events = parse_sse(client.get("/ask/stream", params={"question": "What does the SMF do?"}).text)
    assert events == [("error", {"detail": "You can ask 1 new questions per hour. Please try again later."})]


def test_refusals_are_not_cached(chunks):
    client, _ = make_client(chunks, per_hour=5)
    with client:
        client.post("/ask", json={"question": "What is the best pizza in Delhi?"})
        again = client.post("/ask", json={"question": "What is the best pizza in Delhi?"}).json()
    assert again["cached"] is False


def test_visitors_are_told_apart_by_forwarded_address(chunks):
    client, _ = make_client(chunks, per_hour=1)
    with client:
        a = client.post("/ask", json={"question": "Question one?"}, headers={"X-Forwarded-For": "1.1.1.1"})
        b = client.post("/ask", json={"question": "Question two?"}, headers={"X-Forwarded-For": "2.2.2.2"})
    assert a.status_code == 200 and b.status_code == 200
