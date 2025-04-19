-- Script to modify pod_schedules table to make user_id nullable
-- Run this in the Supabase SQL Editor

-- First, drop the NOT NULL constraint on user_id
ALTER TABLE pod_schedules ALTER COLUMN user_id DROP NOT NULL;

-- Confirm changes
SELECT column_name, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'pod_schedules' AND column_name = 'user_id'; 