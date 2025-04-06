-- Scheduler feature setup for GPU Proxy API

-- Create the users table if it doesn't exist
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  first_name TEXT,
  last_name TEXT,
  company_name TEXT,
  role TEXT NOT NULL DEFAULT 'user',
  api_key TEXT,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  last_login_at TIMESTAMP WITH TIME ZONE
);

-- Create index for faster email lookups
CREATE INDEX IF NOT EXISTS users_email_idx ON users(email);

-- Insert first admin user if it doesn't exist
INSERT INTO users (
  email, 
  password_hash, 
  first_name, 
  last_name, 
  company_name, 
  role
) 
VALUES (
  'tech@pictureworks.com',
  -- In a real implementation, this would be a proper bcrypt hash, not plain text
  '$2b$12$9VLkfxfOn3eRJXTK4yBkpeC.bTQ35gxH.7ldHyASP0ZSZSXxwrEQG', -- hash for 'abcd1234'
  'Admin',
  'User',
  'Picture Works',
  'admin'
)
ON CONFLICT (email) DO NOTHING;

-- Create the pod_schedules table
CREATE TABLE IF NOT EXISTS pod_schedules (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  gpu_type TEXT NOT NULL,
  min_specs JSONB NOT NULL,
  num_gpus INTEGER NOT NULL DEFAULT 1,
  disk_size INTEGER NOT NULL DEFAULT 50,
  docker_image TEXT NOT NULL,
  env_params TEXT,
  onstart_cmd TEXT,
  use_ssh BOOLEAN NOT NULL DEFAULT true,
  use_direct BOOLEAN NOT NULL DEFAULT true,
  template_id UUID REFERENCES instance_templates(id),
  start_schedule TEXT NOT NULL, -- cron format (e.g., "0 8 * * 1-5" for weekdays at 8 AM)
  stop_schedule TEXT NOT NULL,  -- cron format (e.g., "0 20 * * 1-5" for weekdays at 8 PM)
  timezone TEXT NOT NULL DEFAULT 'UTC',
  max_price_per_hour NUMERIC(10, 4),
  is_active BOOLEAN NOT NULL DEFAULT true,
  last_instance_id TEXT,
  last_run_time TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create index for faster user_id lookups
CREATE INDEX IF NOT EXISTS pod_schedules_user_id_idx ON pod_schedules(user_id);

-- Add comments for better documentation
COMMENT ON TABLE users IS 'Stores user account information';
COMMENT ON COLUMN users.id IS 'Unique identifier for the user';
COMMENT ON COLUMN users.email IS 'User email address for login';
COMMENT ON COLUMN users.password_hash IS 'Hashed password for user authentication';
COMMENT ON COLUMN users.first_name IS 'User first name';
COMMENT ON COLUMN users.last_name IS 'User last name';
COMMENT ON COLUMN users.company_name IS 'Company or organization name';
COMMENT ON COLUMN users.role IS 'User role (user, admin, etc.)';
COMMENT ON COLUMN users.api_key IS 'API key for programmatic access';
COMMENT ON COLUMN users.is_active IS 'Whether the user account is active';
COMMENT ON COLUMN users.created_at IS 'Time when the user account was created';
COMMENT ON COLUMN users.updated_at IS 'Time when the user account was last updated';
COMMENT ON COLUMN users.last_login_at IS 'Time of last successful login';

COMMENT ON TABLE pod_schedules IS 'Stores GPU pod scheduling configurations';
COMMENT ON COLUMN pod_schedules.id IS 'Unique identifier for the schedule';
COMMENT ON COLUMN pod_schedules.user_id IS 'ID of the user who created the schedule';
COMMENT ON COLUMN pod_schedules.name IS 'Name of the scheduled pod';
COMMENT ON COLUMN pod_schedules.gpu_type IS 'Type of GPU required (e.g., RTX 4090)';
COMMENT ON COLUMN pod_schedules.min_specs IS 'Minimum required specifications as JSON';
COMMENT ON COLUMN pod_schedules.num_gpus IS 'Number of GPUs to provision';
COMMENT ON COLUMN pod_schedules.disk_size IS 'Disk size in GB';
COMMENT ON COLUMN pod_schedules.docker_image IS 'Docker image to use for the pod';
COMMENT ON COLUMN pod_schedules.env_params IS 'Environment parameters for the container';
COMMENT ON COLUMN pod_schedules.onstart_cmd IS 'Command to run on startup';
COMMENT ON COLUMN pod_schedules.use_ssh IS 'Whether to enable SSH access';
COMMENT ON COLUMN pod_schedules.use_direct IS 'Whether to enable direct connection';
COMMENT ON COLUMN pod_schedules.template_id IS 'Reference to a template if used';
COMMENT ON COLUMN pod_schedules.start_schedule IS 'Cron expression for when to start the pod';
COMMENT ON COLUMN pod_schedules.stop_schedule IS 'Cron expression for when to stop the pod';
COMMENT ON COLUMN pod_schedules.timezone IS 'Timezone for the schedule expressions';
COMMENT ON COLUMN pod_schedules.max_price_per_hour IS 'Maximum price willing to pay per hour';
COMMENT ON COLUMN pod_schedules.is_active IS 'Whether the schedule is active';
COMMENT ON COLUMN pod_schedules.last_instance_id IS 'ID of the last instance created by this schedule';
COMMENT ON COLUMN pod_schedules.last_run_time IS 'Time when the schedule last ran';
COMMENT ON COLUMN pod_schedules.created_at IS 'Time when the schedule was created';
COMMENT ON COLUMN pod_schedules.updated_at IS 'Time when the schedule was last updated'; 