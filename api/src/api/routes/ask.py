"""
POST /ask — RAG question-answering endpoint.

Injects the LLMClient from app.state (set in lifespan) so tests can swap
it for a mock without touching the route logic.
"""

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.engine import get_db_session
from src.generation.answer import AnswerResult, answer_question
from src.generation.llm import LLMClient

router = APIRouter(tags=["ask"])


class AskRequest(BaseModel):
    question: str


class SourceResponse(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    structure_path: str
    page_number: int


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
    found: bool


@router.post("/ask", response_model=AskResponse)
async def ask(
    body: AskRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> AskResponse:
    """
    Answer a question using hybrid retrieval + LLM generation.

    - found=True  → LLM answered using retrieved chunks; sources are cited inline.
    - found=False → either no relevant chunks exist, or the LLM was unavailable.
                    In the latter case sources may still be populated so the
                    client can display the relevant fragments directly.
    """
    llm: LLMClient = request.app.state.llm
    result: AnswerResult = await answer_question(body.question, session, llm)

    return AskResponse(
        answer=result.answer,
        sources=[
            SourceResponse(
                chunk_id=s.chunk_id,
                document_id=s.document_id,
                structure_path=s.structure_path,
                page_number=s.page_number,
            )
            for s in result.sources
        ],
        found=result.found,
    )
