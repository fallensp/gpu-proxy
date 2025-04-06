#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import uuid
from datetime import datetime
from dotenv import load_dotenv
import logging
import httpx
from urllib.parse import urljoin

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def insert_test_schedule():
    """Insert a test record into the pod_schedules table via Supabase API."""
    
    # Load Supabase credentials from env
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("Missing SUPABASE_URL or SUPABASE_KEY/SUPABASE_SERVICE_KEY environment variables")
        return False
    
    logger.info(f"Using Supabase URL: {supabase_url}")
    
    # Create API endpoint for pod_schedules table
    api_endpoint = urljoin(supabase_url, "rest/v1/pod_schedules")
    
    # Set up headers
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"  # This asks Supabase to return the inserted record
    }
    
    # Create a test record
    test_schedule = {
        "id": str(uuid.uuid4()),
        "name": f"Test Schedule {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "gpu_type": "Test GPU",
        "min_specs": json.dumps({}),  # Ensure this is a JSON string
        "num_gpus": 1,
        "disk_size": 10,
        "docker_image": "nvidia/cuda:11.6.2-base-ubuntu20.04",
        "use_ssh": True,
        "start_schedule": "0 9 * * 1-5",  # 9am weekdays
        "stop_schedule": "0 17 * * 1-5",  # 5pm weekdays
        "timezone": "UTC",
        "last_instance_id": "test-instance-123",
        "is_active": True,
        "user_id": None,  # Set to null to avoid foreign key constraint
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    logger.info(f"Inserting test schedule with ID: {test_schedule['id']}")
    logger.info(f"Record data: {json.dumps(test_schedule, indent=2)}")
    
    try:
        # Insert the record
        async with httpx.AsyncClient() as client:
            response = await client.post(
                api_endpoint,
                headers=headers,
                json=test_schedule
            )
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            logger.info(f"Successfully inserted test schedule:")
            logger.info(f"Response: {json.dumps(result, indent=2)}")
            
            return True
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error inserting test schedule: {e.response.status_code} {e.response.reason_phrase}")
        logger.error(f"Response content: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"Error inserting test schedule: {str(e)}")
        return False

async def main():
    await insert_test_schedule()

if __name__ == "__main__":
    asyncio.run(main()) 