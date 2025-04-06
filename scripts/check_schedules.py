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

async def check_schedule_records():
    """Check for schedule records in the database."""
    try:
        # Get Supabase client
        supabase = await get_supabase_client_async()
        logger.info("Connected to Supabase")
        
        # Check pod_schedules table
        try:
            # Note: using await correctly with execute
            result = await supabase.table("pod_schedules").select("*").execute()
            
            # Access result.data directly (no await needed here)
            if hasattr(result, 'data') and result.data:
                logger.info(f"Found {len(result.data)} schedule records:")
                for idx, record in enumerate(result.data):
                    logger.info(f"Schedule {idx+1}:")
                    for key, value in record.items():
                        logger.info(f"  {key}: {value}")
                    logger.info("-----")
            else:
                logger.info("No schedule records found in the database")
                
            try:
                # Try a direct count query
                count_result = await supabase.from_("pod_schedules").select("*", count="exact").execute()
                logger.info(f"Table count: {count_result.count if hasattr(count_result, 'count') else 'unknown'}")
            except Exception as count_error:
                logger.error(f"Count query error: {str(count_error)}")
                
        except Exception as e:
            logger.error(f"Error querying pod_schedules table: {str(e)}")
            logger.error(f"Exception type: {type(e)}")
        
        return True
    except Exception as e:
        logger.error(f"Error checking schedule records: {str(e)}")
        return False

async def main():
    # Load environment variables
    load_dotenv()
    
    logger.info("Checking schedule records in the database...")
    await check_schedule_records()

if __name__ == "__main__":
    asyncio.run(main()) 