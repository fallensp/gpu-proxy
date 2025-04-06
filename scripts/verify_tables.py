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

async def verify_table(table_name):
    """Verify that a table exists and show its structure."""
    try:
        # Get Supabase client
        supabase = await get_supabase_client_async()
        logger.info(f"Connected to Supabase, checking table: {table_name}")
        
        # Check if table exists
        query = f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name = '{table_name}'
        );
        """
        result = await supabase.rpc('exec_sql', {'query': query}).execute()
        
        if not result.data or not result.data.get('success', False):
            logger.error(f"Failed to execute query: {result.data}")
            return False
        
        exists_query = f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name = '{table_name}'
        ) as exists;
        """
        exists_result = await supabase.rpc('exec_sql', {'query': exists_query}).execute()
        
        if exists_result.data and exists_result.data.get('success'):
            logger.info(f"Table {table_name} exists.")
        else:
            logger.error(f"Table {table_name} does not exist!")
            return False
        
        # Get table columns
        columns_query = f"""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = '{table_name}'
        ORDER BY ordinal_position;
        """
        columns_result = await supabase.rpc('exec_sql', {'query': columns_query}).execute()
        
        if not columns_result.data or not columns_result.data.get('success'):
            logger.error(f"Failed to get columns: {columns_result.data}")
            return False
        
        # Display columns
        logger.info(f"Columns in {table_name}:")
        column_query = f"""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = '{table_name}'
        ORDER BY ordinal_position;
        """
        column_result = await supabase.rpc('exec_sql', {'query': column_query}).execute()
        logger.info(f"Column details: {column_result.data}")
        
        # Count rows
        count_query = f"SELECT COUNT(*) as row_count FROM {table_name};"
        count_result = await supabase.rpc('exec_sql', {'query': count_query}).execute()
        
        if count_result.data and count_result.data.get('success'):
            logger.info(f"Row count in {table_name}: {count_result.data}")
        
        return True
    except Exception as e:
        logger.error(f"Error verifying table {table_name}: {str(e)}")
        return False

async def main():
    # Load environment variables
    load_dotenv()
    
    # Tables to verify
    tables = ['pod_schedules', 'instances', 'api_logs']
    
    # Verify each table
    for table in tables:
        logger.info(f"Verifying table: {table}")
        await verify_table(table)

if __name__ == "__main__":
    asyncio.run(main()) 