"""
RAG answer generation with citations.

answer_question
---------------
Orchestrates the full pipeline:
  1. hybrid_search  → top-N chunks
  2. If no chunks  → return "not found" immediately, no LLM call
  3. Build numbered context (structure_path + page + content)
  4. Generate answer via LLM
  5. Return answer + all retrieved chunks as sources

"Sources" are all retrieved chunks, not only those the model mentioned.
Parsing LLM output to detect which citations were used is fragile; the
frontend renders the full list and the model's inline citations give the user
the mapping.

System prompt
-------------
Loaded once at module import from the adjacent prompts/system.txt file.
Never hardcoded in logic — architecture rule from .cursorrules.

OllamaUnavailable
-----------------
If the LLM call fails (timeout, network error, etc.) answer_question catches
OllamaUnavailable and returns a structured AnswerResult with found=False and
a human-readable message.  The retrieval results are not lost — the caller
can still surface them if desired.
"""

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.generation.llm import LLMClient, OllamaUnavailable
from src.retrieval.search import ChunkResult, hybrid_search

_SYSTEM_PROMPT: str = (
    Path(__file__).parent / "prompts" / "system.txt"
).read_text(encoding="utf-8")

_NOT_FOUND_MSG = "No encontré esta información en los documentos disponibles."
_LLM_ERROR_MSG = (
    "El servicio de generación no está disponible en este momento. "
    "Aquí están los fragmentos más relevantes encontrados en los documentos:"
)

_DEFAULT_TOP_N = 5


@dataclass
class Source:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    structure_path: str
    page_number: int


@dataclass
class AnswerResult:
    answer: str
    sources: list[Source] = field(default_factory=list)
    found: bool = False


def _build_context(chunks: list[ChunkResult]) -> str:
    """Format retrieved chunks into a numbered context block for the prompt."""
    lines: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        lines.append(
            f"[{i}] Ruta: {chunk.structure_path} | Página: {chunk.page_number}\n"
            f"{chunk.content}"
        )
    return "\n\n".join(lines)


def _build_prompt(context: str, question: str) -> str:
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"--- FRAGMENTOS ---\n{context}\n--- FIN FRAGMENTOS ---\n\n"
        f"Pregunta: {question}"
    )


async def answer_question(
    question: str,
    session: AsyncSession,
    llm: LLMClient,
    top_n: int = _DEFAULT_TOP_N,
) -> AnswerResult:
    """
    Answer *question* using hybrid retrieval + LLM generation.

    Returns an AnswerResult with:
    - found=False, empty sources, and a "not found" message if retrieval is empty.
    - found=False, retrieved sources, and an error message if the LLM fails —
      so partial results are not lost even when generation is unavailable.
    - found=True, retrieved sources, and the LLM's answer on success.
    """
    chunks: list[ChunkResult] = await hybrid_search(session, question, top_n)

    if not chunks:
        return AnswerResult(answer=_NOT_FOUND_MSG, sources=[], found=False)

    sources = [
        Source(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            structure_path=chunk.structure_path,
            page_number=chunk.page_number,
        )
        for chunk in chunks
    ]

    context = _build_context(chunks)
    prompt = _build_prompt(context, question)

    try:
        answer = await llm.generate(prompt)
    except OllamaUnavailable:
        # Retrieval succeeded — return sources even though generation failed.
        return AnswerResult(answer=_LLM_ERROR_MSG, sources=sources, found=False)

    return AnswerResult(answer=answer, sources=sources, found=True)
