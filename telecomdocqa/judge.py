"""Step 5: an LLM judge that grades answers.

Two checks, because they catch different problems:
- Faithfulness: is every claim in the answer supported by the sources it
  was given? (Catches the model making things up.)
- Correctness: does the answer agree with the reference answer?
  (Catches answers that are faithful to the WRONG sources.)
An answer can be 100% faithful and still wrong, which is why we need both.
"""

from telecomdocqa import config
from telecomdocqa.answer import source_label
from telecomdocqa.metrics import parse_json_reply

FAITHFULNESS_PROMPT = """You check whether an answer is supported by its sources.

Sources:
{sources}

Answer:
{answer}

Instructions:
1. Split the answer into its individual factual claims (ignore citation markers like [1]).
2. For each claim, decide if the sources directly support it.
3. Reply with ONLY this JSON, nothing else:
{{"claims": [{{"claim": "...", "supported": true}}], "supported_claims": <number>, "total_claims": <number>}}"""

CORRECTNESS_PROMPT = """You grade an answer to a question about 5G (3GPP) specifications.

Question: {question}

Reference answer (written by an expert from the specification):
{reference}

Answer to grade:
{answer}

Grade the answer against the reference:
- "correct": contains the key facts of the reference and nothing that contradicts it
- "partial": some key facts are right, but important ones are missing
- "incorrect": wrong, contradicts the reference, or doesn't answer the question
Extra correct detail beyond the reference is fine.

Reply with ONLY this JSON, nothing else:
{{"grade": "correct" | "partial" | "incorrect", "reason": "<one sentence>"}}"""

GRADE_SCORES = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}


class Judge:
    def __init__(self, llm):
        self.llm = llm

    def faithfulness(self, answer, sources):
        """Share of the answer's claims that the sources support (0 to 1)."""
        source_text = "\n\n".join(
            f"[{i}] {source_label(chunk)}\n{chunk['text']}" for i, chunk in enumerate(sources, start=1)
        )
        reply = self.llm.chat(
            [{"role": "user", "content": FAITHFULNESS_PROMPT.format(sources=source_text, answer=answer)}],
            max_tokens=config.JUDGE_MAX_TOKENS,
        )
        data = parse_json_reply(reply)
        total = int(data.get("total_claims", 0))
        supported = int(data.get("supported_claims", 0))
        return {"score": supported / total if total else None, "supported": supported, "total": total}

    def correctness(self, question, reference, answer):
        """'correct' = 1, 'partial' = 0.5, 'incorrect' = 0."""
        reply = self.llm.chat(
            [{"role": "user", "content": CORRECTNESS_PROMPT.format(question=question, reference=reference, answer=answer)}],
            max_tokens=config.JUDGE_MAX_TOKENS,
        )
        data = parse_json_reply(reply)
        grade = str(data.get("grade", "")).lower().strip()
        if grade not in GRADE_SCORES:
            raise ValueError(f"Unexpected grade from judge: {grade!r}")
        return {"score": GRADE_SCORES[grade], "grade": grade, "reason": data.get("reason", "")}


def load_judge():
    from telecomdocqa.llm import LLMClient

    llm = LLMClient(model=config.JUDGE_MODEL, reasoning_effort=config.JUDGE_REASONING_EFFORT)
    return Judge(llm)
