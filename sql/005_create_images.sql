CREATE TABLE IF NOT EXISTS images (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id   UUID NOT NULL
                     REFERENCES projects(id) ON DELETE CASCADE,

    prompt       TEXT,              -- The generation prompt
    url          TEXT NOT NULL,     -- Storage URL or mock path
    provider     TEXT NOT NULL DEFAULT 'mock'
                     CHECK (provider IN ('mock', 'dalle', 'stability', 'replicate', 'upload')),

    -- Gemini analysis result — null until analyze endpoint is called
    analysis     TEXT,
    analyzed_at  TIMESTAMPTZ,

    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_images_project
    ON images(project_id, created_at DESC);

-- Create the private storage bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'project-images',
    'project-images',
    false,  -- Private bucket for security
    5242880,
    ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/gif']
)
ON CONFLICT (id) DO UPDATE SET public = false;

-- Disable all public access (RLS is enabled by default on new buckets)
-- The backend will use the SERVICE_ROLE key to bypass these policies.
DELETE FROM pg_policies 
WHERE tablename = 'objects' 
  AND schemaname = 'storage' 
  AND policyname IN ('Public Access', 'Public Upload Access', 'Public Delete Access', 'Upload Access', 'Delete Access');
