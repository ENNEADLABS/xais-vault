-- RPC : agrégation usage_logs par mois et type d'opération.
-- Appelé depuis le service admin_stats.py.
--
-- Usage Python:
--   db.rpc("admin_usage_by_month", {"target_org_id": org_id, "month_count": 6}).execute()

CREATE OR REPLACE FUNCTION admin_usage_by_month(
    target_org_id UUID,
    month_count INT DEFAULT 6
)
RETURNS TABLE (
    month TEXT,
    operation TEXT,
    count BIGINT,
    input_tokens BIGINT,
    output_tokens BIGINT,
    cost_usd NUMERIC
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        to_char(date_trunc('month', ul.created_at), 'YYYY-MM') AS month,
        ul.operation,
        COUNT(*)::BIGINT AS count,
        COALESCE(SUM(ul.input_tokens), 0)::BIGINT AS input_tokens,
        COALESCE(SUM(ul.output_tokens), 0)::BIGINT AS output_tokens,
        COALESCE(SUM(ul.cost_usd), 0::NUMERIC) AS cost_usd
    FROM usage_logs ul
    WHERE ul.organization_id = target_org_id
      AND ul.created_at >= date_trunc('month', now()) - ((month_count - 1) || ' months')::INTERVAL
    GROUP BY date_trunc('month', ul.created_at), ul.operation
    ORDER BY date_trunc('month', ul.created_at) DESC, ul.operation;
END;
$$;
