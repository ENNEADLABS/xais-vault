#!/usr/bin/env bash
set -euo pipefail

if ! command -v psql >/dev/null 2>&1; then
  echo "psql is required. Install PostgreSQL client tools first." >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
database_url="${XAIS_DATABASE_URL:-postgresql://postgres:postgres@127.0.0.1:55322/postgres}"
psql_args=(-X --set ON_ERROR_STOP=1 --dbname "$database_url")

existing_schema="$(psql "${psql_args[@]}" --tuples-only --no-align \
  --command "SELECT to_regclass('public.organizations') IS NOT NULL;")"

if [[ "$existing_schema" == "t" ]]; then
  echo "Refusing to bootstrap a database that already contains XAIS Vault tables." >&2
  echo "Use a fresh Supabase project or run 'supabase db reset' locally first." >&2
  exit 1
fi

apply_sql() {
  local file="$1"
  echo "Applying ${file#"$repo_root/"}"
  psql "${psql_args[@]}" --file "$file"
}

apply_sql "$repo_root/supabase/schema.sql"
apply_sql "$repo_root/supabase/rls.sql"
apply_sql "$repo_root/supabase/storage.sql"

for migration in "$repo_root"/supabase/migrations/*.sql; do
  # schema.sql already contains the knowledge-graph tables and policies from
  # this historical migration. Reapplying it would fail on CREATE TABLE.
  if [[ "$(basename "$migration")" == "20260405000000_knowledge_graph.sql" ]]; then
    echo "Skipping ${migration#"$repo_root/"} (included in schema.sql)"
    continue
  fi
  apply_sql "$migration"
done

echo "XAIS Vault database bootstrap complete."
