-- Add image_hash column for deduplication
-- Run this in Supabase SQL Editor

-- Add image_hash column to posts table
ALTER TABLE posts ADD COLUMN IF NOT EXISTS image_hash TEXT;

-- Create index for faster hash lookups
CREATE INDEX IF NOT EXISTS idx_posts_image_hash ON posts(image_hash);

-- Create index for time-based queries (for 2-hour window checks)
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);
