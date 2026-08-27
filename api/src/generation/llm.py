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
Only the read timeout needs to be long.  The first call to Ollama also loads
the model into RAM (several GB on CPU), which can take 60–120 s before the
first token appears.  Subsequent calls are faster (model stays hot) but
generation itself on CPU still takes 30–90 s for a 3B model with a legal
prompt.  We set read=180 s to cover both the cold-load and generation cost.
Connection, write, and pool timeouts stay short (5–10 s) because those
phases are not compute-bound and a long wait there indicates a real failure.

Error handling
--------------
Any httpx error (network failure, timeout, non-200 response) raises
OllamaUnavailable.  The caller — answer_question — catches it and returns
a structured AnswerResult instead of letting a raw exception reach the
client as a 500.
"""

import logging
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    async def generate(self, prompt: str) -> str: ...


class OllamaUnavailable(Exception):
    """Raised when the Ollama service cannot be reached or returns an error."""


_TIMEOUT = httpx.Timeout(
    connect=10.0,  # Ollama is local — if connect takes >10 s it is down
    write=10.0,
    read=300.0,    # cold model load (~60–120 s) + CPU generation on long prompts
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
        Subsequent calls pay only the generation cost, not the load cost.
        Failures are silently ignored — warmup is best-effort; if Ollama is
        not ready yet the first real /ask call will still work (just slower).
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
            "stream": False,  # wait for the full response before returning
        }
        logger.debug("Ollama request → %s  model=%s  prompt_len=%d",
                     url, self._model, len(prompt))
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                result = data["response"]
                logger.debug("Ollama response ← %d chars", len(result))
                return result
        except httpx.TimeoutException as exc:
            logger.error("Ollama timeout after %.0fs: %s", _TIMEOUT.read, exc)
            raise OllamaUnavailable(
                f"Ollama did not respond within the timeout ({_TIMEOUT.read}s)"
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
