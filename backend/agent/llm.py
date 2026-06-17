from __future__ import annotations

import os

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


class MissingApiKeyError(RuntimeError):
    """Raised when GOOGLE_API_KEY is not configured on the backend."""


def get_llm(temperature: float = 0.2):
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise MissingApiKeyError(
            "GOOGLE_API_KEY is not set. Add it to the backend .env file or the environment "
            "before running the API server."
        )

    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=DEFAULT_MODEL,
        temperature=temperature,
        google_api_key=api_key,
    )
