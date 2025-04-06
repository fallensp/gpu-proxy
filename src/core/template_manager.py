"""
Template manager module for managing instance templates.
"""
import logging
from typing import Dict, Any, List, Optional
from src.core.db import get_supabase_client
import uuid

logger = logging.getLogger(__name__)

# Default templates
DEFAULT_TEMPLATES = [
    {
        "name": "ComfyUI",
        "description": "ComfyUI with CUDA 12.1 and PyTorch 2.5.1",
        "image": "vastai/comfy:v0.3.13-cuda-12.1-pytorch-2.5.1-py311",
        "env_params": '-p 1111:1111 -p 8080:8080 -p 8384:8384 -p 72299:72299 -p 8188:8188 -e OPEN_BUTTON_PORT=1111 -e OPEN_BUTTON_TOKEN=1 -e JUPYTER_DIR=/ -e DATA_DIRECTORY=/workspace/ -e PORTAL_CONFIG="localhost:1111:11111:/:Instance Portal|localhost:8188:18188:/:ComfyUI|localhost:8080:18080:/:Jupyter|localhost:8080:18080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing" -e PROVISIONING_SCRIPT=https://raw.githubusercontent.com/vast-ai/base-image/refs/heads/main/derivatives/pytorch/derivatives/comfyui/provisioning_scripts/flux.sh -e COMFYUI_ARGS="--disable-auto-launch --port 18188 --enable-cors-header"',
        "onstart_cmd": "entrypoint.sh",
        "disk_size": 100,
        "use_ssh": True,
        "use_direct": True,
        "template_type": "system",
        "tags": ["comfyui", "ai", "stable-diffusion"],
        "is_public": True,
        "is_featured": True
    }
    # Add more default templates here as needed
]

class TemplateManager:
    """
    Manager for instance templates.
    """
    
    def __init__(self, supabase_client=None):
        """
        Initialize the template manager.
        
        Args:
            supabase_client: Supabase client. If None, one will be created.
        """
        self.client = supabase_client or get_supabase_client()
    
    async def create_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new instance template.
        
        Args:
            template_data: Data for the new template.
            
        Returns:
            The created template.
        """
        try:
            result = self.client.table("instance_templates").insert(template_data).execute()
            if result and hasattr(result, 'data') and result.data:
                logger.info(f"Created template: {result.data[0]['id']}")
                return result.data[0]
            else:
                logger.error("Failed to create template: No data returned")
                return {}
        except Exception as e:
            logger.exception(f"Error creating template: {str(e)}")
            raise
    
    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a template by ID.
        
        Args:
            template_id: ID of the template to get.
            
        Returns:
            The template data or None if not found.
        """
        try:
            result = self.client.table("instance_templates").select("*").eq("id", template_id).execute()
            if result and hasattr(result, 'data') and result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.exception(f"Error getting template {template_id}: {str(e)}")
            raise
    
    async def update_template(self, template_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a template.
        
        Args:
            template_id: ID of the template to update.
            update_data: Data to update.
            
        Returns:
            The updated template.
        """
        try:
            # Add updated_at timestamp
            if "updated_at" not in update_data:
                from datetime import datetime
                update_data["updated_at"] = datetime.now().isoformat()
                
            result = self.client.table("instance_templates").update(update_data).eq("id", template_id).execute()
            if result and hasattr(result, 'data') and result.data:
                logger.info(f"Updated template: {template_id}")
                return result.data[0]
            else:
                logger.error(f"Failed to update template {template_id}: No data returned")
                return {}
        except Exception as e:
            logger.exception(f"Error updating template {template_id}: {str(e)}")
            raise
    
    async def delete_template(self, template_id: str) -> bool:
        """
        Delete a template.
        
        Args:
            template_id: ID of the template to delete.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            result = self.client.table("instance_templates").delete().eq("id", template_id).execute()
            if result and hasattr(result, 'data') and result.data:
                logger.info(f"Deleted template: {template_id}")
                return True
            else:
                logger.error(f"Failed to delete template {template_id}: No data returned")
                return False
        except Exception as e:
            logger.exception(f"Error deleting template {template_id}: {str(e)}")
            raise
    
    async def list_templates(self, 
                            user_id: Optional[str] = None, 
                            include_public: bool = True,
                            template_type: Optional[str] = None,
                            tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        List templates, optionally filtered by user ID, template type, and tags.
        
        Args:
            user_id: Filter by user ID.
            include_public: Whether to include public templates.
            template_type: Filter by template type.
            tags: Filter by tags.
            
        Returns:
            List of templates.
        """
        try:
            query = self.client.table("instance_templates").select("*")
            
            # Apply filters
            filters = []
            if user_id:
                filters.append(f"user_id.eq.{user_id}")
                
            if include_public:
                if user_id:
                    # Get user's templates OR public templates
                    query = query.or_(f"user_id.eq.{user_id},is_public.eq.true")
                else:
                    # Only get public templates
                    query = query.eq("is_public", True)
            else:
                if user_id:
                    # Only get user's templates
                    query = query.eq("user_id", user_id)
                    
            if template_type:
                query = query.eq("template_type", template_type)
                
            if tags and len(tags) > 0:
                # Filter by tags (if any tag matches)
                tag_filter = f"tags.cs.{{{','.join(tags)}}}"
                query = query.or_(tag_filter)
                
            # Execute the query
            result = query.order("name").execute()
            
            templates = result.data if result and hasattr(result, 'data') else []
            return templates
        except Exception as e:
            logger.exception(f"Error listing templates: {str(e)}")
            raise

    async def create_default_templates(self) -> List[Dict[str, Any]]:
        """
        Create default templates if they don't exist.
        
        Returns:
            List of created templates.
        """
        created_templates = []
        
        try:
            for template_data in DEFAULT_TEMPLATES:
                # Check if template with same name and type already exists
                existing = await self.find_template_by_name_and_type(
                    template_data["name"], 
                    template_data["template_type"]
                )
                
                if not existing:
                    # Add a unique ID to ensure we don't get conflicts
                    if "id" not in template_data:
                        template_data["id"] = str(uuid.uuid4())
                        
                    result = await self.create_template(template_data)
                    if result:
                        created_templates.append(result)
                        logger.info(f"Created default template: {template_data['name']}")
                else:
                    logger.info(f"Default template already exists: {template_data['name']}")
            
            return created_templates
        except Exception as e:
            logger.exception(f"Error creating default templates: {str(e)}")
            return []
    
    async def find_template_by_name_and_type(self, name: str, template_type: str) -> Optional[Dict[str, Any]]:
        """
        Find a template by name and type.
        
        Args:
            name: Name of the template.
            template_type: Type of the template.
            
        Returns:
            The template data or None if not found.
        """
        try:
            result = self.client.table("instance_templates").select("*").eq("name", name).eq("template_type", template_type).execute()
            if result and hasattr(result, 'data') and result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.exception(f"Error finding template by name and type: {str(e)}")
            return None

# Create a global instance for dependency injection
_template_manager = None

def get_template_manager():
    """
    Get the template manager instance.
    
    Returns:
        The template manager.
    """
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager 