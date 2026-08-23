from __future__ import annotations

import json
import sys
from pathlib import Path

from src.grounding.conflict import ConflictChecker
from src.grounding.entailment import EntailmentChecker
from src.grounding.gate import GroundingDecision, GroundingGate
from src.grounding.renderer import render_grounding_result
from src.index_builder import create_retriever
from src.llm.answerer import PolicyAnswerer
from src.llm.gemini import GeminiClient


QUESTIONS_FILE = Path(__file__).parent / "questions.json"


def load_questions() -> list[dict]:
    with QUESTIONS_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_pipeline():
    retriever = create_retriever()
    client = GeminiClient()

    answerer = PolicyAnswerer(client)
    entailment_checker = EntailmentChecker(client)
    conflict_checker = ConflictChecker()

    gate = GroundingGate(
        entailment_checker=entailment_checker,
        conflict_checker=conflict_checker,
    )

    return retriever, answerer, gate


def classify(decision: GroundingDecision) -> str:
    return decision.value


def run_question(
    question: str,
    retriever,
    answerer,
    gate,
) -> tuple[str, str]:
    evidence = retriever.search(
        question,
        top_k=5,
    )

    if not evidence:
        return (
            "REFUSE",
            "No relevant policy evidence was retrieved.",
        )

    answer = answerer.answer(
        question,
        evidence,
    )

    result = gate.evaluate(
        question,
        answer,
        evidence,
    )

    return classify(result.decision), answer


def run_evaluation() -> int:
    questions = load_questions()

    retriever, answerer, gate = build_pipeline()

    passed = 0

    print("=" * 70)
    print("GROUNDED ANSWER EVALUATION")
    print("=" * 70)

    for item in questions:
        question_id = item["id"]
        question = item["question"]
        expected = item["expected"]

        actual, answer = run_question(
            question,
            retriever,
            answerer,
            gate,
        )

        success = actual == expected

        if success:
            passed += 1

        print()
        print("=" * 70)
        print(question_id)
        print("=" * 70)

        print("\nQUESTION:")
        print(question)

        print("\nEXPECTED:")
        print(expected)

        print("\nACTUAL DECISION:")
        print(actual)

        print("\nANSWER:")
        print(answer)

        print("\nRESULT:")
        print("PASS" if success else "FAIL")

    total = len(questions)
    percentage = (passed / total) * 100

    print()
    print("=" * 70)
    print(f"RESULT: {passed}/{total} passed ({percentage:.1f}%)")
    print("=" * 70)

    return 0 if passed == total else 1


def run_cli(question: str) -> int:
    retriever, answerer, gate = build_pipeline()

    evidence = retriever.search(
        question,
        top_k=5,
    )

    if not evidence:
        print("\nREFUSAL")
        print("────────────────────────────────────────")
        print()
        print(
            "The supplied policy evidence does not establish the answer."
        )
        print()
        print("NEXT STEP")
        print("────────────────────────────────────────")
        print()
        print(
            "Please contact your local Department district office "
            "for clarification."
        )
        return 0

    answer = answerer.answer(
        question,
        evidence,
    )

    result = gate.evaluate(
        question,
        answer,
        evidence,
    )

    print()
    print(render_grounding_result(result, evidence))

    return 0


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--eval":
        raise SystemExit(run_evaluation())

    if len(sys.argv) < 2:
        print('Usage: python -m eval.run "your question"')
        print("       python -m eval.run --eval")
        raise SystemExit(1)

    question = " ".join(sys.argv[1:]).strip()

    raise SystemExit(run_cli(question))


if __name__ == "__main__":
    main()