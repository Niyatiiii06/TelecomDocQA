"""Step 1b: split sections into overlapping chunks and save them.

Every chunk keeps metadata (document, spec number, topic, section, pages).
That metadata is what makes citations and metadata filtering possible later.

Run from the project root:
    python -m telecomdocqa.chunking
"""

import argparse
import json
from pathlib import Path

from telecomdocqa import config
from telecomdocqa.ingest import load_document_sections


def chunk_section(section, doc_info, chunk_size, overlap):
    """ We keep the page number of every word, so each chunk knows which
    page(s) it came from."""
    words = []  # list of (word, page_number)
    for page_number, line in section["lines"]:
        for word in line.split():
            words.append((word, page_number))
    if len(words) < config.MIN_SECTION_WORDS:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        # If only a few words would be left over, add them to this chunk
        # instead of making a tiny last chunk that is mostly overlap.
        if len(words) - end < overlap:
            end = len(words)
        piece = words[start:end]

        chunk_number = len(chunks)
        chunks.append({
            "chunk_id": f"{doc_info['doc_id']}::{section['section_number']}::{chunk_number}",
            "doc_id": doc_info["doc_id"],
            "spec": doc_info["spec"],
            "doc_title": doc_info["title"],
            "topic": doc_info["topic"],
            "section_number": section["section_number"],
            "section_title": section["section_title"],
            "page_start": piece[0][1],
            "page_end": piece[-1][1],
            "text": " ".join(word for word, _ in piece),
            "n_words": len(piece),
        })
        if end == len(words):
            break
        start = end - overlap  # step back so neighbouring chunks overlap
    return chunks


def chunk_document(pdf_path, doc_info, chunk_size, overlap, keep_front_matter=False):
    """Read one PDF and return (number_of_pages, number_of_sections, chunks)."""
    pages, sections = load_document_sections(pdf_path)
    if not keep_front_matter:
        sections = [s for s in sections if s["section_number"] != "0"]
    chunks = []
    seen_ids = set()
    for section in sections:
        for chunk in chunk_section(section, doc_info, chunk_size, overlap):
            # A few section numbers appear twice in a spec. Add a suffix
            # so every chunk_id stays unique (we need that for evaluation).
            chunk_id = chunk["chunk_id"]
            n = 2
            while chunk_id in seen_ids:
                chunk_id = f"{chunk['chunk_id']}-{n}"
                n += 1
            chunk["chunk_id"] = chunk_id
            seen_ids.add(chunk_id)
            chunks.append(chunk)
    return len(pages), len(sections), chunks


def load_manifest(manifest_path):
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)["documents"]


def save_chunks(chunks, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def load_chunks(path=config.CHUNKS_PATH):
    """Read chunks back from the JSONL file (used by later steps)."""
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    parser = argparse.ArgumentParser(description="Ingest PDF specs and create chunks.")
    parser.add_argument("--manifest", default=str(config.MANIFEST_PATH))
    parser.add_argument("--raw-dir", default=str(config.RAW_DIR))
    parser.add_argument("--output", default=str(config.CHUNKS_PATH))
    parser.add_argument("--chunk-size", type=int, default=config.CHUNK_SIZE_WORDS)
    parser.add_argument("--overlap", type=int, default=config.CHUNK_OVERLAP_WORDS)
    parser.add_argument("--show", type=int, default=0, help="print this many example chunks")
    args = parser.parse_args()

    if args.overlap >= args.chunk_size:
        raise ValueError("--overlap must be smaller than --chunk-size")

    all_chunks = []
    print(f"{'document':<12} {'pages':>6} {'sections':>9} {'chunks':>7}")
    for doc_info in load_manifest(args.manifest):
        pdf_path = Path(args.raw_dir) / doc_info["file"]
        if not pdf_path.exists():
            print(f"{doc_info['doc_id']:<12} MISSING: download it to {pdf_path}")
            continue

        n_pages, n_sections, chunks = chunk_document(pdf_path, doc_info, args.chunk_size, args.overlap)
        all_chunks.extend(chunks)
        print(f"{doc_info['doc_id']:<12} {n_pages:>6} {n_sections:>9} {len(chunks):>7}")

    if not all_chunks:
        print("No chunks created. Check that the PDFs are in", args.raw_dir)
        return

    save_chunks(all_chunks, args.output)
    print(f"\nSaved {len(all_chunks)} chunks to {args.output}")

    for chunk in all_chunks[: args.show]:
        print("\n---", chunk["chunk_id"], f"(pages {chunk['page_start']}-{chunk['page_end']})")
        print(chunk["section_number"], chunk["section_title"])
        print(chunk["text"][:300], "...")


if __name__ == "__main__":
    main()
