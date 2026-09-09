CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    page_count INT NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- `data` is JSONB on purpose: different fact types need different fields
-- (a revenue fact needs unit + time_scope, a director fact needs a date range)
-- and we don't want a schema migration every time a new fact shape shows up.
CREATE TABLE IF NOT EXISTS facts (
    id SERIAL PRIMARY KEY,
    document_id INT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page INT NOT NULL,
    quote TEXT NOT NULL,
    grounded BOOLEAN NOT NULL,
    data JSONB NOT NULL,
    embedding VECTOR(384) NOT NULL,
    search_text TSVECTOR NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS facts_search_idx ON facts USING GIN (search_text);
CREATE INDEX IF NOT EXISTS facts_embedding_idx ON facts USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS relations (
    id SERIAL PRIMARY KEY,
    fact_a_id INT NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
    fact_b_id INT NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,   -- corroborates | contradicts | reconciled
    explanation TEXT NOT NULL,
    confidence REAL NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
