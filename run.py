#!/usr/bin/env python3
"""
Run script for the GPU Proxy API.
"""
import os
import sys
import logging

from dotenv import load_dotenv
# Remove the direct import since we'll use the string path instead
# from src.main import app
import uvicorn

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    # Log startup info
    logger.info(f"Starting GPU Proxy API on {host}:{port} (debug={debug})")
    
    # Run Uvicorn server - use import string path instead of app object
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    ) 