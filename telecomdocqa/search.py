"""Try the retriever from the command line.

Examples (run from the project root):
    python -m telecomdocqa.search "What does the AMF do?"
    python -m telecomdocqa.search "How is SUPI concealed?" --topic security
    python -m telecomdocqa.search "registration procedure" --doc ts_23502 --section 4.2
    python -m telecomdocqa.search "N2 interface" --mode bm25
"""

import argparse
import json

from telecomdocqa import config
from telecomdocqa.chunking import load_chunks
from telecomdocqa.retrievers import BM25Retriever, DenseRetriever, HybridRetriever


def load_retriever():
    """Load chunks, the BM25 index and the Chroma index, ready for searching.
    Later steps (the API, the evaluation) reuse this function."""
    from telecomdocqa.embeddings import Embedder
    from telecomdocqa.index_builder import open_collection

    chunks = load_chunks(config.CHUNKS_PATH)
    collection = open_collection()

    if collection.count() != len(chunks):
        print(f"WARNING: index has {collection.count()} chunks but chunks.jsonl has {len(chunks)}. "
              "Re-run: python -m telecomdocqa.index_builder")

    info = json.loads(config.INDEX_INFO_PATH.read_text(encoding="utf-8"))
    embedder = Embedder(info["embedding_model"])  # same model the index was built with

    dense = DenseRetriever(collection, embedder)
    bm25 = BM25Retriever(chunks)
    return HybridRetriever(chunks, dense, bm25)


def build_filters(doc_id=None, topic=None, section=None):
    """Only keep the filters that were actually given."""
    filters = {"doc_id": doc_id, "topic": topic, "section": section}
    return {key: value for key, value in filters.items() if value}


def preview(text, limit=250):
    """Shorten text to about `limit` characters without cutting a word in half."""
    text = text.replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + " ..."


def print_results(results):
    if not results:
        print("No results. Try removing a filter.")
    for i, r in enumerate(results, start=1):
        pages = f"p.{r['page_start']}" if r["page_start"] == r["page_end"] else f"pp.{r['page_start']}-{r['page_end']}"
        print(f"\n[{i}] {r['spec']} §{r['section_number']} {r['section_title']} ({pages})")
        print(f"    score={r['score']}  dense_rank={r['dense_rank']}  bm25_rank={r['bm25_rank']}")
        print("   ", preview(r["text"]))


def main():
    parser = argparse.ArgumentParser(description="Search the 5G specs.")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=config.TOP_K)
    parser.add_argument("--doc", help="e.g. ts_23501")
    parser.add_argument("--topic", help="radio_access, architecture, procedures or security")
    parser.add_argument("--section", help="e.g. 5.2 (also matches 5.2.1, 5.2.2 ...)")
    parser.add_argument("--mode", choices=["hybrid", "dense", "bm25"], default="hybrid")
    args = parser.parse_args()

    retriever = load_retriever()
    filters = build_filters(args.doc, args.topic, args.section)
    results = retriever.search(args.query, top_k=args.top_k, filters=filters, mode=args.mode)
    print_results(results)


if __name__ == "__main__":
    main()
