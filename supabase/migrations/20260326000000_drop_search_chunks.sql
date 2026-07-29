-- Suppression de l'ancienne RPC search_chunks (vector-only)
-- Remplacée par search_chunks_hybrid (vector + full-text) depuis la migration 20260325000000
DROP FUNCTION IF EXISTS search_chunks(VECTOR(1536), UUID, INT, FLOAT);
