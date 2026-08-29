"""
LLM client interface, Ollama implementation, and Groq implementation.

LLMClient is a Protocol (structural typing) — any object with an async
`generate(prompt)` method satisfies it.  This keeps the generation logic
decoupled from the concrete provider, as required by the architecture rules.

LLMError
--------
Base exception for all LLM provider failures.  answer.py catches this single
type so it stays provider-agnostic.  Each concrete subclass adds context
specific to its provider (timeout values, HTTP status codes, etc.).

OllamaClient
------------
Wraps the Ollama HTTP API ( POST /api/generate ).  Suitable for local
development when a GPU or a patient CPU is available.  read timeout is long
(300 s) to cover cold model load + CPU generation.

GroqClient
----------
Wraps the Groq cloud API using the OpenAI-compatible chat completions endpoint.
Requires a GROQ_API_KEY.  Groq runs inference on custom hardware and typically
responds in 1–3 s, so timeouts are kept short.  No warmup needed.
"""

import logging
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    async def generate(self, prompt: str) -> str: ...


class LLMError(Exception):
    """Base class for all LLM provider errors."""


class OllamaUnavailable(LLMError):
    """Raised when the Ollama service cannot be reached or returns an error."""


class GroqUnavailable(LLMError):
    """Raised when the Groq API cannot be reached or returns an error."""


# ---------------------------------------------------------------------------
# OllamaClient
# ---------------------------------------------------------------------------

_OLLAMA_TIMEOUT = httpx.Timeout(
    connect=10.0,
    write=10.0,
    read=300.0,   # cold model load (~60–120 s) + CPU generation on long prompts
    pool=10.0,
)


class OllamaClient:
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def warmup(self) -> None:
        """
        Load the model into Ollama's RAM before the first real request.

        Sends a minimal prompt so Ollama pulls the model weights into memory.
        Failures are silently ignored — warmup is best-effort.
        """
        try:
            await self.generate("ok")
        except OllamaUnavailable:
            pass  # Ollama may not be up yet; the real call will retry naturally

    async def generate(self, prompt: str) -> str:
        """
        Send *prompt* to Ollama and return the model's response text.

        Raises OllamaUnavailable on any network error, timeout, or non-200
        HTTP status so callers can handle LLM failures without crashing.
        """
        url = f"{self._base_url}/api/generate"
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        }
        logger.debug("Ollama request → %s  model=%s  prompt_len=%d",
                     url, self._model, len(prompt))
        try:
            async with httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                result = data["response"]
                logger.debug("Ollama response ← %d chars", len(result))
                return result
        except httpx.TimeoutException as exc:
            logger.error("Ollama timeout after %.0fs: %s", _OLLAMA_TIMEOUT.read, exc)
            raise OllamaUnavailable(
                f"Ollama did not respond within the timeout ({_OLLAMA_TIMEOUT.read}s)"
            ) from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Ollama HTTP %s — body: %s",
                exc.response.status_code,
                exc.response.text[:500],
            )
            raise OllamaUnavailable(
                f"Ollama returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Ollama request error: %s", exc)
            raise OllamaUnavailable(f"Could not reach Ollama: {exc}") from exc
        except Exception as exc:
            logger.exception("Unexpected error calling Ollama: %s", exc)
            raise OllamaUnavailable(f"Unexpected error: {exc}") from exc


# ---------------------------------------------------------------------------
# GroqClient
# ---------------------------------------------------------------------------

_GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

_GROQ_TIMEOUT = httpx.Timeout(
    connect=10.0,
    write=10.0,
    read=60.0,   # Groq is fast; 60 s is generous for any plausible prompt
    pool=10.0,
)


class GroqClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def generate(self, prompt: str) -> str:
        """
        Send *prompt* to Groq and return the model's response text.

        Uses the OpenAI-compatible chat completions format.
        Raises GroqUnavailable on network errors, timeouts, or API errors
        (including 401 for a bad key and 429 for rate limits).
        """
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
        }
        logger.debug("Groq request  model=%s  prompt_len=%d",
                     self._model, len(prompt))
        try:
            async with httpx.AsyncClient(timeout=_GROQ_TIMEOUT) as client:
                response = await client.post(
                    _GROQ_ENDPOINT, headers=headers, json=payload
                )
                response.raise_for_status()
                data = response.json()
                result: str = data["choices"][0]["message"]["content"]
                logger.debug("Groq response ← %d chars", len(result))
                return result
        except httpx.TimeoutException as exc:
            logger.error("Groq timeout: %s", exc)
            raise GroqUnavailable(
                f"Groq did not respond within {_GROQ_TIMEOUT.read}s"
            ) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 401:
                logger.error("Groq 401 — check GROQ_API_KEY")
                raise GroqUnavailable("Groq rejected the API key (401)") from exc
            if status == 429:
                logger.error("Groq 429 — rate limit exceeded")
                raise GroqUnavailable("Groq rate limit exceeded (429)") from exc
            logger.error("Groq HTTP %s — body: %s", status, exc.response.text[:500])
            raise GroqUnavailable(f"Groq returned HTTP {status}") from exc
        except httpx.RequestError as exc:
            logger.error("Groq request error: %s", exc)
            raise GroqUnavailable(f"Could not reach Groq: {exc}") from exc
        except Exception as exc:
            logger.exception("Unexpected error calling Groq: %s", exc)
            raise GroqUnavailable(f"Unexpected error: {exc}") from exc
