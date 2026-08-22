import pytest

from src.llm.gemini import GeminiClient, DEFAULT_MODEL


def test_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiClient()


def test_default_model():
    assert DEFAULT_MODEL == "gemini-3.6-flash"