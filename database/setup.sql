-- Database setup for GPU Proxy API

-- Drop tables if they exist (for clean setup)
DROP TABLE IF EXISTS instances;
DROP TABLE IF EXISTS api_logs;
DROP TABLE IF EXISTS instance_templates;

-- Create the instances table
CREATE TABLE instances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vast_id VARCHAR(255),
    offer_id VARCHAR(255),
    label VARCHAR(255),
    image VARCHAR(255),
    disk_size INTEGER,
    status VARCHAR(50) NOT NULL,
    provider VARCHAR(50) NOT NULL DEFAULT 'vast.ai',
    details JSONB,
    user_id UUID,
    scheduled BOOLEAN DEFAULT FALSE,
    scheduled_job_id VARCHAR(255),
    scheduled_time TIMESTAMP WITH TIME ZONE,
    shutdown_job_id VARCHAR(255),
    scheduled_shutdown_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indices for faster lookups
CREATE INDEX idx_instances_vast_id ON instances(vast_id);
CREATE INDEX idx_instances_status ON instances(status);
CREATE INDEX idx_instances_user_id ON instances(user_id);
CREATE INDEX idx_instances_created_at ON instances(created_at);

-- Add comments for better documentation
COMMENT ON TABLE instances IS 'Stores information about GPU instances';
COMMENT ON COLUMN instances.id IS 'Unique identifier for the instance record';
COMMENT ON COLUMN instances.vast_id IS 'ID of the instance on Vast.ai';
COMMENT ON COLUMN instances.offer_id IS 'ID of the offer used to create the instance';
COMMENT ON COLUMN instances.label IS 'User-defined label for the instance';
COMMENT ON COLUMN instances.image IS 'Docker image used for the instance';
COMMENT ON COLUMN instances.disk_size IS 'Disk size in GB';
COMMENT ON COLUMN instances.status IS 'Current status of the instance (creating, running, stopped, etc.)';
COMMENT ON COLUMN instances.provider IS 'Provider of the instance (vast.ai, etc.)';
COMMENT ON COLUMN instances.details IS 'Additional details about the instance as JSON';
COMMENT ON COLUMN instances.user_id IS 'ID of the user who created the instance';
COMMENT ON COLUMN instances.scheduled IS 'Whether the instance was created through scheduling';
COMMENT ON COLUMN instances.scheduled_job_id IS 'ID of the job that scheduled the instance creation';
COMMENT ON COLUMN instances.scheduled_time IS 'Time when the instance was scheduled to be created';
COMMENT ON COLUMN instances.shutdown_job_id IS 'ID of the job that scheduled the instance shutdown';
COMMENT ON COLUMN instances.scheduled_shutdown_time IS 'Time when the instance is scheduled to shut down';
COMMENT ON COLUMN instances.created_at IS 'Time when the instance record was created';
COMMENT ON COLUMN instances.updated_at IS 'Time when the instance record was last updated';

-- Create API Logs table for tracking requests and responses
CREATE TABLE api_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    request_payload JSONB,
    response_payload JSONB,
    status VARCHAR(50) NOT NULL,
    status_code INTEGER,
    error_message TEXT,
    user_id UUID,
    vast_id VARCHAR(255),
    instance_id UUID,
    ip_address VARCHAR(255),
    duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indices for faster lookups in the logs table
CREATE INDEX idx_api_logs_endpoint ON api_logs(endpoint);
CREATE INDEX idx_api_logs_status ON api_logs(status);
CREATE INDEX idx_api_logs_created_at ON api_logs(created_at);
CREATE INDEX idx_api_logs_vast_id ON api_logs(vast_id);
CREATE INDEX idx_api_logs_instance_id ON api_logs(instance_id);

-- Add comments for better documentation
COMMENT ON TABLE api_logs IS 'Stores API request and response logs';
COMMENT ON COLUMN api_logs.id IS 'Unique identifier for the log entry';
COMMENT ON COLUMN api_logs.endpoint IS 'API endpoint that was called';
COMMENT ON COLUMN api_logs.method IS 'HTTP method used (GET, POST, etc.)';
COMMENT ON COLUMN api_logs.request_payload IS 'Request data as JSON';
COMMENT ON COLUMN api_logs.response_payload IS 'Response data as JSON';
COMMENT ON COLUMN api_logs.status IS 'Status of the request (success, error)';
COMMENT ON COLUMN api_logs.status_code IS 'HTTP status code of the response';
COMMENT ON COLUMN api_logs.error_message IS 'Error message if the request failed';
COMMENT ON COLUMN api_logs.user_id IS 'ID of the user who made the request';
COMMENT ON COLUMN api_logs.vast_id IS 'ID of the Vast.ai instance if applicable';
COMMENT ON COLUMN api_logs.instance_id IS 'ID of the instance record if applicable';
COMMENT ON COLUMN api_logs.ip_address IS 'IP address of the client';
COMMENT ON COLUMN api_logs.duration_ms IS 'Duration of the request in milliseconds';
COMMENT ON COLUMN api_logs.created_at IS 'Time when the log entry was created';

-- Create Instance Templates table for storing reusable instance configurations
CREATE TABLE instance_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    image VARCHAR(255) NOT NULL,
    env_params TEXT,
    onstart_cmd VARCHAR(255),
    disk_size INTEGER NOT NULL DEFAULT 50,
    use_ssh BOOLEAN NOT NULL DEFAULT TRUE,
    use_direct BOOLEAN NOT NULL DEFAULT TRUE,
    other_params JSONB,
    template_type VARCHAR(50) NOT NULL DEFAULT 'user',
    tags VARCHAR(255)[],
    user_id UUID,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    is_featured BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indices for faster lookups in the templates table
CREATE INDEX idx_instance_templates_name ON instance_templates(name);
CREATE INDEX idx_instance_templates_user_id ON instance_templates(user_id);
CREATE INDEX idx_instance_templates_template_type ON instance_templates(template_type);
CREATE INDEX idx_instance_templates_is_public ON instance_templates(is_public);

-- Add comments for better documentation
COMMENT ON TABLE instance_templates IS 'Stores reusable instance configurations and templates';
COMMENT ON COLUMN instance_templates.id IS 'Unique identifier for the template';
COMMENT ON COLUMN instance_templates.name IS 'Name of the template';
COMMENT ON COLUMN instance_templates.description IS 'Description of what the template is for';
COMMENT ON COLUMN instance_templates.image IS 'Docker image to use for the instance';
COMMENT ON COLUMN instance_templates.env_params IS 'Environment parameters for the Docker container';
COMMENT ON COLUMN instance_templates.onstart_cmd IS 'Command to run when the instance starts';
COMMENT ON COLUMN instance_templates.disk_size IS 'Disk size in GB';
COMMENT ON COLUMN instance_templates.use_ssh IS 'Whether to enable SSH access';
COMMENT ON COLUMN instance_templates.use_direct IS 'Whether to use direct connection';
COMMENT ON COLUMN instance_templates.other_params IS 'Additional parameters as JSON';
COMMENT ON COLUMN instance_templates.template_type IS 'Type of template (user, system, etc.)';
COMMENT ON COLUMN instance_templates.tags IS 'Tags for categorizing templates';
COMMENT ON COLUMN instance_templates.user_id IS 'ID of the user who created the template';
COMMENT ON COLUMN instance_templates.is_public IS 'Whether the template is public';
COMMENT ON COLUMN instance_templates.is_featured IS 'Whether the template is featured';
COMMENT ON COLUMN instance_templates.created_at IS 'Time when the template was created';
COMMENT ON COLUMN instance_templates.updated_at IS 'Time when the template was last updated';

-- For future: We may want to add users table, billing records, etc. 