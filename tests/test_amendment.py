from datetime import date

from src.models import PolicyClause
from src.policy.amendments import apply_amendments, parse_amendment


AMENDMENT = "data/Amendment No. 2026-01.md"


def test_amendment_is_parsed_from_document():
    amendment = parse_amendment(AMENDMENT)
    assert amendment.effective == date(2026, 3, 1)
    assert len(amendment.changes) == 6


def test_event_based_change_uses_old_version_before_effective_date():
    amendment = parse_amendment(AMENDMENT)
    clauses = [PolicyClause("§4.3.2", "Report within 10 calendar days.", "Part 4", "4.3", 1)]
    result = apply_amendments(clauses, [amendment], event_date=date(2026, 2, 28))
    assert result[0].text == clauses[0].text


def test_event_based_change_uses_amended_version_after_effective_date():
    amendment = parse_amendment(AMENDMENT)
    clauses = [PolicyClause("§4.3.2", "Report within 10 calendar days.", "Part 4", "4.3", 1)]
    result = apply_amendments(clauses, [amendment], event_date=date(2026, 3, 1))
    assert "14 calendar days" in result[0].text


def test_determination_based_change_uses_determination_date():
    amendment = parse_amendment(AMENDMENT)
    clauses = [PolicyClause("§10.5.2", "Deduction is 20 per cent.", "Part 10", "10.5", 1)]
    old = apply_amendments(clauses, [amendment], determination_date=date(2026, 2, 28))
    new = apply_amendments(clauses, [amendment], determination_date=date(2026, 3, 1))
    assert "20 per cent" in old[0].text
    assert "15 per cent" in new[0].text


def test_inserted_clause_is_document_derived():
    amendment = parse_amendment(AMENDMENT)
    clauses = [PolicyClause("§10.5.3", "Existing provision.", "Part 10", "10.5", 1)]
    result = apply_amendments(clauses, [amendment], determination_date=date(2026, 3, 1))
    inserted = next(c for c in result if c.clause_id == "§10.5.3A")
    assert "failure to report" in inserted.text
