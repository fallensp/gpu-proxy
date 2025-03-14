"""
Main application module for the GPU Proxy API.
"""
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from src.api.routes import router

# Load environment variables
load_dotenv()

# Configure logging
logging_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, logging_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="GPU Proxy API",
    description="API for interacting with Vast.ai GPU resources",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include API routes
app.include_router(router, prefix="/api/v1")

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add custom info
    openapi_schema["info"]["x-logo"] = {
        "url": "https://vast.ai/static/img/vast-logo.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint that redirects to the API documentation."""
    return {
        "message": "Welcome to the GPU Proxy API",
        "documentation": "/docs",
        "api_prefix": "/api/v1"
    }

if __name__ == "__main__":
    import uvicorn
    
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