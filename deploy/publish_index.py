"""Step 8: publish the prebuilt index to a free Hugging Face dataset repository.

The live demo and the Docker image download the index from there
(telecomdocqa/remote_index.py), so no server needs the PDFs or has to spend
10 minutes rebuilding it. Run this again whenever you rebuild the index.

Before running it once, put a Hugging Face WRITE token in your .env:
    HF_TOKEN=hf_...

Run from the project root:
    python deploy/publish_index.py --dry-run
    python deploy/publish_index.py
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from telecomdocqa import config  # noqa: E402  (needs the path line above)
from telecomdocqa.remote_index import INDEX_FILES, index_is_ready  # noqa: E402

DATASET_CARD = """---
license: other
pretty_name: TelecomDocQA index
tags: [rag, 3gpp, 5g]
---

# TelecomDocQA index

The prebuilt search index for [TelecomDocQA](https://github.com/{github}/TelecomDocQA):
section-aware chunks of four 3GPP specifications (TS 38.300, 23.501, 23.502, 33.501,
Release 18) and their ChromaDB vector index (`{model}` embeddings).

The text comes from the 3GPP specifications as published for free by ETSI
(etsi.org/deliver); all rights in the specifications remain with ETSI and the
3GPP Organizational Partners. This index exists only to run a non-commercial,
educational demo.
"""


def main():
    parser = argparse.ArgumentParser(description="Publish the index to a Hugging Face dataset.")
    parser.add_argument("--repo", default=config.INDEX_REPO, help="e.g. your-hf-username/telecomdocqa-index")
    parser.add_argument("--github", default="Niyatiiii06", help="your GitHub username, for the dataset card")
    parser.add_argument("--dry-run", action="store_true", help="only list what would be uploaded")
    args = parser.parse_args()

    if not index_is_ready():
        sys.exit("Build the index first: python -m telecomdocqa.chunking, then python -m telecomdocqa.index_builder")

    files = [p for p in config.DATA_DIR.rglob("*")
             if p.is_file() and p.relative_to(config.DATA_DIR).parts[0] in ("processed", "index")]
    total_mb = sum(p.stat().st_size for p in files) / 1e6
    print(f"{len(files)} files, {total_mb:.0f} MB to upload to the dataset {args.repo}")
    if args.dry_run:
        for p in sorted(files):
            print(f"  {p.stat().st_size / 1e6:8.1f} MB  {p.relative_to(config.DATA_DIR).as_posix()}")
        return

    from huggingface_hub import HfApi

    api = HfApi()
    print("Logged in as:", api.whoami()["name"])
    api.create_repo(args.repo, repo_type="dataset", exist_ok=True)
    card = DATASET_CARD.format(github=args.github, model=config.EMBEDDING_MODEL)
    api.upload_file(path_or_fileobj=card.encode("utf-8"), path_in_repo="README.md",
                    repo_id=args.repo, repo_type="dataset", commit_message="Update dataset card")
    api.upload_folder(
        folder_path=str(config.DATA_DIR),
        repo_id=args.repo,
        repo_type="dataset",
        allow_patterns=INDEX_FILES,
        delete_patterns=INDEX_FILES,  # remove files that no longer exist locally
        commit_message="Publish index",
    )
    print(f"Done: https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    main()
