"""Steps 2-3: keyword, dense and hybrid retrieval, filters and reranking.

Dense search runs on a real ChromaDB index built in a temporary folder,
with the fake embedder from conftest.py.
"""

import pytest

from telecomdocqa import config, index_builder
from telecomdocqa.pipeline import SearchPipeline
from telecomdocqa.reranker import CrossEncoderReranker
from telecomdocqa.retrievers import (
    BM25Retriever,
    DenseRetriever,
    HybridRetriever,
    chroma_where,
    matches_filters,
    reciprocal_rank_fusion,
    section_matches,
    tokenize,
)


@pytest.fixture
def hybrid(chunks, fake_embedder, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHROMA_DIR", tmp_path / "chroma")
    collection = index_builder.open_collection(create_new=True)
    index_builder.build_index(chunks, fake_embedder, collection)
    return HybridRetriever(chunks, DenseRetriever(collection, fake_embedder), BM25Retriever(chunks))


def test_tokenize_keeps_telecom_terms():
    assert tokenize("How does the AMF use N2 and S-NSSAI in NG-RAN?") == ["amf", "use", "n2", "s-nssai", "ng-ran"]


def test_section_matches():
    assert section_matches("5.2", "5.2")
    assert section_matches("5.2.1", "5.2")
    assert not section_matches("5.20", "5.2")


def test_matches_filters(chunks):
    amf = chunks[0]
    assert matches_filters(amf, None)
    assert matches_filters(amf, {"doc_id": "ts_23501", "topic": "architecture", "section": "6.2"})
    assert not matches_filters(amf, {"topic": "security"})
    assert not matches_filters(amf, {"section": "6.20"})


def test_chroma_where():
    assert chroma_where(None) is None
    assert chroma_where({"section": "5.2"}) is None   # sections are filtered in Python
    assert chroma_where({"topic": "security"}) == {"topic": "security"}
    assert chroma_where({"doc_id": "ts_23501", "topic": "architecture"}) == {
        "$and": [{"doc_id": "ts_23501"}, {"topic": "architecture"}]
    }


def test_reciprocal_rank_fusion_rewards_agreement():
    fused = reciprocal_rank_fusion([[("a", 9.1), ("b", 8.0)], [("b", 0.9), ("c", 0.8)]], k=60)
    assert [chunk_id for chunk_id, _ in fused] == ["b", "a", "c"]   # "b" is in both lists
    assert fused[0][1] == pytest.approx(1 / 62 + 1 / 61)


def test_bm25_finds_exact_terms(chunks):
    results = BM25Retriever(chunks).search("S-NSSAI network slice")
    assert results[0][0] == "ts_23501::5.15.2::3"


def test_bm25_respects_filters(chunks):
    results = BM25Retriever(chunks).search("AMF registration", filters={"topic": "security"})
    assert all(chunk_id.startswith("ts_33501") for chunk_id, _ in results)


@pytest.mark.parametrize("mode", ["dense", "bm25", "hybrid"])
def test_each_mode_finds_the_right_chunk(hybrid, mode):
    results = hybrid.search("Which function allocates the UE IP address?", top_k=3, mode=mode)
    assert results[0]["section_number"] == "6.2.2"


def test_hybrid_results_carry_both_ranks(hybrid):
    top = hybrid.search("AMF registration mobility", top_k=1)[0]
    assert top["section_number"] == "6.2.1"
    assert top["dense_rank"] == 1 and top["bm25_rank"] == 1


def test_hybrid_filters(hybrid):
    results = hybrid.search("bandwidth part", top_k=5, filters={"doc_id": "ts_38300"})
    assert results and all(r["doc_id"] == "ts_38300" for r in results)
    assert hybrid.search("AMF", filters={"topic": "nonexistent"}) == []


def test_reranker_reorders_and_scores(chunks, fake_cross_encoder):
    reranker = CrossEncoderReranker(model=fake_cross_encoder)
    reranked = reranker.rerank("UE IP address session management", chunks, top_k=2)
    assert len(reranked) == 2
    assert reranked[0]["section_number"] == "6.2.2"
    assert reranked[0]["rerank_score"] >= reranked[1]["rerank_score"]
    assert "rerank_score" not in chunks[1]   # the input list is not changed


def test_pipeline_reranks_more_candidates_than_it_returns(hybrid, fake_cross_encoder):
    pipeline = SearchPipeline(hybrid, CrossEncoderReranker(model=fake_cross_encoder))
    results = pipeline.search("SUPI concealed SUCI", top_k=2, n_candidates=6)
    assert len(results) == 2
    assert results[0]["section_number"] == "6.12.2"
    assert all("retrieval_rank" in r and "rerank_score" in r for r in results)


def test_pipeline_without_reranking(hybrid, fake_cross_encoder):
    pipeline = SearchPipeline(hybrid, CrossEncoderReranker(model=fake_cross_encoder))
    results = pipeline.search("AMF", top_k=3, rerank=False)
    assert len(results) <= 3 and all("rerank_score" not in r for r in results)


def test_compact_bm25_matches_rank_bm25(chunks):
    """Our memory-saving BM25 must give the same scores as the rank_bm25 library."""
    import numpy as np
    from rank_bm25 import BM25Okapi

    from telecomdocqa.retrievers import BM25Index, chunk_to_text

    docs = [tokenize(chunk_to_text(c)) for c in chunks]
    ours, reference = BM25Index(iter(docs)), BM25Okapi(docs)
    for query in ["AMF registration", "UE IP address session", "network slice S-NSSAI", "TS 23.501", "unknownword"]:
        words = tokenize(query)
        assert np.allclose(ours.get_scores(words), reference.get_scores(words))
