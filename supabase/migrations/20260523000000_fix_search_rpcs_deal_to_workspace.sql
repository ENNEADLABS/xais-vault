-- Fix search RPCs: rename deal_id → workspace_id (Phase 3 pivot followup)
-- The Phase 3 migration renamed the column but missed these RPC definitions.

-- pgvector type must be visible at function creation time
SET search_path = public, extensions;

-- DROP old signatures (param rename not allowed by CREATE OR REPLACE)
DROP FUNCTION IF EXISTS search_chunks_hybrid(VECTOR(1536), TEXT, UUID, INT, FLOAT, FLOAT);
DROP FUNCTION IF EXISTS search_chunks_fulltext(TEXT, UUID, INT);
DROP FUNCTION IF EXISTS search_graph_chunks(VECTOR(1536), UUID, INT, FLOAT);

-- 1. search_chunks_hybrid
CREATE OR REPLACE FUNCTION search_chunks_hybrid(
    query_embedding VECTOR(1536),
    query_text TEXT,
    target_workspace_id UUID,
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
        WHERE c.workspace_id = target_workspace_id
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

-- 2. search_chunks_fulltext
CREATE OR REPLACE FUNCTION search_chunks_fulltext(
    query_text TEXT,
    target_workspace_id UUID,
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
    WHERE c.workspace_id = target_workspace_id
      AND c.fts @@ plainto_tsquery('simple', query_text)
    ORDER BY fts_rank DESC
    LIMIT match_count;
END;
$$;

-- 3. search_graph_chunks
CREATE OR REPLACE FUNCTION search_graph_chunks(
    query_embedding VECTOR(1536),
    target_workspace_id UUID,
    match_count INT DEFAULT 30,
    entity_similarity_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    chunk_id UUID,
    content TEXT,
    source_id UUID,
    page_number INT,
    section_title TEXT,
    graph_score FLOAT,
    matched_entities TEXT[]
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    WITH
    candidate_entities AS (
        SELECT
            e.id AS entity_id,
            e.name AS entity_name,
            1 - (e.embedding <=> query_embedding) AS entity_similarity
        FROM entities e
        WHERE e.workspace_id = target_workspace_id
          AND e.embedding IS NOT NULL
          AND 1 - (e.embedding <=> query_embedding) > entity_similarity_threshold
        ORDER BY e.embedding <=> query_embedding
        LIMIT 20
    ),
    related_entities AS (
        SELECT DISTINCT
            er.target_entity_id AS entity_id,
            ce.entity_name AS via_entity,
            ce.entity_similarity * er.confidence AS propagated_score
        FROM candidate_entities ce
        JOIN entity_relations er ON er.source_entity_id = ce.entity_id
        WHERE er.workspace_id = target_workspace_id

        UNION

        SELECT DISTINCT
            er.source_entity_id AS entity_id,
            ce.entity_name AS via_entity,
            ce.entity_similarity * er.confidence * 0.8 AS propagated_score
        FROM candidate_entities ce
        JOIN entity_relations er ON er.target_entity_id = ce.entity_id
        WHERE er.workspace_id = target_workspace_id
    ),
    all_entities AS (
        SELECT entity_id, entity_name AS matched_entity, entity_similarity AS score
        FROM candidate_entities
        UNION ALL
        SELECT entity_id, via_entity AS matched_entity, propagated_score AS score
        FROM related_entities
    ),
    scored_chunks AS (
        SELECT
            ce.chunk_id,
            SUM(ae.score) AS total_graph_score,
            ARRAY_AGG(DISTINCT ae.matched_entity) AS entities_matched
        FROM chunk_entities ce
        JOIN all_entities ae ON ae.entity_id = ce.entity_id
        GROUP BY ce.chunk_id
    )
    SELECT
        sc.chunk_id,
        c.content,
        c.source_id,
        c.page_number,
        c.section_title,
        sc.total_graph_score AS graph_score,
        sc.entities_matched AS matched_entities
    FROM scored_chunks sc
    JOIN chunks c ON c.id = sc.chunk_id
    WHERE c.workspace_id = target_workspace_id
    ORDER BY sc.total_graph_score DESC
    LIMIT match_count;
END;
$$;
