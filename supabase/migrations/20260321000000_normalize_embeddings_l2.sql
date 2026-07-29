-- Migration : normalisation L2 des embeddings existants
-- Contexte : Gemini Embedding 2 en dims < 3072 retourne des vecteurs non normalisés.
-- Depuis l'implémentation de la normalisation L2 dans le provider (packages/llm/gemini_embeddings.py),
-- les nouveaux embeddings sont normalisés. Ce script normalise les vecteurs existants pour cohérence.
--
-- Idempotent : normaliser un vecteur déjà normalisé est un no-op (||v|| ≈ 1.0 → v/1.0 = v).

-- Inclure le schéma extensions (pgvector) dans le search_path
SET search_path TO public, extensions;

-- Fonction temporaire de normalisation L2
CREATE OR REPLACE FUNCTION _tmp_normalize_l2(v vector)
RETURNS vector
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
  arr float[];
  norm float;
  i int;
BEGIN
  -- vector ne cast pas directement en float[] — passer par text
  arr := string_to_array(trim(both '[]' from v::text), ',')::float[];
  norm := 0;
  FOR i IN 1..array_length(arr, 1) LOOP
    norm := norm + arr[i] * arr[i];
  END LOOP;
  norm := sqrt(norm);
  IF norm = 0 THEN
    RETURN v;
  END IF;
  FOR i IN 1..array_length(arr, 1) LOOP
    arr[i] := arr[i] / norm;
  END LOOP;
  RETURN arr::vector;
END;
$$;

-- Normaliser tous les vecteurs existants
UPDATE chunks
SET embedding = _tmp_normalize_l2(embedding)
WHERE embedding IS NOT NULL;

-- Nettoyage
DROP FUNCTION _tmp_normalize_l2(vector);
