from __future__ import annotations

from ..models import Evidence
from .gemini import GeminiClient


SYSTEM_INSTRUCTION = """You answer questions about a policy manual.

Use only the evidence supplied in the user prompt.
Do not use general knowledge or invent missing policy.

Every substantive factual claim must include a citation in the form §X.Y.Z.
Only cite clause IDs that appear in the supplied evidence.

If the evidence does not establish an answer, say that the manual evidence
provided does not establish it. Do not guess.

If the evidence contains conflicting provisions, do not choose one silently.
State that the provisions conflict and cite both sides.

Keep the answer concise and directly answer the question.
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
                "I cannot answer this from the supplied policy evidence."
            )

        evidence_text = self._format_evidence(evidence)

        prompt = f"""Question:
{question}

Policy evidence:
{evidence_text}

Write the answer using only this evidence.
"""

        return self.client.generate(
            prompt=prompt,
            system_instruction=SYSTEM_INSTRUCTION,
            max_output_tokens=800,
        )