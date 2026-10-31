"""Step 8: the Streamlit demo page, run with Streamlit's own test runner and
a fake answer generator (no models, no index download, no LLM calls)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import telecomdocqa.answer
import telecomdocqa.remote_index
from telecomdocqa import config
from telecomdocqa.answer import AnswerGenerator

from .conftest import FakeLLM
from .test_api import FakePipeline

APP = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")


@pytest.fixture
def fake_backend(chunks, monkeypatch):
    llm = FakeLLM("The AMF handles registration [1].")
    monkeypatch.setattr(telecomdocqa.answer, "load_answer_generator", lambda: AnswerGenerator(FakePipeline(chunks), llm))
    monkeypatch.setattr(telecomdocqa.remote_index, "ensure_index", lambda: False)
    monkeypatch.setattr(config, "LLM_API_KEY", "test-key")
    yield llm
    import streamlit as st
    st.cache_resource.clear()  # each test starts with an empty cache and fresh limits


def ask(app, question):
    app.text_area(key="question").set_value(question)
    app.button[-1].click()  # the form's Ask button is the last button
    return app.run(timeout=30)


def test_page_loads(fake_backend):
    app = AppTest.from_file(APP).run(timeout=30)
    assert not app.exception
    assert app.title[0].value == "📡 TelecomDocQA"


def test_question_gets_a_cited_answer(fake_backend):
    app = ask(AppTest.from_file(APP).run(timeout=30), "What does the AMF do?")
    assert not app.exception
    assert any("The AMF handles registration [1]." in m.value for m in app.markdown)
    assert any("cited" in e.label for e in app.expander)


def test_repeated_question_comes_from_the_cache(fake_backend):
    app = ask(AppTest.from_file(APP).run(timeout=30), "What does the AMF do?")
    app = ask(app, "what does the AMF do?")
    assert any("cached" in c.value for c in app.caption)
    assert len(fake_backend.calls) == 1


def test_off_topic_question_is_refused(fake_backend):
    app = ask(AppTest.from_file(APP).run(timeout=30), "What is the best pizza in Delhi?")
    assert any(config_message in m.value for m in app.markdown
               for config_message in ["I couldn't find this in the provided 3GPP specifications."])
    assert fake_backend.calls == []


def test_bad_section_is_rejected(fake_backend):
    app = AppTest.from_file(APP).run(timeout=30)
    app.text_input[0].set_value("5.2; DROP")
    app = ask(app, "What does the AMF do?")
    assert app.warning and "section number" in app.warning[0].value


def test_missing_api_key_shows_a_clear_message(fake_backend, monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    app = AppTest.from_file(APP).run(timeout=30)
    assert not app.exception
    assert "No LLM API key" in app.error[0].value
