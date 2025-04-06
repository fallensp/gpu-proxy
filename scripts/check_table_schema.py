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

async def check_table_schema():
    """Check the schema of the pod_schedules table."""
    
    # Load Supabase credentials from env
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("Missing SUPABASE_URL or SUPABASE_KEY/SUPABASE_SERVICE_KEY environment variables")
        return False
    
    logger.info(f"Using Supabase URL: {supabase_url}")
    
    # Create API endpoint for querying the information schema
    api_endpoint = urljoin(supabase_url, "rest/v1/rpc/inspect_table_schema")
    
    # Set up headers
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
    }
    
    # Set up payload
    payload = {
        "table_name": "pod_schedules"
    }
    
    try:
        # Query the schema
        async with httpx.AsyncClient() as client:
            response = await client.post(api_endpoint, headers=headers, json=payload)
            response.raise_for_status()
            
            schema = response.json()
            
            logger.info(f"Schema for pod_schedules table:")
            logger.info(json.dumps(schema, indent=2))
            
            return True
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error checking schema: {e.response.status_code} {e.response.reason_phrase}")
        
        # Try a direct schema query as fallback
        logger.info("Trying fallback query to information_schema...")
        try:
            # Create API endpoint for querying the information schema
            info_schema_endpoint = urljoin(supabase_url, "rest/v1/information_schema/columns")
            
            # Set up query parameters
            params = {
                "select": "*",
                "table_name": "eq.pod_schedules",
                "table_schema": "eq.public"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(info_schema_endpoint, headers=headers, params=params)
                response.raise_for_status()
                
                columns = response.json()
                
                logger.info(f"Columns for pod_schedules table:")
                logger.info(json.dumps(columns, indent=2))
                
                return True
        except Exception as fallback_error:
            logger.error(f"Error with fallback query: {str(fallback_error)}")
            logger.error(f"Response content: {e.response.text}")
            return False
    except Exception as e:
        logger.error(f"Error checking table schema: {str(e)}")
        return False

async def main():
    await check_table_schema()

if __name__ == "__main__":
    asyncio.run(main()) 