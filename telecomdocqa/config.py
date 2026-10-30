"""All project settings live here, so you only change values in one place."""

from pathlib import Path

# Folder paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"              # put the downloaded PDF specs here
PROCESSED_DIR = DATA_DIR / "processed"  # ingestion output goes here
MANIFEST_PATH = DATA_DIR / "manifest.json"
CHUNKS_PATH = PROCESSED_DIR / "chunks.jsonl"

# Chunking settings (measured in words, which is simple and easy to explain).
# ~200 words is roughly 260 tokens: big enough to hold one idea from a spec,
# small enough that retrieval stays precise.
CHUNK_SIZE_WORDS = 200
CHUNK_OVERLAP_WORDS = 40   # words shared by neighbouring chunks, so a sentence cut at a boundary is not lost
MIN_SECTION_WORDS = 10     # sections shorter than this (e.g. "Void.") are skipped

# A line that appears on at least this fraction of pages is treated as a
# repeated header or footer (e.g. "ETSI TS 138 300 V17.0.0") and removed.
HEADER_FOOTER_THRESHOLD = 0.5

# ---------------- Step 2: retrieval ----------------
INDEX_DIR = DATA_DIR / "index"
CHROMA_DIR = INDEX_DIR / "chroma"
INDEX_INFO_PATH = INDEX_DIR / "index_info.json"
COLLECTION_NAME = "telecom_chunks"

# Small, fast embedding model that does well on retrieval benchmarks.
# It runs fine on a laptop CPU (384-dimensional vectors).
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
# BGE models work best when the *query* (not the documents) has this prefix.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# How many candidates each retriever (dense and BM25) returns before fusion.
CANDIDATES_PER_RETRIEVER = 30
# Reciprocal Rank Fusion constant. 60 is the value from the original RRF paper.
RRF_K = 60
# Default number of final results.
TOP_K = 5

# ---------------- Step 3: reranking ----------------
# A cross-encoder reads the question and a chunk *together* and scores how
# well the chunk answers it. This small model (22M parameters) is fast on a
# laptop CPU. A stronger but ~10x slower option is "BAAI/bge-reranker-base".
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
# How many hybrid results we pass to the reranker. More = better recall but
# slower, because the cross-encoder runs once per candidate.
RERANK_CANDIDATES = 20
