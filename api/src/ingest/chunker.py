"""
Chunker: converts StructuralBlocks into indexable Chunks.

Splitting strategy
------------------
One block → one chunk (primary rule).

If a block's content exceeds MAX_CHARS (≈ 1 000 tokens at ~4 chars/token for
Spanish text), it is split on paragraph boundaries first.  A paragraph that
is itself larger than MAX_CHARS falls back to a hard character split.

All sub-chunks inherit the parent block's structure_path and page_number so
citations remain accurate regardless of how many pieces a long artículo was
broken into.
"""

from src.ingest.models import Chunk, StructuralBlock

_MAX_CHARS: int = 4_000  # ≈ 1 000 tokens


def chunk_document(blocks: list[StructuralBlock]) -> list[Chunk]:
    """Convert structural blocks into Chunks with monotonically increasing indices."""
    chunks: list[Chunk] = []
    chunk_index = 0

    for block in blocks:
        if not block.content.strip():
            # Headings whose body is empty (e.g. a TÍTULO followed immediately
            # by a CAPÍTULO with no descriptive text) produce no chunk.
            continue

        parts = (
            [block.content]
            if len(block.content) <= _MAX_CHARS
            else _split_content(block.content)
        )

        for part in parts:
            chunks.append(
                Chunk(
                    content=part,
                    structure_path=block.structure_path,
                    page_number=block.page_number,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

    return chunks


def _split_content(text: str) -> list[str]:
    """
    Split text into segments of at most MAX_CHARS characters.

    Paragraph breaks (double newline) are preferred split points.
    A paragraph that exceeds MAX_CHARS on its own is hard-split by character.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    result: list[str] = []
    bucket: list[str] = []
    bucket_len = 0

    for para in paragraphs:
        para_len = len(para)

        if para_len > _MAX_CHARS:
            # Flush whatever is in the bucket first.
            if bucket:
                result.append("\n\n".join(bucket))
                bucket, bucket_len = [], 0
            # Hard split of the oversized paragraph.
            for start in range(0, para_len, _MAX_CHARS):
                result.append(para[start : start + _MAX_CHARS])
        elif bucket_len + para_len + 2 > _MAX_CHARS and bucket:
            # Adding this paragraph would overflow — flush and start fresh.
            result.append("\n\n".join(bucket))
            bucket, bucket_len = [para], para_len
        else:
            bucket.append(para)
            bucket_len += para_len + 2  # +2 for the "\n\n" separator

    if bucket:
        result.append("\n\n".join(bucket))

    return result
