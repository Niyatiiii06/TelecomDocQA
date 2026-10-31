"""The live demo, hosted free on Streamlit Community Cloud.

It uses exactly the same pipeline as the FastAPI service (hybrid retrieval,
reranking, cited answers, the answer cache and the rate limits); Streamlit
only replaces the web page. On first start it downloads the prebuilt index
from Hugging Face (telecomdocqa/remote_index.py).

Run it locally:
    streamlit run streamlit_app.py
"""

import os
import re
import uuid

import streamlit as st

# On Streamlit Community Cloud, settings come from the app's "Secrets".
# Copy them into environment variables before telecomdocqa.config reads them.
# (Locally there are no Streamlit secrets; the .env file is used instead.)
try:
    for name in ("LLM_API_KEY", "INDEX_REPO"):
        if name in st.secrets:
            os.environ.setdefault(name, str(st.secrets[name]))
except Exception:
    pass

from openai import APIError  # noqa: E402

from telecomdocqa import config  # noqa: E402
from telecomdocqa.answer import source_label  # noqa: E402
from telecomdocqa.limits import AnswerCache, RateLimiter  # noqa: E402

GITHUB_URL = "https://github.com/Niyatiiii06/TelecomDocQA"
TOPICS = {
    "All topics": None,
    "Radio access (TS 38.300)": "radio_access",
    "Architecture (TS 23.501)": "architecture",
    "Procedures (TS 23.502)": "procedures",
    "Security (TS 33.501)": "security",
}
EXAMPLES = ["What is the role of the AMF?", "How is the SUPI protected over the air?", "What is a bandwidth part?"]
SECTION_RE = re.compile(r"^[A-Z0-9]{1,2}(\.\d{1,3}){0,6}$")

st.set_page_config(page_title="TelecomDocQA", page_icon="📡", layout="centered")

if not config.LLM_API_KEY:
    st.error("No LLM API key found. On Streamlit Community Cloud, open the app's Settings > Secrets and add a line "
             'like LLM_API_KEY = "gsk_..." (with the quotes), then reboot the app. Locally, put it in your .env file.')
    st.stop()


# st.cache_resource runs a function once per server and shares the result
# with every visitor: the models load once, not on every click.
@st.cache_resource(show_spinner="Starting up: downloading the index and loading the models (first visit only)...")
def load_generator():
    from telecomdocqa.answer import load_answer_generator
    from telecomdocqa.remote_index import ensure_index

    ensure_index()
    return load_answer_generator()


@st.cache_resource
def shared_limits():
    """One cache and one rate limiter for all visitors of this server."""
    return AnswerCache(config.ANSWER_CACHE_SIZE), RateLimiter(config.RATE_LIMIT_PER_HOUR, config.DAILY_QUESTION_LIMIT)


def visitor_id():
    """Who is asking, for the per-visitor limit."""
    forwarded = st.context.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if st.context.ip_address:
        return st.context.ip_address
    st.session_state.setdefault("visitor", str(uuid.uuid4()))
    return st.session_state["visitor"]


def show_sources(sources, cited_numbers):
    st.subheader("Sources")
    for number, source in enumerate(sources, start=1):
        cited = " · cited" if number in cited_numbers else ""
        with st.expander(f"[{number}] {source_label(source)}{cited}", expanded=bool(cited)):
            st.write(source["text"])


def set_question(text):
    st.session_state["question"] = text


# ---------------- The page ----------------

st.title("📡 TelecomDocQA")
st.write("Ask about 5G. Answers come only from 3GPP specifications "
         "(TS 38.300, 23.501, 23.502, 33.501) and cite their sources.")

columns = st.columns(len(EXAMPLES))
for column, example in zip(columns, EXAMPLES):
    column.button(example, on_click=set_question, args=(example,), use_container_width=True)

with st.form("ask"):
    question = st.text_area("Your question", key="question", max_chars=500,
                            placeholder="e.g. What is the role of the AMF?")
    left, right = st.columns([2, 1])
    topic = TOPICS[left.selectbox("Topic", list(TOPICS))]
    section = right.text_input("Section (optional)", placeholder="e.g. 6.2").strip()
    asked = st.form_submit_button("Ask", type="primary")

if asked:
    question = question.strip()
    if len(question) < 3:
        st.warning("Please type a question.")
        st.stop()
    if section and not SECTION_RE.match(section):
        st.warning("A section number looks like 6.2 or A.3.")
        st.stop()

    filters = {key: value for key, value in {"topic": topic, "section": section}.items() if value}
    cache, limiter = shared_limits()
    key = cache.key(question, filters)
    cached = cache.get(key)

    if cached:
        st.subheader("Answer")
        st.markdown(cached["done"]["answer"])
        st.caption("Answered instantly (cached)")
        show_sources(cached["sources"], {c["number"] for c in cached["done"]["citations"]})
        st.stop()

    refusal = limiter.check(visitor_id())
    if refusal:
        st.warning(refusal)
        st.stop()

    generator = load_generator()
    try:
        events = generator.stream_answer(question, filters=filters)
        _, sources = next(events)
        done = {}

        def answer_tokens():
            for name, data in events:
                if name == "token":
                    yield data
                elif name == "done":
                    done.update(data)

        st.subheader("Answer")
        answer_box = st.empty()
        with answer_box:
            st.write_stream(answer_tokens())  # the answer appears word by word
        answer_box.markdown(done["answer"])  # then the cleaned answer with checked citations

        cited = {c["number"] for c in done["citations"]}
        st.caption(f"Answered in {done['total_seconds']:.1f} s")
        if done["invalid_citations"]:
            st.caption(f"Warning: the model cited sources that don't exist: {done['invalid_citations']}")
        if sources:
            show_sources(sources, cited)
        if done["found_answer"]:
            cache.put(key, {"sources": sources, "done": done})
    except APIError:
        st.error("The language model service is busy or out of free quota. Please try again later.")

st.divider()
st.caption(f"Free demo: {config.RATE_LIMIT_PER_HOUR} new questions per visitor per hour, "
           f"{config.DAILY_QUESTION_LIMIT} per day in total. Repeated questions are answered from a cache. "
           f"[Source code and evaluation]({GITHUB_URL})")
