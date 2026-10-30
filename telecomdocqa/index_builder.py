"""Step 2: embed every chunk and store the vectors in ChromaDB.

Run once after step 1 (and again whenever the chunks change):
    python -m telecomdocqa.index_builder

On a laptop CPU this takes roughly 5-15 minutes for ~7,700 chunks.
"""

import json
import time

import chromadb

from telecomdocqa import config
from telecomdocqa.chunking import load_chunks
from telecomdocqa.retrievers import chunk_to_text

ADD_BATCH_SIZE = 500  # how many chunks we send to Chroma at once


def open_collection(create_new=False):
    """Open the Chroma collection on disk. With create_new=True, any old
    index is deleted first so we never mix old and new chunks."""
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    if create_new:
        existing = [c.name for c in client.list_collections()]
        if config.COLLECTION_NAME in existing:
            client.delete_collection(config.COLLECTION_NAME)
        # cosine distance, because our embeddings are normalised
        return client.create_collection(config.COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    return client.get_collection(config.COLLECTION_NAME)


def chunk_metadata(chunk):
    """The fields we store next to each vector, used for filtering."""
    return {
        "doc_id": chunk["doc_id"],
        "spec": chunk["spec"],
        "topic": chunk["topic"],
        "section_number": chunk["section_number"],
        "section_title": chunk["section_title"],
        "page_start": chunk["page_start"],
        "page_end": chunk["page_end"],
    }


def build_index(chunks, embedder, collection):
    """Embed all chunks and add them to the collection in batches."""
    texts = [chunk_to_text(c) for c in chunks]
    print(f"Embedding {len(texts)} chunks with {embedder.model_name} ...")
    vectors = embedder.embed_documents(texts, show_progress=True)

    for start in range(0, len(chunks), ADD_BATCH_SIZE):
        batch = chunks[start:start + ADD_BATCH_SIZE]
        collection.add(
            ids=[c["chunk_id"] for c in batch],
            embeddings=vectors[start:start + ADD_BATCH_SIZE],
            documents=[c["text"] for c in batch],
            metadatas=[chunk_metadata(c) for c in batch],
        )
    return collection.count()


def main():
    from telecomdocqa.embeddings import Embedder

    chunks = load_chunks(config.CHUNKS_PATH)
    embedder = Embedder()
    collection = open_collection(create_new=True)

    start_time = time.time()
    count = build_index(chunks, embedder, collection)
    minutes = (time.time() - start_time) / 60

    # Save what the index was built from, so we can spot an out-of-date index.
    info = {"embedding_model": embedder.model_name, "num_chunks": count}
    config.INDEX_INFO_PATH.write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(f"Indexed {count} chunks in {minutes:.1f} min -> {config.CHROMA_DIR}")


if __name__ == "__main__":
    main()
