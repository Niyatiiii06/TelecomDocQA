"""The full retrieval pipeline: hybrid search -> cross-encoder reranking.

Later steps (answers, evaluation, the API) all use SearchPipeline, so the
retrieval logic lives in exactly one place.
"""

from telecomdocqa import config


class SearchPipeline:
    def __init__(self, retriever, reranker=None):
        self.retriever = retriever
        self.reranker = reranker

    def search(self, query, top_k=config.TOP_K, filters=None, mode="hybrid", rerank=True, n_candidates=None):
        """Return the top_k chunks for the query.

        With rerank=True we first fetch RERANK_CANDIDATES chunks, let the
        cross-encoder reorder them, and keep the best top_k.
        Each chunk keeps `retrieval_rank` (its position before reranking),
        so you can see how much the reranker moved it.
        """
        use_reranker = rerank and self.reranker is not None
        if use_reranker:
            n_candidates = max(n_candidates or config.RERANK_CANDIDATES, top_k)
        else:
            n_candidates = top_k

        candidates = self.retriever.search(query, top_k=n_candidates, filters=filters, mode=mode)
        for position, chunk in enumerate(candidates, start=1):
            chunk["retrieval_rank"] = position

        if not use_reranker:
            return candidates
        return self.reranker.rerank(query, candidates, top_k=top_k)


def load_pipeline(use_reranker=True):
    """Load everything needed for searching (indexes + models)."""
    from telecomdocqa.reranker import CrossEncoderReranker
    from telecomdocqa.search import load_retriever

    retriever = load_retriever()
    reranker = CrossEncoderReranker() if use_reranker else None
    return SearchPipeline(retriever, reranker)
