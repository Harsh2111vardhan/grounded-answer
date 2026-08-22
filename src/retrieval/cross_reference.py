from __future__ import annotations

import re

from ..models import Evidence, PolicyClause


REFERENCE_RE = re.compile(
    r"§(?P<id>\d+\.\d+\.\d+(?:\([a-z]+\))?|\d+\.\d+)"
)


class CrossReferenceExpander:
    """Expand one-hop policy references found in retrieved clauses."""

    def __init__(self, clauses: list[PolicyClause]):
        self.clauses = clauses
        self.by_id = {clause.clause_id: clause for clause in clauses}

    def _resolve(self, reference_id: str) -> list[PolicyClause]:
        """Resolve an exact clause or a section-level reference."""
        exact_id = f"§{reference_id}"

        if exact_id in self.by_id:
            return [self.by_id[exact_id]]

        # A reference such as §5.4 points to the provisions in that section.
        prefix = f"§{reference_id}."
        return [
            clause
            for clause in self.clauses
            if clause.clause_id.startswith(prefix)
        ]

    def expand(self, evidence: list[Evidence]) -> list[Evidence]:
        """Add directly referenced clauses, one hop deep."""
        expanded = list(evidence)
        existing_ids = {item.clause_id for item in expanded}

        for item in evidence:
            for match in REFERENCE_RE.finditer(item.text):
                reference_id = match.group("id")
                referenced = self._resolve(reference_id)

                for clause in referenced:
                    if clause.clause_id in existing_ids:
                        continue

                    expanded.append(
                        Evidence(
                            clause_id=clause.clause_id,
                            text=clause.text,
                            part=clause.part,
                            section=clause.section,
                            line_no=clause.line_no,
                            retrieval_sources=["cross_reference"],
                            cross_reference_of=item.clause_id,
                        )
                    )
                    existing_ids.add(clause.clause_id)

        return expanded
