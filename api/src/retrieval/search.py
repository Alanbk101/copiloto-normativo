"""
Hybrid retrieval: full-text (tsvector/GIN) + vector (pgvector/HNSW),
fused with Reciprocal Rank Fusion.

RRF formula
-----------
score(d) = Σ  1 / (k + rank_i(d))
          lists i

where rank is 1-based and k=60 prevents high-rank outliers from dominating.
A chunk that appears at rank 1 in both lists outscores any chunk that only
appears in one list, regardless of how well it ranks there.

Vector query
------------
Uses Chunk.embedding.cosine_distance(query_embedding) from pgvector's
SQLAlchemy integration.  The embedding travels as a properly typed bind
parameter — no string serialization of floats.

Full-text query
---------------
Uses websearch_to_tsquery('spanish', :question) via SQLAlchemy text() with
a bound parameter.  websearch_to_tsquery tolerates arbitrary user input
(spaces, punctuation, stop words) without raising.
"""

import asyncio
import uuid
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Chunk
from src.embeddings.encoder import encode_query

RRF_K: int = 60
FT_TOP_K: int = 20
VEC_TOP_K: int = 20


@dataclass
class ChunkResult:
    id: uuid.UUID
    document_id: uuid.UUID
    content: str
    structure_path: str
    page_number: int
    score: float


_FT_SQL = text("""
    SELECT
        id,
        document_id,
        content,
        structure_path,
        page_number
    FROM chunks
    WHERE tsv @@ websearch_to_tsquery('spanish', :question)
    ORDER BY ts_rank(tsv, websearch_to_tsquery('spanish', :question)) DESC
    LIMIT :limit
""")


async def _ft_search(
    session: AsyncSession, question: str, limit: int
) -> list[ChunkResult]:
    rows = await session.execute(_FT_SQL, {"question": question, "limit": limit})
    return [
        ChunkResult(
            id=row.id,
            document_id=row.document_id,
            content=row.content,
            structure_path=row.structure_path,
            page_number=row.page_number,
            score=0.0,  # placeholder; replaced by RRF score after fusion
        )
        for row in rows
    ]


async def _vec_search(
    session: AsyncSession, query_embedding: list[float], limit: int
) -> list[ChunkResult]:
    # cosine_distance() is provided by pgvector-python's SQLAlchemy integration.
    # It generates the <=> operator and passes the embedding as a typed bind
    # parameter — no manual serialization to a vector literal string.
    stmt = (
        select(
            Chunk.id,
            Chunk.document_id,
            Chunk.content,
            Chunk.structure_path,
            Chunk.page_number,
        )
        .where(Chunk.embedding.isnot(None))
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    rows = await session.execute(stmt)
    return [
        ChunkResult(
            id=row.id,
            document_id=row.document_id,
            content=row.content,
            structure_path=row.structure_path,
            page_number=row.page_number,
            score=0.0,
        )
        for row in rows
    ]


def _rrf(
    ft_ids: list[uuid.UUID],
    vec_ids: list[uuid.UUID],
    k: int = RRF_K,
) -> list[tuple[uuid.UUID, float]]:
    """
    Reciprocal Rank Fusion over two ranked ID lists.

    Returns (chunk_id, rrf_score) pairs sorted by score descending.
    Chunks that appear in both lists score higher than those in only one.
    """
    scores: dict[uuid.UUID, float] = {}
    for rank, chunk_id in enumerate(ft_ids, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    for rank, chunk_id in enumerate(vec_ids, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


async def hybrid_search(
    session: AsyncSession,
    question: str,
    top_n: int,
) -> list[ChunkResult]:
    """
    Return the top-N most relevant chunks for *question* using hybrid retrieval.

    Embeds the query (via the configured embedding provider), runs full-text
    and vector searches concurrently, fuses ranks with RRF, and returns the
    top-N results with their fusion scores.
    """
    query_embedding: list[float] = await encode_query(question)

    # Sequential — AsyncSession does not support concurrent operations on the
    # same connection.  Both queries are fast index lookups; gather buys nothing.
    ft_results = await _ft_search(session, question, FT_TOP_K)
    vec_results = await _vec_search(session, query_embedding, VEC_TOP_K)

    # Merge metadata from both result sets; vec results overwrite ft on collision
    # (both carry the same data, so order doesn't matter).
    metadata: dict[uuid.UUID, ChunkResult] = {r.id: r for r in ft_results}
    metadata.update({r.id: r for r in vec_results})

    fused = _rrf(
        [r.id for r in ft_results],
        [r.id for r in vec_results],
    )

    results: list[ChunkResult] = []
    for chunk_id, rrf_score in fused[:top_n]:
        chunk = metadata[chunk_id]
        chunk.score = rrf_score
        results.append(chunk)
    return results
