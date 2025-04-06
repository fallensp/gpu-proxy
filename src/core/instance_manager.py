"""
Instance manager module for handling GPU instances in the database.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from supabase import Client

from src.core.db import get_supabase_client

logger = logging.getLogger(__name__)

class InstanceManager:
    """
    Manager for GPU instance data in Supabase.
    """
    
    def __init__(self, supabase_client: Client):
        """
        Initialize the instance manager.
        
        Args:
            supabase_client: The Supabase client.
        """
        self.supabase = supabase_client
        self.table_name = "instances"  # The name of your Supabase table
    
    async def create_instance(self, instance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new instance record in the database.
        
        Args:
            instance_data: The instance data to store.
        
        Returns:
            The created instance record.
        """
        try:
            # Add timestamps
            instance_data["created_at"] = datetime.utcnow().isoformat()
            instance_data["updated_at"] = instance_data["created_at"]
            
            # Insert the instance data
            result = self.supabase.table(self.table_name).insert(instance_data).execute()
            
            # Log success
            inserted_data = result.data[0] if result.data else None
            logger.info(f"Created instance record: {inserted_data.get('id') if inserted_data else None}")
            
            return inserted_data
        except Exception as e:
            logger.exception(f"Error creating instance record: {str(e)}")
            raise
    
    async def get_instance(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an instance record by ID.
        
        Args:
            instance_id: The ID of the instance to retrieve.
        
        Returns:
            The instance record, or None if not found.
        """
        try:
            result = self.supabase.table(self.table_name).select("*").eq("id", instance_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.exception(f"Error getting instance {instance_id}: {str(e)}")
            raise
    
    async def list_instances(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all instances, optionally filtered by user ID.
        
        Args:
            user_id: The ID of the user to filter by.
        
        Returns:
            A list of instance records.
        """
        try:
            query = self.supabase.table(self.table_name).select("*")
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            result = query.order("created_at", desc=True).execute()
            return result.data
        except Exception as e:
            logger.exception(f"Error listing instances: {str(e)}")
            raise
    
    async def update_instance(self, instance_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an instance record.
        
        Args:
            instance_id: The ID of the instance to update.
            update_data: The data to update.
        
        Returns:
            The updated instance record.
        """
        try:
            # Add updated timestamp
            update_data["updated_at"] = datetime.utcnow().isoformat()
            
            # Update the instance
            result = self.supabase.table(self.table_name).update(update_data).eq("id", instance_id).execute()
            
            updated_data = result.data[0] if result.data else None
            logger.info(f"Updated instance record: {instance_id}")
            
            return updated_data
        except Exception as e:
            logger.exception(f"Error updating instance {instance_id}: {str(e)}")
            raise
    
    async def delete_instance(self, instance_id: str) -> bool:
        """
        Delete an instance record.
        
        Args:
            instance_id: The ID of the instance to delete.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            result = self.supabase.table(self.table_name).delete().eq("id", instance_id).execute()
            success = bool(result.data)
            logger.info(f"Deleted instance record: {instance_id}, success: {success}")
            return success
        except Exception as e:
            logger.exception(f"Error deleting instance {instance_id}: {str(e)}")
            raise

def get_instance_manager() -> InstanceManager:
    """
    Factory function to get an instance manager with a Supabase client.
    
    Returns:
        An instance manager.
    """
    supabase_client = get_supabase_client()
    return InstanceManager(supabase_client) 