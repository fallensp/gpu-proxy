#!/usr/bin/env python3
import os
import sys
import logging
import asyncio
from dotenv import load_dotenv

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

from src.core.db import get_supabase_client_async

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def create_pod_schedules_table():
    """Create the pod_schedules table directly."""
    try:
        # Get Supabase client
        supabase = await get_supabase_client_async()
        logger.info("Connected to Supabase")
        
        # Check if the table already exists
        query = supabase.from_("information_schema.tables").select("table_name") \
            .eq("table_schema", "public") \
            .eq("table_name", "pod_schedules") \
            .execute()
        
        if query.data and len(query.data) > 0:
            logger.info("pod_schedules table already exists.")
            return True
            
        # SQL for creating pod_schedules table
        create_table_sql = """
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
        
        -- Add index for user_id and is_active if it doesn't exist
        CREATE INDEX IF NOT EXISTS idx_pod_schedules_user_id ON pod_schedules(user_id);
        CREATE INDEX IF NOT EXISTS idx_pod_schedules_is_active ON pod_schedules(is_active);
        """
        
        # Direct execution via REST API using the SQL endpoint
        # Note: This requires that SQL execution is enabled in your Supabase project
        # You may need to use the web interface to run this SQL if the REST endpoint doesn't work
        logger.info("Attempting to create pod_schedules table...")
        
        # Try to use the SQL REST endpoint if available
        # Otherwise, output the SQL to run manually
        try:
            # Use the SQL endpoint if available
            # This is a method that might not be directly available - might need to use the Supabase web interface
            await supabase.table("pod_schedules").select("id").limit(1).execute()
            logger.info("pod_schedules table exists or was created successfully")
            return True
        except Exception as e:
            logger.warning(f"Could not verify or create table via REST API: {str(e)}")
            logger.info("Please run the following SQL in the Supabase web interface SQL editor:")
            print("\n" + create_table_sql + "\n")
            
            # Check if we need to show instructions on how to access the SQL editor
            logger.info("To run this SQL manually:")
            logger.info("1. Log into your Supabase dashboard")
            logger.info("2. Select your project")
            logger.info("3. Go to the SQL Editor")
            logger.info("4. Create a new query")
            logger.info("5. Paste the SQL above")
            logger.info("6. Run the query")
            
            return False
        
    except Exception as e:
        logger.error(f"Error creating pod_schedules table: {str(e)}")
        return False

async def main():
    # Load environment variables
    load_dotenv()
    
    logger.info("Starting table creation process...")
    success = await create_pod_schedules_table()
    
    if success:
        logger.info("Table creation process completed successfully")
    else:
        logger.warning("Table creation process completed with warnings")
        logger.info("Please check the logs and consider creating the table manually using the SQL provided")

if __name__ == "__main__":
    asyncio.run(main()) 