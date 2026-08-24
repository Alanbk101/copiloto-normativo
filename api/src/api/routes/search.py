import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.engine import get_db_session
from src.retrieval.search import hybrid_search

router = APIRouter(prefix="/search", tags=["search"])

_DEFAULT_TOP_K = 5


class SearchRequest(BaseModel):
    question: str
    top_k: int = Field(default=_DEFAULT_TOP_K, ge=1, le=20)


class ChunkResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    content: str
    structure_path: str
    page_number: int
    score: float


@router.post("", response_model=list[ChunkResponse])
async def search(
    body: SearchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> list[ChunkResponse]:
    """
    Hybrid search: returns the top-k most relevant chunks for the given question.

    Uses full-text (tsvector/GIN) + vector (pgvector/HNSW) search fused with
    Reciprocal Rank Fusion.  Returns an empty list when no chunks match —
    never raises a 404.
    """
    results = await hybrid_search(session, body.question, body.top_k)
    return [
        ChunkResponse(
            id=r.id,
            document_id=r.document_id,
            content=r.content,
            structure_path=r.structure_path,
            page_number=r.page_number,
            score=r.score,
        )
        for r in results
    ]
