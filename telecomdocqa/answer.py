"""Step 4: grounded answers with citations.

"Grounded" means the LLM may only use the retrieved chunks, not its own
memory. Each chunk is given a number like [1], [2], and the LLM must put
those numbers after every fact. We then check every citation number points
to a real source, and turn it into "TS 23.501 §6.2.1, pp. 522-523".

Run from the project root:
    python -m telecomdocqa.answer "What is the role of the AMF?"
    python -m telecomdocqa.answer "How is the SUPI protected?" --topic security
"""

import argparse
import re
import time

from telecomdocqa import config

SYSTEM_PROMPT = f"""You are an assistant that answers questions about 5G using 3GPP technical specifications.

Rules:
1. Use ONLY the numbered sources provided. Do not use outside knowledge.
2. After every sentence that states a fact, cite the source(s) it came from, like [1] or [2][3].
3. If the sources do not contain the answer, reply with exactly: "{config.NOT_FOUND_MESSAGE}"
4. If the sources only partly answer the question, answer that part and say what is missing.
5. Be clear and concise: a short paragraph or a few bullet points. Keep 3GPP terms (AMF, SUPI, N2) as they are."""


def format_pages(chunk):
    if chunk["page_start"] == chunk["page_end"]:
        return f"p. {chunk['page_start']}"
    return f"pp. {chunk['page_start']}-{chunk['page_end']}"


def source_label(chunk):
    """e.g. 'TS 23.501 §6.2.1 AMF (pp. 522-523)'"""
    return f"{chunk['spec']} §{chunk['section_number']} {chunk['section_title']} ({format_pages(chunk)})"


def build_messages(question, chunks):
    """Put the numbered sources and the question into a chat prompt."""
    sources = []
    for number, chunk in enumerate(chunks, start=1):
        sources.append(f"[{number}] {source_label(chunk)}\n{chunk['text']}")

    user_message = "Sources:\n\n" + "\n\n".join(sources) + f"\n\nQuestion: {question}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]


def normalize_citations(text):
    """Rewrite the different citation styles models use into plain [n].

    gpt-oss often writes 【1】 (or 【1†L3-L5】) instead of [1], and some
    models write [1, 2] instead of [1][2].
    """
    text = re.sub(r"【(\d+)[^】]*】", r"[\1]", text)
    text = re.sub(
        r"\[(\d+(?:\s*,\s*\d+)+)\]",
        lambda match: "".join(f"[{n.strip()}]" for n in match.group(1).split(",")),
        text,
    )
    return text


def extract_citations(answer_text, chunks):
    """Find every [n] in the answer and match it to its source chunk.

    Returns (citations, invalid_numbers). A citation like [7] when we only
    gave 5 sources is invalid: the model made it up, so we report it.
    """
    numbers = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer_text)})
    citations = []
    invalid = []
    for n in numbers:
        if 1 <= n <= len(chunks):
            chunk = chunks[n - 1]
            citations.append({
                "number": n,
                "chunk_id": chunk["chunk_id"],
                "doc_id": chunk["doc_id"],
                "spec": chunk["spec"],
                "section_number": chunk["section_number"],
                "section_title": chunk["section_title"],
                "page_start": chunk["page_start"],
                "page_end": chunk["page_end"],
            })
        else:
            invalid.append(n)
    return citations, invalid


class AnswerGenerator:
    def __init__(self, pipeline, llm):
        self.pipeline = pipeline
        self.llm = llm

    def retrieve(self, question, filters=None):
        """Get the source chunks, or [] if nothing relevant enough was found."""
        chunks = self.pipeline.search(question, top_k=config.ANSWER_TOP_K, filters=filters)
        if not chunks:
            return []
        best = chunks[0].get("rerank_score")
        if best is not None and best < config.MIN_RERANK_SCORE:
            return []  # nothing relevant: don't let the LLM guess
        return chunks

    def answer(self, question, filters=None):
        """Retrieve sources, ask the LLM, and check its citations.
        Returns a dict that later steps (evaluation, API) use directly."""
        start = time.perf_counter()
        chunks = self.retrieve(question, filters)
        retrieval_seconds = time.perf_counter() - start

        if chunks:
            answer_text = normalize_citations(self.llm.chat(build_messages(question, chunks)))
        else:
            answer_text = config.NOT_FOUND_MESSAGE

        citations, invalid = extract_citations(answer_text, chunks)
        return {
            "question": question,
            "answer": answer_text,
            "found_answer": config.NOT_FOUND_MESSAGE not in answer_text,
            "citations": citations,
            "invalid_citations": invalid,
            "sources": chunks,
            "retrieval_seconds": round(retrieval_seconds, 3),
            "total_seconds": round(time.perf_counter() - start, 3),
        }


def load_answer_generator():
    from telecomdocqa.llm import LLMClient
    from telecomdocqa.pipeline import load_pipeline

    return AnswerGenerator(load_pipeline(), LLMClient())


def print_answer(result):
    print("\n" + result["answer"])
    if result["citations"]:
        print("\nSources:")
        for c in result["citations"]:
            print(f"  [{c['number']}] {source_label(c)}")
    if result["invalid_citations"]:
        print(f"\nWARNING: the model cited sources that don't exist: {result['invalid_citations']}")
    print(f"\n(retrieval {result['retrieval_seconds']}s, total {result['total_seconds']}s)")


def main():
    from telecomdocqa.search import build_filters

    parser = argparse.ArgumentParser(description="Ask a question about the 5G specs.")
    parser.add_argument("question")
    parser.add_argument("--doc", help="e.g. ts_23501")
    parser.add_argument("--topic", help="radio_access, architecture, procedures or security")
    parser.add_argument("--section", help="e.g. 5.2")
    args = parser.parse_args()

    generator = load_answer_generator()
    result = generator.answer(args.question, filters=build_filters(args.doc, args.topic, args.section))
    print_answer(result)


if __name__ == "__main__":
    main()
