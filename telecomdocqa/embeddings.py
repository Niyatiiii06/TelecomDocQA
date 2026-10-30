"""Turns text into vectors (embeddings) with a sentence-transformers model.

Texts with similar meaning get vectors that point in a similar direction,
so we can find relevant chunks even when they use different words than
the question (e.g. "handover" vs "mobility between cells").
"""

from telecomdocqa import config


class Embedder:
    def __init__(self, model_name=config.EMBEDDING_MODEL):
        # Imported here so the rest of the project (and tests) can run
        # without loading the big model library unless it's needed.
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts, batch_size=32, show_progress=False):
        """Embed a list of chunk texts. Returns a list of vectors."""
        vectors = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,  # unit length, so cosine similarity = dot product
            show_progress_bar=show_progress,
        )
        return vectors.tolist()

    def embed_query(self, query):
        """Embed one search query (with the prefix BGE models expect)."""
        vector = self.model.encode(config.QUERY_PREFIX + query, normalize_embeddings=True)
        return vector.tolist()
