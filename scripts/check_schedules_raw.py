#!/usr/bin/env python3
import os
import sys
import json
import asyncio
from dotenv import load_dotenv
import logging
import httpx
from urllib.parse import urljoin

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_schedules():
    """Check the pod_schedules table directly via Supabase API."""
    
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
        "Content-Type": "application/json"
    }
    
    try:
        # Query the pod_schedules table
        async with httpx.AsyncClient() as client:
            response = await client.get(api_endpoint, headers=headers)
            response.raise_for_status()
            
            schedules = response.json()
            
            if schedules:
                logger.info(f"Found {len(schedules)} schedule records:")
                for idx, record in enumerate(schedules):
                    logger.info(f"Schedule {idx+1}:")
                    for key, value in record.items():
                        # Format JSON values nicely
                        if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                            try:
                                parsed = json.loads(value)
                                value = json.dumps(parsed, indent=2)
                            except:
                                pass
                        logger.info(f"  {key}: {value}")
                    logger.info("-----")
            else:
                logger.info("No schedule records found in the database")
            
            return True
            
    except Exception as e:
        logger.error(f"Error querying pod_schedules table: {str(e)}")
        return False

async def main():
    await check_schedules()

if __name__ == "__main__":
    asyncio.run(main()) 