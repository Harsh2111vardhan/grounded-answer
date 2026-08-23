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

For example, do NOT write:
"Recover at the higher rate under §9.3.2 §9.6.1."

Instead write:
"Recover at the higher rate. §9.6.1"

or, where the cited clause itself establishes the referenced provision:
"Recover at the higher rate under §9.3.2. §9.6.1"

The citation at the end of each factual claim must identify the clause that
directly supports that claim.

Never invent, infer, or reuse an unavailable citation.

If the evidence does not establish an answer, say that the supplied policy
evidence does not establish it. Do not guess.

If the evidence contains conflicting provisions, do not choose one silently.
State that the provisions conflict and cite the relevant provisions.

Keep the answer concise, but make sure every part of the user's question
is answered before stopping.

When the question asks for multiple pieces of information:
- Answer every requested part.
- Prefer short sentences or bullet points.
- Do not repeat the same policy wording unnecessarily.
- Do not add background information that was not requested.
- Do not add procedural details or conditions unless they are necessary
  to answer the question.

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

Do not combine citations from different clauses into one sentence or bullet.

If a clause is referenced but not supplied, do not cite that clause.

Policy evidence:
{evidence_text}

Write a concise, complete answer.

Requirements:
1. Answer every part of the question.
2. Use only the supplied policy evidence.
3. Every substantive factual claim must have exactly one citation.
4. The citation must directly support the claim immediately before it.
5. Every citation must be one of the ALLOWED CITATIONS.
6. If a clause is referenced but not supplied, do not cite it.
7. If the supplied evidence is insufficient, explicitly say so instead
   of guessing.
8. If multiple facts are requested, use separate bullet points.
9. Do not add unnecessary policy details.
10. Do not stop until every requested part has been answered.
"""

        return self.client.generate(
            prompt=prompt,
            system_instruction=SYSTEM_INSTRUCTION,
            max_output_tokens=1200,
        )