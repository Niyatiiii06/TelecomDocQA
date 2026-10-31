"""Step 2: dense retrieval, BM25 keyword retrieval, and hybrid fusion.

Why two retrievers?
- Dense (embeddings) understands meaning: "how does the phone move between
  cells" can match a chunk about "handover".
- BM25 (keywords) is great at exact terms that matter a lot in telecom:
  "N2", "AMF", "S-NSSAI", "38.300". Embedding models often blur these.
Combining them with Reciprocal Rank Fusion (RRF) gets the best of both.

Every retriever accepts the same `filters` dict, e.g.
    {"doc_id": "ts_23501", "topic": "architecture", "section": "5.2"}
Any key can be left out. "section": "5.2" matches 5.2, 5.2.1, 5.2.3.4 ...
"""

import math
import re
from array import array
from collections import Counter, defaultdict

import numpy as np

from telecomdocqa import config

# Words too common to help keyword search.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "does", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "what",
    "when", "which", "who", "why", "with",
}


def chunk_to_text(chunk):
    """The text we search over. Adding the spec and section title helps both
    retrievers, e.g. a chunk under "5.2.1 Registration procedure" can match
    "registration" even if the word isn't in the chunk body."""
    return f"{chunk['spec']} section {chunk['section_number']} {chunk['section_title']}. {chunk['text']}"


def tokenize(text):
    """Lowercase and split into words, keeping telecom terms like
    "5g", "n2", "ng-ran" and "s-nssai" in one piece."""
    words = re.findall(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", text.lower())
    return [w for w in words if w not in STOPWORDS]


def section_matches(section_number, wanted):
    """True if `section_number` is `wanted` or one of its sub-sections.
    "5.2" matches "5.2" and "5.2.1" but NOT "5.20"."""
    return section_number == wanted or section_number.startswith(wanted + ".")


def matches_filters(chunk, filters):
    """Check one chunk against the filters dict (None or {} = no filters)."""
    if not filters:
        return True
    if filters.get("doc_id") and chunk["doc_id"] != filters["doc_id"]:
        return False
    if filters.get("topic") and chunk["topic"] != filters["topic"]:
        return False
    if filters.get("section") and not section_matches(chunk["section_number"], filters["section"]):
        return False
    return True


class BM25Index:
    """BM25 (Okapi) keyword scoring with an inverted index.

    For each word we store which chunks contain it and how often, as two
    small numpy arrays. Scoring a query only touches the chunks that contain
    its words. This gives exactly the same scores as the rank_bm25 library
    (BM25Okapi, k1=1.5, b=0.75, epsilon=0.25), but uses about 10x less memory,
    because rank_bm25 keeps a separate word-count dictionary for every chunk.

    For one word in one chunk:
        idf(word) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * chunk_length / average_length))
    where tf = how often the word appears in the chunk, and idf is high for
    rare words and low for common ones ("amf" counts less than "s-nssai").
    """

    def __init__(self, tokenized_docs, k1=1.5, b=0.75, epsilon=0.25):
        """`tokenized_docs` can be a generator, so the word lists of all
        chunks never have to be in memory at the same time."""
        self.k1, self.b = k1, b

        # word -> (chunk numbers, counts). array() stores numbers compactly
        # (4 bytes each), unlike a Python list (about 36 bytes each).
        postings = defaultdict(lambda: (array("i"), array("f")))
        lengths = array("f")
        for doc_number, doc in enumerate(tokenized_docs):
            lengths.append(len(doc))
            for word, count in Counter(doc).items():
                postings[word][0].append(doc_number)
                postings[word][1].append(count)

        self.n_docs = len(lengths)
        self.doc_lengths = np.array(lengths, dtype=np.float32)
        self.avg_length = float(self.doc_lengths.mean()) if self.n_docs else 0.0
        self.postings = {
            word: (np.array(docs, dtype=np.int32), np.array(counts, dtype=np.float32))
            for word, (docs, counts) in postings.items()
        }

        # idf, with rank_bm25's rule for very common words: an idf below zero
        # is replaced by a small positive value (epsilon * average idf).
        self.idf = {
            word: math.log(self.n_docs - len(docs) + 0.5) - math.log(len(docs) + 0.5)
            for word, (docs, _) in self.postings.items()
        }
        floor = epsilon * (sum(self.idf.values()) / len(self.idf)) if self.idf else 0.0
        self.idf = {word: (idf if idf >= 0 else floor) for word, idf in self.idf.items()}

    def get_scores(self, query_words):
        """One score per chunk (0 for chunks without any query word)."""
        scores = np.zeros(self.n_docs, dtype=np.float64)
        for word in query_words:
            if word not in self.postings:
                continue
            docs, counts = self.postings[word]
            length_norm = 1 - self.b + self.b * self.doc_lengths[docs] / self.avg_length
            scores[docs] += self.idf[word] * counts * (self.k1 + 1) / (counts + self.k1 * length_norm)
        return scores


class BM25Retriever:
    """Keyword search. Built in memory from the chunks (takes a few seconds)."""

    def __init__(self, chunks):
        self.chunks = chunks
        self.bm25 = BM25Index(tokenize(chunk_to_text(c)) for c in chunks)

    def search(self, query, k=config.CANDIDATES_PER_RETRIEVER, filters=None):
        """Return a list of (chunk_id, score), best first."""
        scores = self.bm25.get_scores(tokenize(query))
        # pair each chunk index with its score, keep only chunks that pass the filters
        candidates = [
            (i, score) for i, score in enumerate(scores)
            if score > 0 and matches_filters(self.chunks[i], filters)
        ]
        candidates.sort(key=lambda pair: pair[1], reverse=True)
        return [(self.chunks[i]["chunk_id"], float(score)) for i, score in candidates[:k]]


def chroma_where(filters):
    """Turn our filters into ChromaDB's `where` format (for doc_id and topic).
    Section prefixes aren't supported by Chroma, so we check those ourselves."""
    conditions = []
    if filters and filters.get("doc_id"):
        conditions.append({"doc_id": filters["doc_id"]})
    if filters and filters.get("topic"):
        conditions.append({"topic": filters["topic"]})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


class DenseRetriever:
    """Embedding search using the ChromaDB index built by index_builder.py."""

    def __init__(self, collection, embedder):
        self.collection = collection
        self.embedder = embedder

    def search(self, query, k=config.CANDIDATES_PER_RETRIEVER, filters=None):
        """Return a list of (chunk_id, similarity), best first."""
        section = filters.get("section") if filters else None
        # With a section filter we ask Chroma for extra results, then keep
        # only the ones in that section.
        n_results = k * 10 if section else k
        n_results = min(n_results, self.collection.count())

        result = self.collection.query(
            query_embeddings=[self.embedder.embed_query(query)],
            n_results=n_results,
            where=chroma_where(filters),
        )

        hits = []
        for chunk_id, distance, metadata in zip(result["ids"][0], result["distances"][0], result["metadatas"][0]):
            if section and not section_matches(metadata["section_number"], section):
                continue
            hits.append((chunk_id, 1 - distance))  # cosine distance -> similarity
        return hits[:k]


def reciprocal_rank_fusion(result_lists, k=config.RRF_K):
    """Combine several ranked lists into one.

    Each chunk gets 1 / (k + rank) from every list it appears in, and the
    scores are added up. We only use ranks, not raw scores, because BM25
    scores (like 12.7) and cosine similarities (like 0.83) aren't on the
    same scale. A chunk ranked high by both retrievers ends up on top.
    """
    fused = {}
    for results in result_lists:
        for rank, (chunk_id, _score) in enumerate(results, start=1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda pair: pair[1], reverse=True)


class HybridRetriever:
    """Runs dense and BM25 search, then fuses the results with RRF."""

    def __init__(self, chunks, dense, bm25):
        self.dense = dense
        self.bm25 = bm25
        self.chunks_by_id = {c["chunk_id"]: c for c in chunks}

    def search(self, query, top_k=config.TOP_K, filters=None, mode="hybrid"):
        """Return the top_k chunks as dicts, each with extra fields:
        score, dense_rank and bm25_rank (None if that retriever missed it).
        mode can be "hybrid", "dense" or "bm25" (useful for comparisons)."""
        dense_hits = self.dense.search(query, filters=filters) if mode in ("hybrid", "dense") else []
        bm25_hits = self.bm25.search(query, filters=filters) if mode in ("hybrid", "bm25") else []

        if mode == "dense":
            ranked = dense_hits
        elif mode == "bm25":
            ranked = bm25_hits
        else:
            ranked = reciprocal_rank_fusion([dense_hits, bm25_hits])

        dense_ranks = {cid: r for r, (cid, _) in enumerate(dense_hits, start=1)}
        bm25_ranks = {cid: r for r, (cid, _) in enumerate(bm25_hits, start=1)}

        results = []
        for chunk_id, score in ranked[:top_k]:
            chunk = dict(self.chunks_by_id[chunk_id])  # copy, so we don't change the original
            chunk["score"] = round(score, 4)
            chunk["dense_rank"] = dense_ranks.get(chunk_id)
            chunk["bm25_rank"] = bm25_ranks.get(chunk_id)
            results.append(chunk)
        return results
