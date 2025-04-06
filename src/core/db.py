"""
Database connection module for interacting with Supabase.
"""
import os
import logging
from typing import Optional, Dict, Any
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class MockSupabaseClient:
    """
    Mock Supabase client for development and testing.
    """
    def table(self, table_name):
        return self
        
    def insert(self, data):
        logger.debug(f"MOCK: Insert into table: {data}")
        return self
        
    def select(self, *args):
        logger.debug(f"MOCK: Select {args}")
        return self
        
    def execute(self):
        logger.debug("MOCK: Executed query")
        return {"data": [], "error": None}

class SupabaseClient:
    """
    Client for interacting with Supabase.
    """
    
    _instance: Optional['SupabaseClient'] = None
    
    def __new__(cls):
        """
        Singleton implementation to ensure only one client instance exists.
        """
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        Initialize the Supabase client.
        """
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        # Get credentials from environment
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            logger.warning("Supabase credentials not found in environment variables. Using mock client for development.")
            self.client = MockSupabaseClient()
            self._initialized = True
            return
        
        # Initialize client
        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
            logger.info(f"Initialized Supabase client. Connected to: {self.supabase_url}")
        except Exception as e:
            logger.warning(f"Failed to initialize Supabase client: {str(e)}. Using mock client instead.")
            self.client = MockSupabaseClient()
        
        self._initialized = True
    
    def get_client(self):
        """
        Get the Supabase client instance.
        
        Returns:
            The Supabase client.
        """
        return self.client

# Global instance
supabase = SupabaseClient()

def get_supabase_client():
    """
    Function to get the Supabase client for dependency injection.
    
    Returns:
        The Supabase client.
    """
    return supabase.get_client()

async def get_supabase_client_async():
    """
    Async function to get the Supabase client for dependency injection.
    This is a wrapper to make it compatible with async dependency injection.
    
    Returns:
        The Supabase client.
    """
    return supabase.get_client()

async def log_api_call(
    client,
    endpoint: str,
    method: str,
    request_payload=None,
    response_payload=None,
    status="success",
    status_code=200,
    error_message=None,
    user_id=None,
    vast_id=None,
    instance_id=None,
    ip_address=None,
    duration_ms=None
):
    """
    Log an API call to the database.
    
    Args:
        client: Supabase client
        endpoint: API endpoint that was called
        method: HTTP method (GET, POST, etc.)
        request_payload: Request data
        response_payload: Response data
        status: Status of the request (success, error)
        status_code: HTTP status code
        error_message: Error message if applicable
        user_id: User ID if available
        vast_id: Vast.ai instance ID if applicable
        instance_id: Internal instance ID if applicable
        ip_address: Client IP address
        duration_ms: Request duration in milliseconds
    """
    try:
        log_data = {
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "status_code": status_code
        }
        
        # Add optional fields if they exist
        if request_payload is not None:
            log_data["request_payload"] = request_payload
        if response_payload is not None:
            log_data["response_payload"] = response_payload
        if error_message:
            log_data["error_message"] = error_message
        if user_id:
            log_data["user_id"] = user_id
        if vast_id:
            log_data["vast_id"] = vast_id
        if instance_id:
            log_data["instance_id"] = instance_id
        if ip_address:
            log_data["ip_address"] = ip_address
        if duration_ms is not None:
            log_data["duration_ms"] = duration_ms
            
        # Insert the log into the database
        result = client.table("api_logs").insert(log_data).execute()
        return result
    except Exception as e:
        # Don't raise an exception - just log it to prevent API failure
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to log API call: {str(e)}")
        return None 