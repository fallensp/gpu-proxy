# Database Setup Instructions

To set up the database schema for the GPU Proxy API, follow these steps:

## Setup via Supabase SQL Editor

1. Log in to your Supabase dashboard at https://app.supabase.com/
2. Select your project
3. Navigate to the SQL Editor section (left sidebar)
4. Click on "New query"
5. Copy the contents of the `setup.sql` file in this directory
6. Paste it into the SQL Editor
7. Click "Run" to execute the script

## What the Setup Script Does

The SQL script will:

1. Create an `instances` table with all necessary columns
2. Create an `api_logs` table for tracking API requests and responses
3. Set up appropriate indexes for performance
4. Add comments to document the schema

## Database Tables

### Instances Table

The `instances` table stores information about GPU instances:

| Name | Type | Default | Primary | Description |
|------|------|---------|---------|-------------|
| id | uuid | gen_random_uuid() | Yes | Unique identifier |
| vast_id | varchar | | No | ID of the instance on Vast.ai |
| offer_id | varchar | | No | ID of the offer used to create the instance |
| label | varchar | | No | User-defined label for the instance |
| image | varchar | | No | Docker image used for the instance |
| disk_size | integer | | No | Disk size in GB |
| status | varchar | | No | Current status of the instance |
| provider | varchar | 'vast.ai' | No | Provider of the instance |
| details | jsonb | | No | Additional details about the instance |
| user_id | uuid | | No | ID of the user who created the instance |
| scheduled | boolean | false | No | Whether created through scheduling |
| scheduled_job_id | varchar | | No | ID of the job that scheduled creation |
| scheduled_time | timestamptz | | No | Time when scheduled to be created |
| shutdown_job_id | varchar | | No | ID of the job that scheduled shutdown |
| scheduled_shutdown_time | timestamptz | | No | Time scheduled to shut down |
| created_at | timestamptz | now() | No | Time when record was created |
| updated_at | timestamptz | now() | No | Time when record was last updated |

### API Logs Table

The `api_logs` table stores information about API requests and responses:

| Name | Type | Default | Primary | Description |
|------|------|---------|---------|-------------|
| id | uuid | gen_random_uuid() | Yes | Unique identifier |
| endpoint | varchar | | No | API endpoint that was called |
| method | varchar | | No | HTTP method (GET, POST, etc.) |
| request_payload | jsonb | | No | Request data |
| response_payload | jsonb | | No | Response data |
| status | varchar | | No | Status of the request (success, error) |
| status_code | integer | | No | HTTP status code |
| error_message | text | | No | Error message if the request failed |
| user_id | uuid | | No | ID of the user who made the request |
| vast_id | varchar | | No | ID of the Vast.ai instance if applicable |
| instance_id | uuid | | No | ID of the instance record if applicable |
| ip_address | varchar | | No | IP address of the client |
| duration_ms | integer | | No | Duration of the request in milliseconds |
| created_at | timestamptz | now() | No | Time when the log entry was created |

## Verifying the Setup

After setting up the database, you can verify that everything is working by:

1. Starting the backend server
2. Making a GET request to the `/api/v1/test/supabase` endpoint
3. If the connection is successful and the table exists, you should see a success message

Example:
```
curl http://localhost:8001/api/v1/test/supabase
```

## Troubleshooting

If you encounter issues:

1. Check that your Supabase URL and key are correctly set in the `.env` file
2. Ensure that the SQL script executed without errors in the Supabase SQL Editor
3. Check the Supabase dashboard for any error messages

## Manual Table Creation

If you prefer to create the table manually through the Supabase interface:

1. Go to the "Table Editor" in the Supabase dashboard
2. Click "Create a new table"
3. Name it "instances"
4. Add the following columns:

| Name | Type | Default | Primary | Description |
|------|------|---------|---------|-------------|
| id | uuid | gen_random_uuid() | Yes | Unique identifier |
| vast_id | varchar | | No | ID of the instance on Vast.ai |
| offer_id | varchar | | No | ID of the offer used to create the instance |
| label | varchar | | No | User-defined label for the instance |
| image | varchar | | No | Docker image used for the instance |
| disk_size | integer | | No | Disk size in GB |
| status | varchar | | No | Current status of the instance |
| provider | varchar | 'vast.ai' | No | Provider of the instance |
| details | jsonb | | No | Additional details about the instance |
| user_id | uuid | | No | ID of the user who created the instance |
| scheduled | boolean | false | No | Whether created through scheduling |
| scheduled_job_id | varchar | | No | ID of the job that scheduled creation |
| scheduled_time | timestamptz | | No | Time when scheduled to be created |
| shutdown_job_id | varchar | | No | ID of the job that scheduled shutdown |
| scheduled_shutdown_time | timestamptz | | No | Time scheduled to shut down |
| created_at | timestamptz | now() | No | Time when record was created |
| updated_at | timestamptz | now() | No | Time when record was last updated |

5. Create indices for `vast_id`, `status`, `user_id`, and `created_at` 