from __future__ import annotations

import contextlib
import io
import logging

logging.getLogger("huggingface_hub.utils._http").setLevel(logging.ERROR)

from src.grounding.conflict import ConflictChecker
from src.grounding.entailment import EntailmentChecker
from src.grounding.gate import GroundingGate
from src.grounding.renderer import render_grounding_result
from src.index_builder import create_retriever
from src.llm.answerer import PolicyAnswerer
from src.llm.gemini import GeminiClient


def _quiet_call(function, *args, **kwargs):
    """
    Suppress noisy third-party library output during normal CLI operation.

    Exceptions are not suppressed. They propagate normally so that actual
    application errors can still be handled and displayed.
    """
    stdout = io.StringIO()
    stderr = io.StringIO()

    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        return function(*args, **kwargs)


def build_pipeline():
    retriever = _quiet_call(create_retriever)
    client = GeminiClient()

    answerer = PolicyAnswerer(client)
    entailment_checker = EntailmentChecker(client)
    conflict_checker = ConflictChecker()

    gate = GroundingGate(
        entailment_checker=entailment_checker,
        conflict_checker=conflict_checker,
    )

    return retriever, answerer, gate


def main() -> None:
    print("=" * 70)
    print("GROUNDED ANSWER")
    print("=" * 70)
    print()
    print("Ask a question about the policy manual.")
    print("Type 'exit' or 'quit' to stop.")
    print()

    try:
        retriever, answerer, gate = build_pipeline()
    except Exception as exc:
        print()
        print("ERROR")
        print("────────────────────────────────────────")
        print()
        print(str(exc))
        return

    while True:
        try:
            question = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n")
            break

        if not question:
            continue

        if question.lower() in {"exit", "quit"}:
            print("\nGoodbye.")
            break

        try:
            evidence = _quiet_call(
                retriever.search,
                question,
                top_k=10,
            )

            if not evidence:
                print()
                print("REFUSAL")
                print("────────────────────────────────────────")
                print()
                print(
                    "The supplied policy evidence does not establish "
                    "the answer."
                )
                print()
                print("NEXT STEP")
                print("────────────────────────────────────────")
                print()
                print(
                    "Please contact your local Department district office "
                    "for clarification."
                )
                print()
                continue

            answer = _quiet_call(
                answerer.answer,
                question,
                evidence,
            )

            result = _quiet_call(
                gate.evaluate,
                question,
                answer,
                evidence,
            )

            print()
            print(render_grounding_result(result, evidence))
            print()

        except RuntimeError as exc:
            print()
            print("ERROR")
            print("────────────────────────────────────────")
            print()
            print(str(exc))
            print()

        except Exception as exc:
            print()
            print("ERROR")
            print("────────────────────────────────────────")
            print()
            print(f"{type(exc).__name__}: {exc}")
            print()


if __name__ == "__main__":
    main()