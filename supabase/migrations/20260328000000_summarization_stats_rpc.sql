-- Index pour les queries sur operation + created_at (monitoring super-admin)
CREATE INDEX IF NOT EXISTS idx_usage_logs_operation
    ON usage_logs(operation, created_at);

-- RPC : KPIs de summarization pour le dashboard super-admin
CREATE OR REPLACE FUNCTION super_admin_summarization_stats()
RETURNS JSON
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
    SELECT json_build_object(
        'total_count', (
            SELECT COUNT(*) FROM usage_logs WHERE operation = 'summarization'
        ),
        'count_24h', (
            SELECT COUNT(*) FROM usage_logs
            WHERE operation = 'summarization'
              AND created_at >= NOW() - INTERVAL '24 hours'
        ),
        'total_cost_usd', (
            SELECT COALESCE(SUM(cost_usd), 0)::NUMERIC(10,4)
            FROM usage_logs WHERE operation = 'summarization'
        ),
        'cost_24h_usd', (
            SELECT COALESCE(SUM(cost_usd), 0)::NUMERIC(10,6)
            FROM usage_logs
            WHERE operation = 'summarization'
              AND created_at >= NOW() - INTERVAL '24 hours'
        ),
        'avg_cost_usd', (
            SELECT COALESCE(AVG(cost_usd), 0)::NUMERIC(10,6)
            FROM usage_logs WHERE operation = 'summarization'
        ),
        'avg_input_tokens', (
            SELECT COALESCE(AVG(input_tokens), 0)::INT
            FROM usage_logs WHERE operation = 'summarization'
        ),
        'avg_output_tokens', (
            SELECT COALESCE(AVG(output_tokens), 0)::INT
            FROM usage_logs WHERE operation = 'summarization'
        )
    );
$$;
