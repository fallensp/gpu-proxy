#!/usr/bin/env python3
"""
Script to run the GPU Proxy API.
"""
import os
import sys
import logging
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

# Configure logging
logging_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, logging_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def main():
    """Run the GPU Proxy API."""
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    logger.info(f"Starting GPU Proxy API on {host}:{port} (debug={debug})")
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level=logging_level.lower(),
    )

if __name__ == "__main__":
    main() 