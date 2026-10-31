"""Step 1: splitting sections into overlapping chunks."""

from telecomdocqa import chunking
from telecomdocqa.chunking import chunk_section

DOC = {"doc_id": "ts_test", "spec": "TS 99.999", "title": "Test", "topic": "architecture"}


def make_section(n_words, number="5.1", words_per_page=100):
    """A section of numbered words: w0 w1 w2 ... spread over pages."""
    lines = [(1 + i // words_per_page, f"w{i}") for i in range(n_words)]
    return {"section_number": number, "section_title": "General", "lines": lines}


def test_short_section_is_one_chunk():
    chunks = chunk_section(make_section(50), DOC, chunk_size=200, overlap=40)
    assert len(chunks) == 1
    assert chunks[0]["n_words"] == 50


def test_tiny_section_is_skipped():
    assert chunk_section(make_section(5), DOC, chunk_size=200, overlap=40) == []


def test_chunks_overlap():
    chunks = chunk_section(make_section(500), DOC, chunk_size=200, overlap=40)
    first, second = chunks[0]["text"].split(), chunks[1]["text"].split()
    assert first[-40:] == second[:40]


def test_no_tiny_last_chunk():
    # 220 words: a separate last chunk would only hold 20 new words,
    # less than the overlap, so they are added to the first chunk instead.
    chunks = chunk_section(make_section(220), DOC, chunk_size=200, overlap=40)
    assert len(chunks) == 1
    assert chunks[0]["n_words"] == 220


def test_every_word_is_covered():
    chunks = chunk_section(make_section(731), DOC, chunk_size=200, overlap=40)
    covered = set()
    for chunk in chunks:
        covered.update(chunk["text"].split())
    assert covered == {f"w{i}" for i in range(731)}


def test_chunk_metadata_and_page_range():
    chunk = chunk_section(make_section(150, words_per_page=100), DOC, chunk_size=200, overlap=40)[0]
    assert chunk["chunk_id"] == "ts_test::5.1::0"
    assert (chunk["spec"], chunk["topic"], chunk["section_number"]) == ("TS 99.999", "architecture", "5.1")
    assert (chunk["page_start"], chunk["page_end"]) == (1, 2)


def test_chunk_ids_stay_unique_when_a_section_number_repeats(monkeypatch):
    sections = [make_section(50, "4.1"), make_section(50, "4.1")]
    monkeypatch.setattr(chunking, "load_document_sections", lambda path: (["page"], sections))
    _, _, chunks = chunking.chunk_document("fake.pdf", DOC, chunk_size=200, overlap=40)
    assert [c["chunk_id"] for c in chunks] == ["ts_test::4.1::0", "ts_test::4.1::0-2"]


def test_save_and_load_chunks(tmp_path):
    chunks = chunk_section(make_section(300), DOC, chunk_size=200, overlap=40)
    path = tmp_path / "chunks.jsonl"
    chunking.save_chunks(chunks, path)
    assert chunking.load_chunks(path) == chunks
