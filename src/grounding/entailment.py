from __future__ import annotations

import re
from dataclasses import dataclass

from ..models import Evidence
from ..llm.gemini import GeminiClient
from .claims import Claim


@dataclass(frozen=True)
class EntailmentResult:
    claim: str
    citation: str
    supported: bool
    reason: str


ENTAILMENT_SYSTEM = """You are a narrow policy entailment checker.

Your only task is to decide whether the supplied policy clause supports the
specific claim.

Answer YES only when the clause text directly supports the claim.
Answer NO when the clause does not support the claim, contradicts it, or the
claim adds information that is not stated or reasonably entailed by the clause.

Do not use general knowledge.
Do not infer missing policy.
Do not judge whether the policy itself is correct.

Your first non-empty line must be exactly YES or NO.
After that, give one short reason based only on the clause.
"""


class EntailmentChecker:
    def __init__(self, client: GeminiClient):
        self.client = client

    def check(self, claim: Claim, clause: Evidence) -> EntailmentResult:
        prompt = f"""Claim:
{claim.text}

Citation:
{claim.citation}

Policy clause:
{clause.clause_id}
{clause.text}

Does this clause support this specific claim?
"""

        response = self.client.generate(
            prompt=prompt,
            system_instruction=ENTAILMENT_SYSTEM,
            max_output_tokens=200,
        )

        first_line = next(
            (
                line.strip().upper()
                for line in response.splitlines()
                if line.strip()
            ),
            "",
        )

        if first_line.startswith("YES"):
            supported = True
        elif first_line.startswith("NO"):
            supported = False
        else:
            raise ValueError(
                "Entailment checker returned an invalid decision. "
                "Expected YES or NO on the first non-empty line."
            )

        reason = re.sub(
            r"^\s*(YES|NO)\s*:?\s*",
            "",
            response.strip(),
            count=1,
            flags=re.IGNORECASE,
        ).strip()

        return EntailmentResult(
            claim=claim.text,
            citation=claim.citation,
            supported=supported,
            reason=reason,
        )

    def check_all(
        self,
        claims: list[Claim],
        evidence: list[Evidence],
    ) -> list[EntailmentResult]:
        evidence_by_id = {
            item.clause_id: item
            for item in evidence
        }

        results: list[EntailmentResult] = []

        # Cache results for identical claim/citation pairs.
        # This prevents repeated Gemini calls for the same claim and
        # avoids inconsistent results caused by nondeterministic generation.
        checked: dict[tuple[str, str], EntailmentResult] = {}

        for claim in claims:
            clause = evidence_by_id.get(claim.citation)

            if clause is None:
                results.append(
                    EntailmentResult(
                        claim=claim.text,
                        citation=claim.citation,
                        supported=False,
                        reason=(
                            "Cited clause is not present in the supplied "
                            "evidence."
                        ),
                    )
                )
                continue

            key = (
                claim.text.strip(),
                claim.citation,
            )

            if key in checked:
                results.append(checked[key])
                continue

            result = self.check(
                claim,
                clause,
            )

            checked[key] = result
            results.append(result)

        return results