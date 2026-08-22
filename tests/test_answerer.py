from src.llm.answerer import PolicyAnswerer
from src.models import Evidence


class FakeGemini:
    def __init__(self):
        self.last_prompt = None
        self.last_system = None

    def generate(
        self,
        prompt,
        system_instruction=None,
        temperature=0.0,
        max_output_tokens=800,
    ):
        self.last_prompt = prompt
        self.last_system = system_instruction
        return "The report must be made within 10 days (§4.3.2)."


def make_evidence():
    return [
        Evidence(
            clause_id="§4.3.2",
            text="A recipient must report a change within 10 calendar days.",
            part="Part 4",
            section="4.3",
            line_no=1,
            retrieval_sources=["bm25", "semantic"],
        )
    ]


def test_answerer_passes_only_supplied_evidence_to_model():
    client = FakeGemini()
    answerer = PolicyAnswerer(client)

    answer = answerer.answer(
        "When must a change be reported?",
        make_evidence(),
    )

    assert "10 days" in answer
    assert "§4.3.2" in client.last_prompt
    assert "general knowledge" in client.last_system
    assert "§9.1.4" not in client.last_prompt


def test_answerer_refuses_without_evidence():
    client = FakeGemini()
    answerer = PolicyAnswerer(client)

    answer = answerer.answer("What is the rule?", [])

    assert "cannot answer" in answer.lower()
    assert client.last_prompt is None
