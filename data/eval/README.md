# Evaluation set

`questions.jsonl` has one question per line:

| Field | Meaning |
|---|---|
| `id` | `q01`-`q58` answerable, `u01`-`u10` unanswerable |
| `question` | The question, phrased the way a user would ask it |
| `gold` | Correct spec section(s) as `[doc_id, section]`. A section also covers its sub-sections (`5.6.9` includes `5.6.9.2.1`). |
| `reference_answer` | Key facts the answer should contain, taken from the spec text |
| `answerable` | `false` for questions the four specs can't answer (off-topic or not covered) |
| `topic` | `radio_access`, `architecture`, `procedures`, `security` (or `off_topic` / `in_domain_not_covered`) |
| `verified` | Set to `true` once a human has checked the question against the spec |

## How it was made

The questions and reference answers were drafted with AI assistance from the
text of the specific spec sections, then reviewed by hand. Gold labels are
sections rather than chunk IDs, so the set stays valid if the chunking changes.

## How to review a question

1. Open the PDF in `data/raw/` and go to the gold section.
2. Check the reference answer matches what the section says.
3. Check the question is clear and the section really answers it.
4. Fix anything wrong, then set `"verified": true`.

The evaluation scripts print how many questions are still unverified.

## Label changes

Changes made after looking at evaluation results, recorded so the numbers stay honest.
A gold section is only added when its text genuinely answers the question.

| Date | Question | Change | Reason |
|---|---|---|---|
| 2026-10-31 | q31 | added `ts_23501 4.2.8.1` | States that untrusted non-3GPP access connects via the N3IWF |
| 2026-10-31 | q44 | added `ts_23501 7.1.5` | Describes NF registration with the NRF |
| 2026-10-31 | q52 | added `ts_23501 5.10.3` | Defines the UP security policy for PDU sessions |
