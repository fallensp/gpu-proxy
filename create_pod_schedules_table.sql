-- Script to create pod_schedules table
-- Run this in the Supabase SQL Editor

-- Create pod_schedules table if it doesn't exist
CREATE TABLE IF NOT EXISTS pod_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    gpu_type TEXT NOT NULL,
    min_specs JSONB DEFAULT '{}'::jsonb,
    num_gpus INTEGER DEFAULT 1,
    disk_size INTEGER DEFAULT 10,
    docker_image TEXT NOT NULL,
    use_ssh BOOLEAN DEFAULT FALSE,
    start_schedule TEXT NOT NULL,
    stop_schedule TEXT NOT NULL,
    timezone TEXT DEFAULT 'UTC',
    last_instance_id TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_pod_schedules_user_id ON pod_schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_pod_schedules_is_active ON pod_schedules(is_active);

-- Grant permissions (if needed)
GRANT ALL ON pod_schedules TO anon, authenticated, service_role;

-- Create a check function (we will implement this client-side instead)
CREATE OR REPLACE FUNCTION check_table_exists(table_name TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public'
    AND table_name = table_name
  );
END;
$$;

-- Test the table
SELECT count(*) FROM pod_schedules; 