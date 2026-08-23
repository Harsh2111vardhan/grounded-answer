from __future__ import annotations

from ..models import Evidence
from .gemini import GeminiClient


SYSTEM_INSTRUCTION = """You answer questions about a policy manual.

Use only the evidence supplied in the user prompt.
Do not use general knowledge or invent missing policy.

CITATION RULES:

Every substantive factual claim must include a citation in the form §X.Y.Z.

You may ONLY use citation IDs that appear in the supplied evidence.

A clause mentioned or cross-referenced inside another clause is NOT available
unless that clause itself appears in the supplied evidence.

Each factual claim must have ONE grounding citation.

Do not place multiple citations at the end of the same factual claim.

If two different clauses support two different facts, write them as separate
sentences or bullet points with one citation attached to each fact.

The citation must identify the clause that directly supports the claim.

Never invent, infer, or reuse an unavailable citation.

ANSWER STYLE:

Answer the user's question directly.

For simple yes/no or definition questions:
- Give the direct answer first.
- Use one or two concise sentences.
- Do not repeat the definition unless it is needed to explain the answer.
- Do not restate the same rule in multiple ways.
- Do not add unnecessary background information.

For questions with multiple requested facts:
- Answer every requested part.
- Use short bullet points when useful.
- Give one citation per factual claim.
- Do not add unrelated policy details.

Do not strengthen policy language with words such as "strictly", "always",
"never", "only", "automatically", or "necessarily" unless that meaning is
explicitly supported by the evidence.

If the evidence does not establish an answer, say that the supplied policy
evidence does not establish it. Do not guess.

If the evidence contains conflicting provisions, do not choose one silently.
State that the provisions conflict and cite the relevant provisions.

ESCALATION INSTRUCTION:

If the retrieved policy evidence does not establish a reliable answer:
- Do not guess or infer the missing policy.
- Clearly state that the available policy evidence does not establish the answer.
- Tell the user who they should contact for clarification, using only a
  person, office, department, or referral explicitly identified in the
  retrieved evidence.
- If the retrieved evidence does not identify a specific contact, tell the
  user to contact their local Department district office.
- Never invent a person's name, phone number, email address, office, or other
  contact details.
"""


class PolicyAnswerer:
    def __init__(self, client: GeminiClient):
        self.client = client

    @staticmethod
    def _format_evidence(evidence: list[Evidence]) -> str:
        blocks = []

        for item in evidence:
            blocks.append(
                f"{item.clause_id}\n"
                f"{item.text}"
            )

        return "\n\n".join(blocks)

    def answer(
        self,
        question: str,
        evidence: list[Evidence],
    ) -> str:
        if not evidence:
            return (
                "I cannot answer this from the supplied policy evidence. "
                "Please contact your local Department district office "
                "for clarification."
            )

        evidence_text = self._format_evidence(evidence)

        allowed_citations = ", ".join(
            item.clause_id
            for item in evidence
        )

        prompt = f"""Question:
{question}

ALLOWED CITATIONS:
{allowed_citations}

IMPORTANT:
You may cite ONLY the clause IDs listed under ALLOWED CITATIONS.

Each factual claim must have exactly ONE grounding citation.

The citation must directly support the claim immediately before it.

Do not combine multiple citations into one factual claim.

If a clause is referenced but not supplied, do not cite that clause.

Policy evidence:
{evidence_text}

Write the final answer for the user using the policy wording as the
grounding source.

For date-sensitive questions, distinguish between:
- the date/event supplied by the user, and
- the policy's stated time period.

If the policy says "14 calendar days", answer "14 calendar days".
Do not calculate the resulting calendar date unless the user explicitly asks
for that calculation.

Requirements:
1. Answer the question directly.
2. Answer every part if the question contains multiple parts.
3. Use only the supplied policy evidence.
4. Every substantive factual claim must have exactly one citation.
5. Every citation must be one of the ALLOWED CITATIONS.
6. For a simple yes/no question, answer yes or no first.
7. For a simple question, keep the answer to one or two concise sentences
   unless more detail is required to answer it completely.
8. Do not repeat the same policy requirement in multiple bullets or sentences.
9. Do not add unnecessary policy details, conditions, procedures, or
   cross-references.
10. Do not strengthen the policy with unsupported words such as "strictly",
    "always", "never", "only", "automatically", or "necessarily".
11. If the evidence is insufficient, say so rather than guessing.
12. If the evidence conflicts, explicitly state the conflict instead of
    selecting one provision.
13. Do not calculate, derive, or add a specific calendar date unless the
    supplied policy evidence explicitly states that date or the user
    explicitly asks you to calculate a date.
14. When the policy gives a time period such as "14 calendar days", preserve
    that period exactly rather than converting it into a calendar date.
15. Do not add information merely because it can be mathematically derived
    from the user's scenario.
"""

        return self.client.generate(
            prompt=prompt,
            system_instruction=SYSTEM_INSTRUCTION,
            max_output_tokens=1200,
        )