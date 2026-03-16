-- Run this in Supabase SQL Editor to add ML analysis columns to posts table

-- Add new columns for AI analysis results
ALTER TABLE public.posts 
ADD COLUMN IF NOT EXISTS disaster_type text DEFAULT NULL,
ADD COLUMN IF NOT EXISTS severity text DEFAULT NULL,
ADD COLUMN IF NOT EXISTS ai_description text DEFAULT NULL,
ADD COLUMN IF NOT EXISTS detected_elements text[] DEFAULT NULL,
ADD COLUMN IF NOT EXISTS location_hints text DEFAULT NULL,
ADD COLUMN IF NOT EXISTS people_affected text DEFAULT NULL,
ADD COLUMN IF NOT EXISTS urgency_score integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS is_disaster boolean DEFAULT NULL,
ADD COLUMN IF NOT EXISTS ai_processed boolean DEFAULT false;

-- Add index for faster queries on status and urgency
CREATE INDEX IF NOT EXISTS idx_posts_status ON public.posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_urgency ON public.posts(urgency_score DESC);
CREATE INDEX IF NOT EXISTS idx_posts_disaster_type ON public.posts(disaster_type);

-- Update RLS to allow service role to update posts (for ML backend)
-- The service role key bypasses RLS, so no changes needed there.

-- Optional: Add a view for urgent posts
CREATE OR REPLACE VIEW public.urgent_posts AS
SELECT * FROM public.posts 
WHERE is_disaster = true AND urgency_score >= 7
ORDER BY urgency_score DESC, created_at DESC;
