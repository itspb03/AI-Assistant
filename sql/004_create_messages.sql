-- Stores all four turn types needed to reconstruct
-- the exact Claude Messages API history:
--   user        → human turn
--   assistant   → Claude's text response
--   tool_use    → Claude requested a tool
--   tool_result → backend returned tool output

CREATE TABLE IF NOT EXISTS messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL
                        REFERENCES conversations(id) ON DELETE CASCADE,
    project_id      UUID NOT NULL
                        REFERENCES projects(id) ON DELETE CASCADE,

    role            TEXT NOT NULL
                        CHECK (role IN ('user', 'assistant', 'tool_use', 'tool_result')),

    -- For user / assistant turns
    content         TEXT,

    -- For tool_use rows (Claude → backend)
    tool_name       TEXT,
    tool_use_id     TEXT,           -- Claude's own ID for the call
    tool_input      JSONB,

    -- For tool_result rows (backend → Claude)
    tool_output     JSONB,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_conversation
    ON messages(conversation_id, created_at ASC);

CREATE INDEX idx_messages_project
    ON messages(project_id, created_at DESC);