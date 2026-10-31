"""Download the prebuilt index (chunks + ChromaDB) from a Hugging Face dataset.

A server shouldn't need the PDFs, or 10 minutes, to rebuild the index, so
the index you built locally is published once to a free Hugging Face dataset
repository (deploy/publish_index.py) and downloaded here when a server starts.

Run from the project root (does nothing if the index is already there):
    python -m telecomdocqa.remote_index
"""

from telecomdocqa import config

INDEX_FILES = ["processed/*", "index/*"]  # paths inside the dataset repo, relative to data/


def index_is_ready():
    return config.CHUNKS_PATH.exists() and config.INDEX_INFO_PATH.exists() and config.CHROMA_DIR.exists()


def ensure_index(repo_id=None):
    """Download the index if it isn't on disk yet. Returns True if it downloaded."""
    if index_is_ready():
        return False

    from huggingface_hub import snapshot_download

    repo_id = repo_id or config.INDEX_REPO
    print(f"Downloading the index from the Hugging Face dataset {repo_id} ...")
    snapshot_download(repo_id=repo_id, repo_type="dataset", local_dir=str(config.DATA_DIR),
                      allow_patterns=INDEX_FILES)
    if not index_is_ready():
        raise RuntimeError(f"The dataset {repo_id} doesn't contain processed/chunks.jsonl and index/.")
    return True


if __name__ == "__main__":
    downloaded = ensure_index()
    print("Index downloaded." if downloaded else "Index already present.")
