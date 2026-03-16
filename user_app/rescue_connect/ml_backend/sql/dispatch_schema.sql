-- Dispatch Operations Schema Migration
-- Run this in Supabase SQL Editor

-- Add dispatch-related columns to posts table
ALTER TABLE posts ADD COLUMN IF NOT EXISTS dispatch_status TEXT DEFAULT 'pending';
ALTER TABLE posts ADD COLUMN IF NOT EXISTS assigned_team TEXT;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS resolution_notes TEXT;

-- Create index for efficient filtering
CREATE INDEX IF NOT EXISTS idx_posts_dispatch_status ON posts(dispatch_status);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);

-- Comment for documentation
COMMENT ON COLUMN posts.dispatch_status IS 'Status: pending, assigned, in-progress, resolved';
COMMENT ON COLUMN posts.assigned_team IS 'Name/ID of assigned response team';
COMMENT ON COLUMN posts.resolution_notes IS 'Notes added when incident is resolved';
