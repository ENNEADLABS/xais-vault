-- Chat History Summarization — résumé des longues conversations
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS history_summary TEXT;
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS history_summary_until UUID;
