"""Step 3: rerank retrieved chunks with a cross-encoder.

Retrieval (step 2) is fast but rough: the embedding model turns the question
and each chunk into vectors *separately*, and BM25 only counts words. So a
chunk can rank high just because it shares words like "role" and "AMF".

A cross-encoder is slower but much more accurate: it reads the question and
the chunk *together* in one pass, so it can tell whether the chunk actually
answers the question. That's too slow to run over all 7,700 chunks, so we
only run it on the top ~20 candidates from hybrid retrieval.
"""

from telecomdocqa import config
from telecomdocqa.retrievers import chunk_to_text


class CrossEncoderReranker:
    def __init__(self, model_name=config.RERANKER_MODEL, model=None):
        self.model_name = model_name
        if model is not None:
            self.model = model  # lets tests pass in a fake model
        else:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model_name)

    def rerank(self, query, chunks, top_k=config.TOP_K):
        """Score every (query, chunk) pair and return the top_k chunks,
        best first. Each returned chunk gets a `rerank_score`."""
        if not chunks:
            return []

        pairs = [(query, chunk_to_text(chunk)) for chunk in chunks]
        scores = self.model.predict(pairs)

        reranked = []
        for chunk, score in zip(chunks, scores):
            chunk = dict(chunk)  # copy, so we don't change the caller's list
            chunk["rerank_score"] = round(float(score), 4)
            reranked.append(chunk)

        reranked.sort(key=lambda c: c["rerank_score"], reverse=True)
        return reranked[:top_k]
