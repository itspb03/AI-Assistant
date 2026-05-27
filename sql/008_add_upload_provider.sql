-- Migration: add 'upload' to the images.provider CHECK constraint
-- Run this once against your Supabase database (SQL Editor or CLI).

ALTER TABLE images
    DROP CONSTRAINT IF EXISTS images_provider_check;

ALTER TABLE images
    ADD CONSTRAINT images_provider_check
    CHECK (provider IN ('mock', 'dalle', 'stability', 'replicate', 'upload'));
