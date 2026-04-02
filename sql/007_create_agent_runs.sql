CREATE TABLE IF NOT EXISTS agent_runs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id    UUID NOT NULL
                      REFERENCES projects(id) ON DELETE CASCADE,

    status        TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    triggered_by  TEXT NOT NULL DEFAULT 'api'
                      CHECK (triggered_by IN ('api', 'schedule')),

    started_at    TIMESTAMPTZ,
    completed_at  TIMESTAMPTZ,
    error_message TEXT,
    output        JSONB,            -- Summary of memory entries written

    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_agent_runs_project
    ON agent_runs(project_id, created_at DESC);