"""Turns text into vectors (embeddings).

Texts with similar meaning get vectors that point in a similar direction,
so we can find relevant chunks even when they use different words than
the question (e.g. "handover" vs "mobility between cells").

The model runs with ONNX Runtime (through the fastembed library) instead
of PyTorch. It's the same BAAI/bge-small-en-v1.5 model, but ONNX Runtime
needs a fraction of PyTorch's memory and install size, which lets the app
run on a free server with 512 MB of RAM.
"""

from telecomdocqa import config


class Embedder:
    def __init__(self, model_name=config.EMBEDDING_MODEL):
        # Imported here so tests can run without loading the model library.
        from fastembed import TextEmbedding

        self.model_name = model_name
        self.model = TextEmbedding(model_name, cache_dir=str(config.MODEL_CACHE_DIR))

    def embed_documents(self, texts, batch_size=32, show_progress=False):
        """Embed a list of chunk texts. Returns a list of vectors (unit length,
        so cosine similarity = dot product)."""
        vectors = []
        for i, vector in enumerate(self.model.embed(texts, batch_size=batch_size), start=1):
            vectors.append(vector.tolist())
            if show_progress and i % 500 == 0:
                print(f"  embedded {i}/{len(texts)} chunks")
        return vectors

    def embed_query(self, query):
        """Embed one search query (with the prefix BGE models expect)."""
        vector = next(iter(self.model.embed([config.QUERY_PREFIX + query])))
        return vector.tolist()
