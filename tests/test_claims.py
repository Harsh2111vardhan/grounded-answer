from src.grounding.claims import extract_claims, find_uncited_sentences


def test_extracts_claim_and_citation():
    answer = (
        "A full-time student is classified as full-time by the institution "
        "§1.4.6."
    )
    claims = extract_claims(answer)
    assert len(claims) == 1
    assert claims[0].citation == "§1.4.6"
    assert "full-time student" in claims[0].text


def test_creates_one_claim_per_citation():
    answer = "The rule is described in §4.3.2 and confirmed by §9.1.4."
    claims = extract_claims(answer)
    assert [claim.citation for claim in claims] == ["§4.3.2", "§9.1.4"]


def test_finds_uncited_sentences():
    answer = (
        "The recipient must report the change §4.3.2. "
        "Ask the supervisor if the situation is unclear."
    )
    assert find_uncited_sentences(answer) == [
        "Ask the supervisor if the situation is unclear."
    ]
