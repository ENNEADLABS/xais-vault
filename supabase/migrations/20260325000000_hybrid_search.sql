-- RAG v2 : Hybrid Search (vector + full-text)
-- Ajoute tsvector sur chunks + 2 RPCs (hybrid + fulltext fallback)

-- Colonne tsvector auto-générée (stemming français + anglais via simple)
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS fts tsvector
  GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(section_title, '') || ' ' || content)
  ) STORED;

-- Index GIN pour le full-text search
CREATE INDEX IF NOT EXISTS idx_chunks_fts ON chunks USING gin(fts);

-- RPC hybrid : combine vector cosine + full-text ts_rank
CREATE OR REPLACE FUNCTION search_chunks_hybrid(
    query_embedding VECTOR(1536),
    query_text TEXT,
    target_deal_id UUID,
    match_count INT DEFAULT 15,
    similarity_threshold FLOAT DEFAULT 0.3,
    vector_weight FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    id UUID,
    source_id UUID,
    content TEXT,
    chunk_index INT,
    page_number INT,
    section_title TEXT,
    similarity FLOAT,
    fts_rank FLOAT,
    combined_score FLOAT
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
    ts_query tsquery;
    fts_weight FLOAT := 1.0 - vector_weight;
BEGIN
    ts_query := plainto_tsquery('simple', query_text);

    RETURN QUERY
    WITH vector_results AS (
        SELECT
            c.id,
            c.source_id,
            c.content,
            c.chunk_index,
            c.page_number,
            c.section_title,
            (1 - (c.embedding <=> query_embedding)) AS vec_score,
            CASE WHEN c.fts @@ ts_query
                 THEN ts_rank(c.fts, ts_query, 32)
                 ELSE 0.0
            END AS text_score
        FROM chunks c
        WHERE c.deal_id = target_deal_id
    ),
    scored AS (
        SELECT
            vr.*,
            (vector_weight * vr.vec_score + fts_weight * vr.text_score) AS combined
        FROM vector_results vr
        WHERE vr.vec_score > similarity_threshold
           OR vr.text_score > 0
    )
    SELECT
        s.id,
        s.source_id,
        s.content,
        s.chunk_index,
        s.page_number,
        s.section_title,
        s.vec_score::FLOAT AS similarity,
        s.text_score::FLOAT AS fts_rank,
        s.combined::FLOAT AS combined_score
    FROM scored s
    ORDER BY s.combined DESC
    LIMIT match_count;
END;
$$;

-- RPC fallback full-text (quand hybrid retourne 0)
CREATE OR REPLACE FUNCTION search_chunks_fulltext(
    query_text TEXT,
    target_deal_id UUID,
    match_count INT DEFAULT 15
)
RETURNS TABLE (
    id UUID,
    source_id UUID,
    content TEXT,
    chunk_index INT,
    page_number INT,
    section_title TEXT,
    similarity FLOAT,
    fts_rank FLOAT,
    combined_score FLOAT
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, extensions
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.source_id,
        c.content,
        c.chunk_index,
        c.page_number,
        c.section_title,
        0.0::FLOAT AS similarity,
        ts_rank(c.fts, plainto_tsquery('simple', query_text), 32)::FLOAT AS fts_rank,
        ts_rank(c.fts, plainto_tsquery('simple', query_text), 32)::FLOAT AS combined_score
    FROM chunks c
    WHERE c.deal_id = target_deal_id
      AND c.fts @@ plainto_tsquery('simple', query_text)
    ORDER BY fts_rank DESC
    LIMIT match_count;
END;
$$;
