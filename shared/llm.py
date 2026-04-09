"""
Shared LLM factory. Auto-detects which provider to use based on available env vars.

Priority:
  1. GROQ_API_KEY    → uses Llama 3.3 70B via Groq (FREE, 14k req/day, no credit card)
  2. GOOGLE_API_KEY  → uses Gemini 2.0 Flash (free tier, but project must have quota)
  3. OPENAI_API_KEY  → uses GPT-4o (requires billing)

Set whichever key you have in .env — nothing else needs to change.

Rate limit handling: We wrap every call with a retry that waits 30s on a 429
before trying again (up to 3 retries).
"""

import os
import time
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _make_groq(temperature: float, groq_key: str):
    from langchain_groq import ChatGroq
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    return ChatGroq(
        model=model,
        temperature=temperature,
        api_key=groq_key,
    )


def _make_gemini(temperature: float, google_key: str):
    from langchain_google_genai import ChatGoogleGenerativeAI
    model = os.environ.get("GOOGLE_MODEL", "gemini-2.0-flash")
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        google_api_key=google_key,
    )


def _make_openai(temperature: float, openai_key: str):
    from langchain_openai import ChatOpenAI
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=openai_key,
    )


class RetryLLM:
    """
    Thin wrapper that retries on 429 / quota errors.
    Groq free tier is very generous — this is mostly a safety net.
    """

    def __init__(self, llm, provider: str, max_retries: int = 3, wait_seconds: int = 30):
        self._llm = llm
        self._provider = provider
        self._max_retries = max_retries
        self._wait = wait_seconds

    def invoke(self, messages):
        for attempt in range(self._max_retries):
            try:
                return self._llm.invoke(messages)
            except Exception as e:
                err = str(e)
                is_rate_limit = "429" in err or "RESOURCE_EXHAUSTED" in err or "rate_limit" in err.lower()
                if is_rate_limit and attempt < self._max_retries - 1:
                    wait = self._wait * (attempt + 1)
                    print(f"  [rate limit] waiting {wait}s before retry {attempt + 1}/{self._max_retries - 1}...")
                    time.sleep(wait)
                else:
                    raise


def get_llm(temperature: float = 0.3) -> RetryLLM:
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    google_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()

    if groq_key:
        print(f"  [llm] using Groq (llama-3.3-70b)")
        return RetryLLM(_make_groq(temperature, groq_key), provider="groq")
    elif google_key:
        print(f"  [llm] using Google Gemini")
        return RetryLLM(_make_gemini(temperature, google_key), provider="gemini")
    elif openai_key:
        print(f"  [llm] using OpenAI")
        return RetryLLM(_make_openai(temperature, openai_key), provider="openai")
    else:
        raise EnvironmentError(
            "No LLM API key found. Set one of these in .env:\n"
            "  GROQ_API_KEY   (free) → https://console.groq.com  ← recommended\n"
            "  GOOGLE_API_KEY (free) → https://aistudio.google.com/app/apikey\n"
            "  OPENAI_API_KEY (paid) → https://platform.openai.com/api-keys"
        )


