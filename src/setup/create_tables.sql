-- Create tables for the GPU Proxy API

-- Function to check if a table exists
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

-- Create instances table if it doesn't exist
CREATE TABLE IF NOT EXISTS instances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vast_id TEXT NOT NULL,
    offer_id BIGINT,
    label TEXT,
    image TEXT NOT NULL,
    disk_size INTEGER NOT NULL DEFAULT 10,
    status TEXT NOT NULL,
    ip_address TEXT,
    ssh_port INTEGER,
    jupyter_url TEXT,
    provider TEXT NOT NULL,
    details JSONB,
    user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

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

-- Create API logs table if it doesn't exist
CREATE TABLE IF NOT EXISTS api_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INTEGER,
    duration_ms INTEGER,
    request_payload JSONB,
    response_payload JSONB,
    client_ip TEXT,
    user_id UUID,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_instances_vast_id ON instances(vast_id);
CREATE INDEX IF NOT EXISTS idx_instances_user_id ON instances(user_id);
CREATE INDEX IF NOT EXISTS idx_instances_status ON instances(status);
CREATE INDEX IF NOT EXISTS idx_pod_schedules_user_id ON pod_schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_pod_schedules_is_active ON pod_schedules(is_active);
CREATE INDEX IF NOT EXISTS idx_api_logs_endpoint ON api_logs(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_logs_created_at ON api_logs(created_at); 