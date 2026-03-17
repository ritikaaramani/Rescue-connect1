-- RescueConnect Supabase Schema
-- Includes tables for ML Backend, Social Media Reports, and Dynamic Rerouting System

-- 1. Profiles Table (Users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
    username TEXT UNIQUE,
    display_name TEXT,
    avatar_url TEXT,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Posts Table (Disaster Reports)
CREATE TABLE IF NOT EXISTS public.posts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    caption TEXT,
    image_url TEXT,
    media_type TEXT DEFAULT 'image', -- image or video
    
    -- Original User GPS
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    location TEXT, -- User provided location name
    
    -- ML Analysis Fields
    status TEXT DEFAULT 'pending', -- pending, urgent, verified, rejected
    is_disaster BOOLEAN DEFAULT FALSE,
    disaster_type TEXT,
    severity TEXT,
    ai_description TEXT,
    detected_elements JSONB DEFAULT '[]'::jsonb,
    location_hints TEXT,
    people_affected TEXT,
    urgency_score INTEGER DEFAULT 0,
    ai_processed BOOLEAN DEFAULT FALSE,
    image_hash TEXT, -- For deduplication
    
    -- OCR & NLP Fields
    ocr_text TEXT,
    text_labels JSONB DEFAULT '[]'::jsonb,
    extracted_locations JSONB DEFAULT '[]'::jsonb,
    
    -- Inferred Geolocation Fields
    inferred_latitude DOUBLE PRECISION,
    inferred_longitude DOUBLE PRECISION,
    location_confidence DOUBLE PRECISION,
    location_method TEXT,
    scene_type TEXT,
    
    -- Dispatch & Management Fields
    dispatch_status TEXT DEFAULT 'pending', -- pending, assigned, in-progress, resolved
    assigned_team TEXT,
    assigned_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Hospitals Table
CREATE TABLE IF NOT EXISTS public.hospitals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    total_beds INTEGER DEFAULT 0,
    available_beds INTEGER DEFAULT 0,
    specialties TEXT[],
    contact_number TEXT,
    address TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Vehicles Table (Ambulances, Fire Trucks, etc.)
CREATE TABLE IF NOT EXISTS public.vehicles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    type TEXT NOT NULL, -- ambulance, fire_truck, police
    plate_number TEXT UNIQUE,
    current_latitude DOUBLE PRECISION,
    current_longitude DOUBLE PRECISION,
    status TEXT DEFAULT 'available', -- available, busy, maintenance
    assigned_hospital_id UUID REFERENCES public.hospitals(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Incidents Table (Converted from verified posts or manually created)
CREATE TABLE IF NOT EXISTS public.incidents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    source_post_id UUID REFERENCES public.posts(id),
    type TEXT,
    severity TEXT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active', -- active, closed
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Witness Reports (Quick reports from citizens)
CREATE TABLE IF NOT EXISTS public.witness_reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    incident_id UUID REFERENCES public.incidents(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.profiles(id),
    report_text TEXT,
    media_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Dispatch Logs
CREATE TABLE IF NOT EXISTS public.dispatch_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    incident_id UUID REFERENCES public.incidents(id),
    vehicle_id UUID REFERENCES public.vehicles(id),
    status TEXT, -- dispatched, arrived, returning
    dispatched_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    route_preview JSONB -- Store the planned route as GeoJSON or points
);

-- 8. Route Updates (Real-time rerouting data)
CREATE TABLE IF NOT EXISTS public.route_updates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    vehicle_id UUID REFERENCES public.vehicles(id),
    incident_id UUID REFERENCES public.incidents(id),
    original_route JSONB,
    updated_route JSONB,
    reason TEXT, -- blockage, traffic, new incident
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_posts_status ON public.posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_ai_processed ON public.posts(ai_processed);
CREATE INDEX IF NOT EXISTS idx_posts_dispatch_status ON public.posts(dispatch_status);
CREATE INDEX IF NOT EXISTS idx_vehicles_status ON public.vehicles(status);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON public.incidents(status);

-- Enable Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE public.posts;
ALTER PUBLICATION supabase_realtime ADD TABLE public.vehicles;
ALTER PUBLICATION supabase_realtime ADD TABLE public.incidents;
ALTER PUBLICATION supabase_realtime ADD TABLE public.dispatch_logs;
