"""Step 6: a FastAPI service around the answer pipeline.

Endpoints:
    GET  /health       is the service up, and what is it running?
    POST /search       retrieval only (no LLM): the top chunks for a question
    POST /ask          the full answer with checked citations, as one JSON reply
    GET  /ask/stream   the same answer streamed with Server-Sent Events (SSE):
                       sources first, then the answer word by word
    GET  /             a small demo page that uses /ask/stream

Repeated questions are answered from a cache, and new questions are rate
limited, to protect the free LLM quota of the public demo (see limits.py).

Run from the project root:
    uvicorn telecomdocqa.api:app --reload
Then open http://127.0.0.1:8000 (demo) or http://127.0.0.1:8000/docs (API docs).
"""

import json
import re
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from openai import APIError, RateLimitError
from pydantic import BaseModel, Field, field_validator

from telecomdocqa import config
from telecomdocqa.chunking import load_manifest
from telecomdocqa.limits import AnswerCache, RateLimiter
from telecomdocqa.search import build_filters

# What filters can contain, read from the manifest so it always matches the data.
DOCUMENTS = load_manifest(config.MANIFEST_PATH)
DOC_IDS = {d["doc_id"] for d in DOCUMENTS}
TOPICS = {d["topic"] for d in DOCUMENTS}
SECTION_RE = re.compile(r"^[A-Z0-9]{1,2}(\.\d{1,3}){0,6}$")  # "5.2.1", "A.3", "6"


# ---------------- Request and response shapes ----------------
# Pydantic checks every request against these. A bad request gets a clear
# 422 error before it ever reaches the models.

class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500, description="A question about the 5G specs")
    doc_id: str | None = Field(None, description=f"Only search one spec: {sorted(DOC_IDS)}")
    topic: str | None = Field(None, description=f"Only search one topic: {sorted(TOPICS)}")
    section: str | None = Field(None, description="Only search a section and its sub-sections, e.g. 5.2")

    @field_validator("question")
    @classmethod
    def strip_question(cls, value):
        value = value.strip()
        if len(value) < 3:
            raise ValueError("question is too short")
        return value

    @field_validator("doc_id")
    @classmethod
    def check_doc_id(cls, value):
        if value is not None and value not in DOC_IDS:
            raise ValueError(f"unknown doc_id, use one of {sorted(DOC_IDS)}")
        return value

    @field_validator("topic")
    @classmethod
    def check_topic(cls, value):
        if value is not None and value not in TOPICS:
            raise ValueError(f"unknown topic, use one of {sorted(TOPICS)}")
        return value

    @field_validator("section")
    @classmethod
    def check_section(cls, value):
        if value is not None and not SECTION_RE.match(value):
            raise ValueError("section must look like 5.2.1 or A.3")
        return value

    def filters(self):
        return build_filters(self.doc_id, self.topic, self.section)


class SearchRequest(AskRequest):
    top_k: int = Field(config.TOP_K, ge=1, le=20)


class Source(BaseModel):
    chunk_id: str
    spec: str
    section_number: str
    section_title: str
    page_start: int
    page_end: int
    text: str
    rerank_score: float | None = None


class Citation(BaseModel):
    number: int
    spec: str
    section_number: str
    section_title: str
    page_start: int
    page_end: int


class AskResponse(BaseModel):
    question: str
    answer: str
    found_answer: bool
    citations: list[Citation]
    invalid_citations: list[int]
    sources: list[Source]
    total_seconds: float
    cached: bool = False


# ---------------- Helpers ----------------

def to_source(chunk):
    """Keep only the fields a client needs from a retrieved chunk."""
    return Source(**{field: chunk.get(field) for field in Source.model_fields}).model_dump()


def sse_event(name, data):
    """Format one Server-Sent Event: an event name and a JSON payload."""
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


DONE_FIELDS = ("answer", "found_answer", "citations", "invalid_citations", "total_seconds")


def cache_entry(sources, done):
    """The one shape both /ask and /ask/stream store in, and read from, the cache."""
    return {"sources": sources, "done": {field: done[field] for field in DONE_FIELDS}}


def client_id(http_request):
    """Who is asking, for rate limiting. Behind a hosting proxy the visitor's
    address is in the X-Forwarded-For header, not in the connection itself."""
    forwarded = http_request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return http_request.client.host if http_request.client else "unknown"


def llm_error(error):
    """Turn an LLM provider error into a clear HTTP error."""
    if isinstance(error, RateLimitError):
        return HTTPException(status_code=429, detail="The LLM provider's rate limit was reached. Try again later.")
    return HTTPException(status_code=502, detail="The LLM provider returned an error. Try again later.")


# ---------------- The app ----------------

def create_app(generator=None, limiter=None, cache=None):
    """Build the app. Tests pass in a fake generator; normally the real
    models are loaded once when the server starts, not on every request."""
    limiter = limiter or RateLimiter(config.RATE_LIMIT_PER_HOUR, config.DAILY_QUESTION_LIMIT)
    cache = cache or AnswerCache(config.ANSWER_CACHE_SIZE)

    @asynccontextmanager
    async def lifespan(app):
        if generator is None:
            from telecomdocqa.answer import load_answer_generator
            app.state.generator = load_answer_generator()
        else:
            app.state.generator = generator
        yield

    app = FastAPI(
        title="TelecomDocQA",
        description="Question answering over 3GPP 5G specifications, with cited sources.",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "documents": sorted(DOC_IDS),
            "llm_model": config.LLM_MODEL,
            "embedding_model": config.EMBEDDING_MODEL,
            "reranker_model": config.RERANKER_MODEL,
        }

    @app.post("/search", response_model=list[Source])
    def search(request: SearchRequest):
        chunks = app.state.generator.pipeline.search(
            request.question, top_k=request.top_k, filters=request.filters()
        )
        return [to_source(c) for c in chunks]

    @app.post("/ask", response_model=AskResponse)
    def ask(request: AskRequest, http_request: Request):
        key = cache.key(request.question, request.filters())
        cached = cache.get(key)
        if cached:
            return {**cached["done"], "sources": cached["sources"], "question": request.question, "cached": True}

        refusal = limiter.check(client_id(http_request))
        if refusal:
            raise HTTPException(status_code=429, detail=refusal)
        try:
            result = app.state.generator.answer(request.question, filters=request.filters())
        except APIError as error:
            raise llm_error(error)

        result["sources"] = [to_source(c) for c in result["sources"]]
        if result["found_answer"]:
            cache.put(key, cache_entry(result["sources"], result))
        return result

    @app.get("/ask/stream")
    def ask_stream(request: Annotated[AskRequest, Query()], http_request: Request):
        key = cache.key(request.question, request.filters())
        cached = cache.get(key)
        # Checked here, before streaming starts, but reported as an event:
        # a browser's EventSource can't read the message of an HTTP error.
        refusal = None if cached else limiter.check(client_id(http_request))

        def events():
            if cached:  # replay the saved answer instantly
                yield sse_event("sources", cached["sources"])
                yield sse_event("token", cached["done"]["answer"])
                yield sse_event("done", {**cached["done"], "cached": True})
                return
            if refusal:
                yield sse_event("error", {"detail": refusal})
                return

            sources = []
            try:
                for name, data in app.state.generator.stream_answer(request.question, filters=request.filters()):
                    if name == "sources":
                        data = sources = [to_source(c) for c in data]
                    if name == "done" and data["found_answer"]:
                        cache.put(key, cache_entry(sources, data))
                    yield sse_event(name, data)
            except APIError as error:
                # The response has already started, so we can't change the
                # status code anymore. We send an error event instead.
                yield sse_event("error", {"detail": llm_error(error).detail})

        return StreamingResponse(events(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get("/", include_in_schema=False)
    def demo_page():
        return FileResponse(config.STATIC_DIR / "index.html")

    return app


app = create_app()
