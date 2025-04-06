import os
import logging
import asyncio
from dotenv import load_dotenv
import sys

# Add parent directory to path so we can import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.db import get_supabase_client_async

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def setup_database():
    """Set up the database tables and functions."""
    logger.info("Setting up database tables and functions...")
    
    # Get Supabase client
    try:
        supabase = await get_supabase_client_async()
        logger.info("Connected to Supabase")
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {str(e)}")
        return False
    
    # Read the SQL file
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sql_file_path = os.path.join(script_dir, 'create_tables.sql')
        
        with open(sql_file_path, 'r') as f:
            sql_script = f.read()
        
        logger.info(f"Read SQL script from {sql_file_path}")
    except Exception as e:
        logger.error(f"Failed to read SQL file: {str(e)}")
        return False
    
    # Execute the SQL script
    try:
        # Split the script by statements (simple approach)
        statements = [s.strip() for s in sql_script.split(';') if s.strip()]
        
        for statement in statements:
            if statement:
                logger.info(f"Executing SQL statement: {statement[:100]}...")
                result = await supabase.rpc('exec_sql', {'query': statement}).execute()
                logger.info(f"SQL execution result: {result}")
        
        logger.info("Database setup completed successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to execute SQL: {str(e)}")
        return False

async def main():
    # Load environment variables
    load_dotenv()
    
    # Set up the database
    success = await setup_database()
    
    if success:
        logger.info("Database setup completed successfully")
    else:
        logger.error("Database setup failed")

if __name__ == "__main__":
    asyncio.run(main()) 