CREATE TABLE IF NOT EXISTS briefs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id       UUID NOT NULL
                         REFERENCES projects(id) ON DELETE CASCADE,

    -- Each field is a distinct design concern, not a text blob.
    -- Claude reads individual fields via get_project_brief tool.
    goals            TEXT,           -- What does success look like?
    target_audience  TEXT,           -- Who is this built for?
    constraints      TEXT,           -- Budget, timeline, technical limits
    deliverables     TEXT,           -- What must be produced/shipped?
    tone             TEXT,           -- Voice/style if content-related
    reference_links  JSONB,          -- [{"label": "...", "url": "..."}]
    open_questions   JSONB,          -- ["Why are we using X?", ...]

    version          INTEGER NOT NULL DEFAULT 1,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT one_brief_per_project UNIQUE (project_id)
);

CREATE TRIGGER trg_briefs_updated_at
    BEFORE UPDATE ON briefs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();