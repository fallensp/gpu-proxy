#!/usr/bin/env python3
import os
import sys
import asyncio
from dotenv import load_dotenv
import logging

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

# Import the setup function
from src.setup.setup_db import setup_database

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Run the database setup process."""
    # Load environment variables
    load_dotenv()
    
    logger.info("Starting database setup process...")
    success = await setup_database()
    
    if success:
        logger.info("Database setup completed successfully!")
    else:
        logger.error("Database setup failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 