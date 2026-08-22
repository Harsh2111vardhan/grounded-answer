from src.grounding.citations import extract_citations, validate_citations


def test_extracts_unique_citations_in_order():
    text = (
        "The rule is in §4.3.2. "
        "The same rule is repeated in §4.3.2 and §9.1.4."
    )

    assert extract_citations(text) == ["§4.3.2", "§9.1.4"]


def test_accepts_citations_present_in_evidence():
    answer = "A change must be reported within 10 days (§4.3.2)."

    result = validate_citations(
        answer,
        {"§4.3.2", "§4.3.3"},
    )

    assert result.valid is True
    assert result.invalid_citations == []


def test_rejects_citation_not_in_evidence():
    answer = (
        "A change must be reported within 10 days (§4.3.2). "
        "Another rule applies under §9.1.4."
    )

    result = validate_citations(
        answer,
        {"§4.3.2"},
    )

    assert result.valid is False
    assert result.invalid_citations == ["§9.1.4"]


def test_ignores_non_clause_numbers():
    answer = "There are 10 days to report the change."

    assert extract_citations(answer) == []
