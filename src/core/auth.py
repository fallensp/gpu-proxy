"""
Authentication module for the GPU Proxy API.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

# Simple mock auth for development
# In production, replace with proper auth

logger = logging.getLogger(__name__)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_current_user(api_key: str = Depends(api_key_header)) -> Dict[str, Any]:
    """
    Get the current user based on API key.
    This is a simplified version for development.
    In production, implement proper authentication.
    
    Returns:
        Dict containing user information
    
    Raises:
        HTTPException: If authentication fails
    """
    # For development, accept any valid API key or none
    # In production, validate against database
    
    # Mock user for development
    mock_user = {
        "id": "00000000-0000-0000-0000-000000000000",
        "email": "tech@pictureworks.com",
        "role": "admin"
    }
    
    # In production, replace with actual validation
    if api_key:
        logger.debug(f"API key provided: {api_key[:8]}...")
    else:
        logger.debug("No API key provided, using default user")
    
    return mock_user

async def get_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Check if the current user is an admin.
    
    Args:
        current_user: The current authenticated user
        
    Returns:
        Dict containing user information
        
    Raises:
        HTTPException: If the user is not an admin
    """
    if current_user.get("role") != "admin":
        logger.warning(f"Non-admin user {current_user.get('email')} attempted to access admin endpoint")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
    
    return current_user 