-- Add location column for user-provided location
-- Run this in Supabase SQL Editor

-- User-provided location (text input from simulator)
ALTER TABLE posts ADD COLUMN IF NOT EXISTS location TEXT;

-- Add index for location searches
CREATE INDEX IF NOT EXISTS idx_posts_location 
ON posts (location) 
WHERE location IS NOT NULL;
