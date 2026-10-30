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
