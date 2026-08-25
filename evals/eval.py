"""
Retrieval evaluation script.

Measures recall@K: for each question, did hybrid_search return at least one
chunk whose content contains one of the expected keywords?

This metric is objective and independent of LLM quality — it tests the
retrieval pipeline (embeddings + full-text + RRF), which is what can actually
be debugged and improved.

Usage
-----
    # From the repo root, with the stack running:
    docker compose exec api python evals/eval.py

    # Or with a custom K:
    docker compose exec api python evals/eval.py --top-k 10

    # Save report to file:
    docker compose exec api python evals/eval.py --out evals/results.txt

Notes
-----
- With an empty database the recall will be 0% for all K. That is expected.
  Load documents first with POST /documents, then re-run.
- The script connects to the same DB used by the API (DATABASE_URL from env).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from src.config import settings  # noqa: E402
from src.retrieval.search import ChunkResult, hybrid_search  # noqa: E402

_QUESTIONS_FILE = Path(__file__).parent / "questions.json"
_DEFAULT_K_VALUES = [1, 3, 5]


def _hit(chunks: list[ChunkResult], keywords: list[str]) -> bool:
    """Return True if any chunk contains at least one expected keyword (case-insensitive)."""
    for chunk in chunks:
        content_lower = chunk.content.lower()
        if any(kw.lower() in content_lower for kw in keywords):
            return True
    return False


async def _evaluate(top_k: int) -> None:
    questions = json.loads(_QUESTIONS_FILE.read_text(encoding="utf-8"))

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    # hits[k] = number of questions with a hit in top-k
    hits: dict[int, int] = {k: 0 for k in _DEFAULT_K_VALUES if k <= top_k}
    failures: list[str] = []

    async with factory() as session:
        session: AsyncSession
        for q in questions:
            qid = q["id"]
            question = q["question"]
            keywords = q["expected_keywords"]

            # Patch encode_query to avoid loading the 2 GB model when running
            # with --dry-run or from CI without the model downloaded.
            # In normal eval usage the model must be present.
            try:
                chunks = await hybrid_search(session, question, top_k)
            except Exception as exc:
                print(f"  ERROR on {qid}: {exc}", file=sys.stderr)
                failures.append(qid)
                continue

            top_k_hit = _hit(chunks, keywords)
            if not top_k_hit:
                failures.append(qid)

            for k in hits:
                if _hit(chunks[:k], keywords):
                    hits[k] += 1

    total = len(questions)

    print(f"\n{'═' * 50}")
    print(f"  Retrieval Evaluation — {_QUESTIONS_FILE.name}")
    print(f"  Total questions: {total}")
    print(f"{'─' * 50}")
    for k in sorted(hits):
        recall = hits[k] / total if total else 0.0
        print(f"  Recall@{k:<2}  {hits[k]:>3}/{total}  ({recall:.0%})")
    print(f"{'─' * 50}")

    if failures:
        print(f"  Failed questions ({len(failures)}):")
        for qid in failures:
            matched = next(q for q in questions if q["id"] == qid)
            print(f"    [{qid}] {matched['question'][:70]}")
    else:
        print("  All questions found in top results.")

    print(f"{'═' * 50}\n")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval recall@K")
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Maximum number of chunks to retrieve per question (default: 5)",
    )
    args = parser.parse_args()
    asyncio.run(_evaluate(args.top_k))


if __name__ == "__main__":
    main()
