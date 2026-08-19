"""resize chunks.embedding from vector(1536) to vector(1024) for multilingual-e5-large"""

from alembic import op

revision = "003_resize_embedding"
down_revision = "002_create_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # vector dimensions cannot be altered in-place; drop and re-add with the new size
    op.execute("DROP INDEX IF EXISTS ix_chunks_hnsw")
    op.execute("ALTER TABLE chunks DROP COLUMN embedding")
    op.execute("ALTER TABLE chunks ADD COLUMN embedding vector(1024)")
    op.execute(
        "CREATE INDEX ix_chunks_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_hnsw")
    op.execute("ALTER TABLE chunks DROP COLUMN embedding")
    op.execute("ALTER TABLE chunks ADD COLUMN embedding vector(1536)")
    op.execute(
        "CREATE INDEX ix_chunks_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)"
    )
