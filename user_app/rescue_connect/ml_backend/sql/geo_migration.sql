-- Geo migration: Add new columns for OCR and geolocation data
-- Run this in Supabase SQL Editor

-- OCR extracted text
ALTER TABLE posts ADD COLUMN IF NOT EXISTS ocr_text TEXT;

-- Text analysis labels (disaster types from text)
ALTER TABLE posts ADD COLUMN IF NOT EXISTS text_labels TEXT[];

-- Location entities extracted from text
ALTER TABLE posts ADD COLUMN IF NOT EXISTS extracted_locations TEXT[];

-- Inferred geographic coordinates
ALTER TABLE posts ADD COLUMN IF NOT EXISTS inferred_latitude DECIMAL(10, 7);
ALTER TABLE posts ADD COLUMN IF NOT EXISTS inferred_longitude DECIMAL(10, 7);

-- Location confidence score (0-1)
ALTER TABLE posts ADD COLUMN IF NOT EXISTS location_confidence DECIMAL(3, 2);

-- Method used to determine location
ALTER TABLE posts ADD COLUMN IF NOT EXISTS location_method TEXT;

-- Scene type from image analysis
ALTER TABLE posts ADD COLUMN IF NOT EXISTS scene_type TEXT;

-- Add index for geolocation queries
CREATE INDEX IF NOT EXISTS idx_posts_geolocation 
ON posts (inferred_latitude, inferred_longitude) 
WHERE inferred_latitude IS NOT NULL AND inferred_longitude IS NOT NULL;

-- Add index for filtering by scene type
CREATE INDEX IF NOT EXISTS idx_posts_scene_type 
ON posts (scene_type) 
WHERE scene_type IS NOT NULL;
