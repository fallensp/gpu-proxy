"""
Utility classes for working with Vast.ai instances.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class VastInstance:
    """
    Helper class for working with Vast.ai instances.
    """
    def __init__(self, instance_data: Dict[str, Any]):
        """
        Initialize a VastInstance with data from Vast.ai API.
        
        Args:
            instance_data: Dictionary containing instance data from Vast.ai API
        """
        self.data = instance_data
        self.id = instance_data.get('id')
        self.vast_id = instance_data.get('vast_id')
        self.status = instance_data.get('status')
        self.label = instance_data.get('label')
        self.image = instance_data.get('image')
        self.provider = instance_data.get('provider', 'vast.ai')
        self.details = instance_data.get('details', {})
    
    @property
    def is_running(self) -> bool:
        """Check if the instance is running."""
        return self.status == 'running'
    
    @property
    def is_stopped(self) -> bool:
        """Check if the instance is stopped."""
        return self.status == 'stopped'
    
    @property
    def is_terminated(self) -> bool:
        """Check if the instance is terminated."""
        return self.status == 'terminated'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the instance to a dictionary."""
        return self.data

class VastUtils:
    """
    Utility methods for working with Vast.ai instances.
    """
    @staticmethod
    def parse_instance_response(response: Dict[str, Any]) -> VastInstance:
        """
        Parse a response from Vast.ai API into a VastInstance object.
        
        Args:
            response: Response from Vast.ai API
        
        Returns:
            VastInstance object
        """
        return VastInstance(response)
    
    @staticmethod
    def get_instance_status(instance_data: Dict[str, Any]) -> str:
        """
        Get the status of an instance.
        
        Args:
            instance_data: Instance data from Vast.ai API
        
        Returns:
            Status of the instance
        """
        return instance_data.get('status', 'unknown')
    
    @staticmethod
    def get_ssh_command(instance_data: Dict[str, Any]) -> Optional[str]:
        """
        Get the SSH command for an instance.
        
        Args:
            instance_data: Instance data from Vast.ai API
        
        Returns:
            SSH command or None if not available
        """
        if not instance_data or 'ssh_host' not in instance_data or 'ssh_port' not in instance_data:
            return None
        
        host = instance_data.get('ssh_host')
        port = instance_data.get('ssh_port')
        username = instance_data.get('ssh_username', 'root')
        
        return f"ssh {username}@{host} -p {port}" 