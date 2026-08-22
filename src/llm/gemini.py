from __future__ import annotations

import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

DEFAULT_MODEL = "gemini-3.6-flash"


class GeminiClient:
    """Small wrapper around the Google Gen AI SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Add it to your environment or .env file."
            )

        self.model = model
        self.client = genai.Client(api_key=self.api_key)

    def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        max_output_tokens: int = 800,
    ) -> str:
        config = types.GenerateContentConfig(
            max_output_tokens=max_output_tokens,
        )

        if system_instruction:
            config.system_instruction = system_instruction

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
        except Exception as exc:
            # Google Gen AI raises ClientError for quota/rate-limit errors.
            # Don't retry these ourselves. The SDK already handles its own
            # retry behavior, and retrying a 429 just wastes quota.
            if getattr(exc, "code", None) == 429 or "429" in str(exc):
                raise RuntimeError(
                    "Gemini API quota/rate limit reached. "
                    "Please wait before trying again."
                ) from exc

            raise

        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")

        return response.text.strip()