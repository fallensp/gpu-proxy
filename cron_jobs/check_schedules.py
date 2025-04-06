#!/usr/bin/env python3
"""
Cron job script to check and execute scheduled pod actions.
This script is intended to be run every minute by the system's cron service.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.schedule_manager import get_schedule_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/var/log/gpu-proxy/scheduler.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("scheduler_cron")

async def main():
    """
    Main function to check and execute scheduled pod actions.
    """
    logger.info(f"Starting scheduler check at {datetime.now().isoformat()}")
    
    try:
        # Get schedule manager instance
        schedule_manager = get_schedule_manager()
        
        # Check for pending actions
        results = await schedule_manager.check_pending_actions()
        
        # Log the results
        if results["started"] or results["stopped"]:
            logger.info(f"Processed schedules: started {len(results['started'])}, stopped {len(results['stopped'])}")
            
            if results["started"]:
                logger.info(f"Started instances for schedules: {', '.join(results['started'])}")
                
            if results["stopped"]:
                logger.info(f"Stopped instances for schedules: {', '.join(results['stopped'])}")
        else:
            logger.info("No schedules to process at this time")
            
    except Exception as e:
        logger.exception(f"Error in scheduler check: {str(e)}")
    
    logger.info(f"Completed scheduler check at {datetime.now().isoformat()}")

if __name__ == "__main__":
    asyncio.run(main()) 