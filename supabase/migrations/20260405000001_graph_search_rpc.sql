-- =============================================================
-- Graph Search RPC — recherche de chunks via le knowledge graph
-- RAG v3 : traversée entités → relations → chunks connectés
-- =============================================================

CREATE OR REPLACE FUNCTION search_graph_chunks(
    query_embedding VECTOR(1536),
    target_deal_id UUID,
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
    -- 1. Trouver les entités proches de la query (vector similarity)
    candidate_entities AS (
        SELECT
            e.id AS entity_id,
            e.name AS entity_name,
            1 - (e.embedding <=> query_embedding) AS entity_similarity
        FROM entities e
        WHERE e.deal_id = target_deal_id
          AND e.embedding IS NOT NULL
          AND 1 - (e.embedding <=> query_embedding) > entity_similarity_threshold
        ORDER BY e.embedding <=> query_embedding
        LIMIT 20
    ),

    -- 2. Traverser les relations (1 hop) pour trouver les entités liées
    related_entities AS (
        SELECT DISTINCT
            er.target_entity_id AS entity_id,
            ce.entity_name AS via_entity,
            ce.entity_similarity * er.confidence AS propagated_score
        FROM candidate_entities ce
        JOIN entity_relations er ON er.source_entity_id = ce.entity_id
        WHERE er.deal_id = target_deal_id

        UNION

        SELECT DISTINCT
            er.source_entity_id AS entity_id,
            ce.entity_name AS via_entity,
            ce.entity_similarity * er.confidence * 0.8 AS propagated_score
        FROM candidate_entities ce
        JOIN entity_relations er ON er.target_entity_id = ce.entity_id
        WHERE er.deal_id = target_deal_id
    ),

    -- 3. Combiner entités directes et liées
    all_entities AS (
        SELECT entity_id, entity_name AS matched_entity, entity_similarity AS score
        FROM candidate_entities

        UNION ALL

        SELECT entity_id, via_entity AS matched_entity, propagated_score AS score
        FROM related_entities
    ),

    -- 4. Récupérer les chunks liés via chunk_entities
    scored_chunks AS (
        SELECT
            ce.chunk_id,
            SUM(ae.score) AS total_graph_score,
            ARRAY_AGG(DISTINCT ae.matched_entity) AS entities_matched
        FROM chunk_entities ce
        JOIN all_entities ae ON ae.entity_id = ce.entity_id
        GROUP BY ce.chunk_id
    )

    -- 5. Joindre avec chunks pour le contenu
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
    WHERE c.deal_id = target_deal_id
    ORDER BY sc.total_graph_score DESC
    LIMIT match_count;
END;
$$;


-- =============================================================
-- Helper RPC — compter les mentions d'entités dans les chunks
-- =============================================================

CREATE OR REPLACE FUNCTION get_entity_mention_counts(entity_ids UUID[])
RETURNS TABLE (entity_id UUID, total_mentions BIGINT)
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT
        ce.entity_id,
        SUM(ce.mention_count)::BIGINT AS total_mentions
    FROM chunk_entities ce
    WHERE ce.entity_id = ANY(entity_ids)
    GROUP BY ce.entity_id;
$$;
