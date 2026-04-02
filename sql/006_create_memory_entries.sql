-- This table is a DB-side manifest of what's in the memory_store/ files.
-- The file system is the source of truth.
-- This table enables fast lookup, filtering, and listing without reading files.

CREATE TABLE IF NOT EXISTS memory_entries (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID NOT NULL
                    REFERENCES projects(id) ON DELETE CASCADE,

    category    TEXT NOT NULL
                    CHECK (category IN ('context', 'decision', 'entity', 'constraint')),
    key         TEXT NOT NULL,      -- e.g. "target_platform", "chosen_stack"
    summary     TEXT NOT NULL,      -- 1-2 sentence human-readable summary
    detail      JSONB,              -- Full structured data (optional)
    source      TEXT NOT NULL DEFAULT 'agent'
                    CHECK (source IN ('agent', 'user', 'claude')),

    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- One entry per (project, category, key) — upsert-safe
    CONSTRAINT unique_memory_key UNIQUE (project_id, category, key)
);

CREATE INDEX idx_memory_project
    ON memory_entries(project_id, category);

CREATE TRIGGER trg_memory_updated_at
    BEFORE UPDATE ON memory_entries
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();