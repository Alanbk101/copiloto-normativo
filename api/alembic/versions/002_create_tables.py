"""create documents, chunks and queries tables"""

from alembic import op

revision = "002_create_tables"
down_revision = "001_enable_vector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE document_status AS ENUM (
            'pending', 'processing', 'completed', 'failed'
        )
    """)

    op.execute("""
        CREATE TABLE documents (
            id            UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
            filename      TEXT            NOT NULL,
            content_hash  TEXT            NOT NULL UNIQUE,
            status        document_status NOT NULL DEFAULT 'pending',
            page_count    INTEGER,
            error_message TEXT,
            created_at    TIMESTAMPTZ     NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ     NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE FUNCTION set_updated_at()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$
    """)

    op.execute("""
        CREATE TRIGGER trg_documents_updated_at
        BEFORE UPDATE ON documents
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)

    op.execute("""
        CREATE TABLE chunks (
            id             UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id    UUID    NOT NULL
                                   REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index    INTEGER NOT NULL,
            content        TEXT    NOT NULL,
            structure_path TEXT    NOT NULL,
            page_number    INTEGER NOT NULL,
            embedding      vector(1536),
            tsv            TSVECTOR GENERATED ALWAYS AS
                               (to_tsvector('spanish', content)) STORED,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE INDEX ix_chunks_hnsw
            ON chunks USING hnsw (embedding vector_cosine_ops)
    """)

    op.execute("""
        CREATE INDEX ix_chunks_tsv
            ON chunks USING gin (tsv)
    """)

    op.execute("""
        CREATE TABLE queries (
            id                  UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
            question            TEXT    NOT NULL,
            answer              TEXT,
            retrieved_chunk_ids UUID[]  NOT NULL DEFAULT '{}',
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS queries")
    op.execute("DROP INDEX IF EXISTS ix_chunks_tsv")
    op.execute("DROP INDEX IF EXISTS ix_chunks_hnsw")
    op.execute("DROP TABLE IF EXISTS chunks")
    op.execute("DROP TRIGGER IF EXISTS trg_documents_updated_at ON documents")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at")
    op.execute("DROP TABLE IF EXISTS documents")
    op.execute("DROP TYPE IF EXISTS document_status")
