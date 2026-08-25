"""
LLM client interface and Ollama implementation.

LLMClient is a Protocol (structural typing) — any object with an async
`generate(prompt)` method satisfies it.  This keeps the generation logic
decoupled from the concrete provider, as required by the architecture rules.

OllamaClient
------------
Wraps the Ollama HTTP API ( POST /api/generate ).  Uses httpx.AsyncClient
so the FastAPI event loop is never blocked while waiting for the model.

Timeout
-------
CPU inference for a 3B model takes 10–40 s depending on prompt length.
We set a 60 s read timeout to cover slow hardware while still failing fast
if Ollama crashes or hangs.  Connection and write timeouts remain short
(5 s) because those phases are not CPU-bound.

Error handling
--------------
Any httpx error (network failure, timeout, non-200 response) raises
OllamaUnavailable.  The caller — answer_question — catches it and returns
a structured AnswerResult instead of letting a raw exception reach the
client as a 500.
"""

from typing import Protocol

import httpx


class LLMClient(Protocol):
    async def generate(self, prompt: str) -> str: ...


class OllamaUnavailable(Exception):
    """Raised when the Ollama service cannot be reached or returns an error."""


_TIMEOUT = httpx.Timeout(
    connect=5.0,
    write=5.0,
    read=60.0,   # generation on CPU can take up to ~40 s for a 3B model
    pool=5.0,
)


class OllamaClient:
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def generate(self, prompt: str) -> str:
        """
        Send *prompt* to Ollama and return the model's response text.

        Raises OllamaUnavailable on any network error, timeout, or non-200
        HTTP status so callers can handle LLM failures without crashing.
        """
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,  # wait for the full response before returning
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.post(
                    f"{self._base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise OllamaUnavailable(
                f"Ollama did not respond within the timeout ({_TIMEOUT.read}s)"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaUnavailable(
                f"Ollama returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise OllamaUnavailable(f"Could not reach Ollama: {exc}") from exc

        return response.json()["response"]
