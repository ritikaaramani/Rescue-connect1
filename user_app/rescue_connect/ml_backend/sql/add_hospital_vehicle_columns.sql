-- Add hospital and vehicle assignment columns to posts table
-- Run this in Supabase SQL Editor

ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS destination_hospital_id UUID REFERENCES public.hospitals(id);
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS assigned_vehicle_id UUID REFERENCES public.vehicles(id);
