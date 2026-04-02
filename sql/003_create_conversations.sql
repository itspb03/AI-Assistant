CREATE TABLE IF NOT EXISTS conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID NOT NULL
                    REFERENCES projects(id) ON DELETE CASCADE,
    title       TEXT,               -- Auto-set from first user message (optional)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_conversations_project
    ON conversations(project_id, created_at DESC);