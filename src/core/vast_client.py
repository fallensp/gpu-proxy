"""
Core module for interacting with the Vast.ai SDK.
"""
import os
import logging
from typing import Dict, Any, Optional, List, Union
import vastai_sdk

logger = logging.getLogger(__name__)

class VastClient:
    """
    Client for interacting with Vast.ai GPU resources using the official SDK.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Vast.ai client.
        
        Args:
            api_key: Optional API key. If not provided, will use the one from environment
                    or from the default location.
        """
        self.api_key = api_key or os.environ.get("VAST_API_KEY")
        self.client = vastai_sdk.VastAI(self.api_key)
        logger.info(f"Initialized Vast.ai client. Credentials source: {self.client.creds_source}")
    
    def search_offers(self, **filters) -> List[Dict[str, Any]]:
        """
        Search for available GPU instances.
        
        Args:
            **filters: Filters to apply to the search.
                      See Vast.ai documentation for available filters.
        
        Returns:
            List of available instances matching the filters.
        """
        logger.debug(f"Searching offers with filters: {filters}")
        
        # Map our API filter names to what the SDK expects if they differ
        filter_mapping = {
            # Add mappings if the SDK uses different parameter names
            # 'our_param_name': 'sdk_param_name',
        }
        
        # Apply mappings and prepare filters for the SDK
        mapped_filters = {}
        for key, value in filters.items():
            # Use the mapped name if it exists, otherwise use the original name
            sdk_key = filter_mapping.get(key, key)
            mapped_filters[sdk_key] = value
        
        logger.debug(f"Mapped filters for SDK: {mapped_filters}")
        
        # Special handling for gpu_name if needed
        if 'gpu_name' in mapped_filters:
            # Some SDKs might require exact formatting or special handling for GPU names
            gpu_name = mapped_filters['gpu_name']
            logger.debug(f"Filtering by GPU name: {gpu_name}")
            
            # If the SDK search_offers doesn't properly filter by GPU name,
            # we might need to do post-filtering
            results = self.client.search_offers(**mapped_filters)
            
            # Check if we need to manually filter results
            if any(offer.get('gpu_name', '').lower() != gpu_name.lower() for offer in results if 'gpu_name' in offer):
                logger.debug("SDK didn't properly filter by GPU name, applying manual filter")
                # Manual filtering as fallback
                filtered_results = [
                    offer for offer in results 
                    if 'gpu_name' in offer and gpu_name.lower() in offer['gpu_name'].lower()
                ]
                return filtered_results
            
            return results
        
        # Normal case - let the SDK handle all filtering
        return self.client.search_offers(**mapped_filters)
    
    def search_offers_with_params(self, query: Optional[str] = None, 
                                 type: str = "on-demand", 
                                 disable_bundling: bool = False,
                                 storage: float = 5.0,
                                 order: str = "score-",
                                 no_default: bool = False) -> List[Dict[str, Any]]:
        """
        Search for available GPU instances with advanced parameters.
        
        Args:
            query: Custom query string (e.g., 'gpu_name=RTX_4090 num_gpus>=2')
            type: Pricing type: 'on-demand', 'reserved', or 'bid'
            disable_bundling: Show identical offers
            storage: Amount of storage to use for pricing, in GiB
            order: Comma-separated list of fields to sort on
            no_default: Disable default query
        
        Returns:
            List of available instances matching the criteria.
        """
        logger.debug(f"Searching offers with params: query={query}, type={type}, disable_bundling={disable_bundling}, storage={storage}, order={order}, no_default={no_default}")
        
        # Prepare parameters for the SDK
        params = {}
        
        if query:
            params['query'] = query
        
        params['type'] = type
        
        if disable_bundling:
            params['disable_bundling'] = True
            
        params['storage'] = storage
        params['order'] = order
        
        if no_default:
            params['no_default'] = True
        
        # Call the SDK method
        return self.client.search_offers(**params)
    
    def show_instances(self) -> List[Dict[str, Any]]:
        """
        Get information about currently rented instances.
        
        Returns:
            List of currently rented instances.
        """
        logger.debug("Fetching current instances")
        return self.client.show_instances()
    
    def create_instance(self, **options) -> Dict[str, Any]:
        """
        Create a new instance.
        
        Args:
            **options: Options for creating the instance.
                      See Vast.ai documentation for available options.
        
        Returns:
            Information about the created instance.
        """
        logger.info(f"Creating instance with options: {options}")
        return self.client.create_instance(**options)
    
    def destroy_instance(self, instance_id: Union[str, int]) -> Dict[str, Any]:
        """
        Destroy an instance.
        
        Args:
            instance_id: ID of the instance to destroy.
        
        Returns:
            Result of the destroy operation.
        """
        logger.info(f"Destroying instance {instance_id}")
        return self.client.destroy_instance(instance_id)
    
    def start_instance(self, instance_id: Union[str, int]) -> Dict[str, Any]:
        """
        Start a stopped instance.
        
        Args:
            instance_id: ID of the instance to start.
        
        Returns:
            Result of the start operation.
        """
        logger.info(f"Starting instance {instance_id}")
        return self.client.start_instance(instance_id)
    
    def stop_instance(self, instance_id: Union[str, int]) -> Dict[str, Any]:
        """
        Stop a running instance.
        
        Args:
            instance_id: ID of the instance to stop.
        
        Returns:
            Result of the stop operation.
        """
        logger.info(f"Stopping instance {instance_id}")
        return self.client.stop_instance(instance_id)
    
    def get_ssh_url(self, instance_id: Union[str, int]) -> str:
        """
        Get the SSH URL for an instance.
        
        Args:
            instance_id: ID of the instance.
        
        Returns:
            SSH URL for the instance.
        """
        logger.debug(f"Getting SSH URL for instance {instance_id}")
        return self.client.ssh_url(instance_id)
    
    def get_instance_logs(self, instance_id: Union[str, int]) -> Dict[str, Any]:
        """
        Get logs for an instance.
        
        Args:
            instance_id: ID of the instance.
        
        Returns:
            Logs for the instance.
        """
        logger.debug(f"Getting logs for instance {instance_id}")
        return self.client.logs(instance_id)
    
    def change_bid(self, instance_id: Union[str, int], price: float) -> Dict[str, Any]:
        """
        Change the bid price for a spot/interruptible instance.
        
        Args:
            instance_id: ID of the instance.
            price: New bid price in $/hour.
        
        Returns:
            Result of the change bid operation.
        """
        logger.info(f"Changing bid for instance {instance_id} to ${price}/hour")
        return self.client.change_bid(instance_id, price)
    
    def label_instance(self, instance_id: Union[str, int], label: str) -> Dict[str, Any]:
        """
        Assign a string label to an instance.
        
        Args:
            instance_id: ID of the instance.
            label: Label to assign.
        
        Returns:
            Result of the label operation.
        """
        logger.info(f"Labeling instance {instance_id} as '{label}'")
        return self.client.label_instance(instance_id, label)
    
    def search_instances(self, **filters) -> List[Dict[str, Any]]:
        """
        Search through user's rented instances with filters.
        
        Args:
            **filters: Filters to apply to the search.
        
        Returns:
            List of user's instances matching the filters.
        """
        logger.debug(f"Searching instances with filters: {filters}")
        
        # Get all instances
        instances = self.show_instances()
        
        # If no filters, return all instances
        if not filters:
            return instances
        
        # Apply filters
        filtered_instances = instances
        
        # Filter by instance_id if provided
        if 'instance_id' in filters and filters['instance_id'] is not None:
            filtered_instances = [
                instance for instance in filtered_instances
                if instance.get('id') == filters['instance_id']
            ]
        
        # Filter by machine_id if provided
        if 'machine_id' in filters and filters['machine_id'] is not None:
            filtered_instances = [
                instance for instance in filtered_instances
                if instance.get('machine_id') == filters['machine_id']
            ]
        
        # Filter by gpu_name if provided (case-insensitive partial match)
        if 'gpu_name' in filters and filters['gpu_name'] is not None:
            gpu_name = filters['gpu_name'].lower()
            filtered_instances = [
                instance for instance in filtered_instances
                if 'gpu_name' in instance and gpu_name in instance.get('gpu_name', '').lower()
            ]
        
        # Filter by num_gpus if provided
        if 'num_gpus' in filters and filters['num_gpus'] is not None:
            filtered_instances = [
                instance for instance in filtered_instances
                if instance.get('num_gpus') == filters['num_gpus']
            ]
        
        # Filter by ssh_host if provided
        if 'ssh_host' in filters and filters['ssh_host'] is not None:
            filtered_instances = [
                instance for instance in filtered_instances
                if filters['ssh_host'] in instance.get('ssh_host', '')
            ]
        
        # Filter by ssh_port if provided
        if 'ssh_port' in filters and filters['ssh_port'] is not None:
            filtered_instances = [
                instance for instance in filtered_instances
                if instance.get('ssh_port') == filters['ssh_port']
            ]
        
        # Filter by label if provided (case-insensitive partial match)
        if 'label' in filters and filters['label'] is not None:
            label = filters['label'].lower()
            filtered_instances = [
                instance for instance in filtered_instances
                if 'label' in instance and label in instance.get('label', '').lower()
            ]
        
        # Filter by status if provided
        if 'status' in filters and filters['status'] is not None:
            status = filters['status'].lower()
            filtered_instances = [
                instance for instance in filtered_instances
                if instance.get('actual_status', '').lower() == status
            ]
        
        # Filter by image if provided (case-insensitive partial match)
        if 'image' in filters and filters['image'] is not None:
            image = filters['image'].lower()
            filtered_instances = [
                instance for instance in filtered_instances
                if 'image' in instance and image in instance.get('image', '').lower()
            ]
        
        # Filter by disk_space if provided
        if 'disk_space' in filters and filters['disk_space'] is not None:
            filtered_instances = [
                instance for instance in filtered_instances
                if instance.get('disk_space', 0) >= filters['disk_space']
            ]
        
        logger.debug(f"Found {len(filtered_instances)} instances matching filters")
        return filtered_instances
    
    def create_autoscaler(self, **options) -> Dict[str, Any]:
        """
        Create a new autoscaler group.
        
        Args:
            **options: Options for creating the autoscaler group.
                      See Vast.ai documentation for available options.
        
        Returns:
            Information about the created autoscaler group.
        """
        logger.info(f"Creating autoscaler group with options: {options}")
        return self.client.create_autoscaler(**options)
    
    def show_autoscalers(self) -> List[Dict[str, Any]]:
        """
        Get information about user's autoscaler groups.
        
        Returns:
            List of autoscaler groups.
        """
        logger.debug("Fetching autoscaler groups")
        return self.client.show_autoscalers()
    
    def update_autoscaler(self, autoscaler_id: Union[str, int], **options) -> Dict[str, Any]:
        """
        Update an existing autoscaler group.
        
        Args:
            autoscaler_id: ID of the autoscaler group to update.
            **options: Options to update.
        
        Returns:
            Result of the update operation.
        """
        logger.info(f"Updating autoscaler group {autoscaler_id} with options: {options}")
        return self.client.update_autoscaler(autoscaler_id, **options)
    
    def delete_autoscaler(self, autoscaler_id: Union[str, int]) -> Dict[str, Any]:
        """
        Delete an autoscaler group.
        
        Args:
            autoscaler_id: ID of the autoscaler group to delete.
        
        Returns:
            Result of the delete operation.
        """
        logger.info(f"Deleting autoscaler group {autoscaler_id}")
        return self.client.delete_autoscaler(autoscaler_id) 