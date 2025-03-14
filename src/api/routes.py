"""
API routes for the GPU Proxy API.
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from src.core.vast_client import VastClient
from src.api.models import (
    ErrorResponse, 
    InstanceCreate, 
    InstanceBidChange, 
    InstanceLabel,
    SearchFilters,
    InstanceSearchFilters,
    AutoscalerCreate,
    SearchOffersParams
)

logger = logging.getLogger(__name__)
router = APIRouter()

def get_vast_client() -> VastClient:
    """Dependency to get the Vast.ai client."""
    return VastClient()

@router.get("/", summary="API Status")
async def get_status():
    """Get the API status."""
    return {"status": "online", "service": "GPU Proxy for Vast.ai"}

@router.get(
    "/instances", 
    summary="List Available Instances",
    response_model=List[Dict[str, Any]],
    responses={500: {"model": ErrorResponse}}
)
async def list_instances(
    filters: SearchFilters = Depends(),
    client: VastClient = Depends(get_vast_client)
):
    """
    List available GPU instances with optional filtering.
    
    This endpoint supports all the filtering options available in the Vast.ai SDK:
    
    - **GPU-related filters**: min_gpus, max_gpus, gpu_name, gpu_ram, cuda_vers, pci_gen, gpu_mem_bw, flops
    - **System-related filters**: disk_space, ram, inet_up, inet_down, reliability, dlperf, dlperf_usd, num_cpus
    - **Pricing and availability filters**: max_price, min_bid, verified, external, order, disable_bundling
    
    You can combine multiple filters to narrow down your search.
    
    Note: For gpu_name, you can use values like "RTX 3090", "A100", etc. The filter is case-insensitive
    and will match partial names.
    """
    try:
        # Convert the filters model to a dictionary, excluding None values
        filter_dict = {k: v for k, v in filters.model_dump().items() if v is not None}
        
        # Handle extra filters if provided
        if filters.extra:
            filter_dict.update(filters.extra)
            del filter_dict["extra"]
        
        logger.debug(f"API received filters: {filter_dict}")
        
        # Get results with filters applied
        results = client.search_offers(**filter_dict)
        
        # Log the number of results for debugging
        logger.debug(f"Found {len(results)} instances matching filters")
        
        return results
    except Exception as e:
        logger.exception("Error listing instances")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/my-instances", 
    summary="Get My Instances",
    response_model=List[Dict[str, Any]],
    responses={500: {"model": ErrorResponse}}
)
async def get_my_instances(client: VastClient = Depends(get_vast_client)):
    """
    Get information about currently rented instances.
    """
    try:
        return client.show_instances()
    except Exception as e:
        logger.exception("Error getting instances")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/instances", 
    summary="Create Instance",
    response_model=Dict[str, Any],
    responses={500: {"model": ErrorResponse}}
)
async def create_instance(
    instance: InstanceCreate,
    client: VastClient = Depends(get_vast_client)
):
    """
    Create a new GPU instance.
    """
    try:
        # Convert the instance model to a dictionary, excluding None values
        instance_dict = {k: v for k, v in instance.model_dump().items() if v is not None}
        
        # Handle extra options if provided
        if instance.extra:
            instance_dict.update(instance.extra)
            del instance_dict["extra"]
            
        return client.create_instance(**instance_dict)
    except Exception as e:
        logger.exception("Error creating instance")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete(
    "/instances/{instance_id}", 
    summary="Destroy Instance",
    response_model=Dict[str, Any],
    responses={500: {"model": ErrorResponse}}
)
async def destroy_instance(
    instance_id: int,
    client: VastClient = Depends(get_vast_client)
):
    """
    Destroy an instance.
    """
    try:
        return client.destroy_instance(instance_id)
    except Exception as e:
        logger.exception(f"Error destroying instance {instance_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/instances/{instance_id}/start", 
    summary="Start Instance",
    response_model=Dict[str, Any],
    responses={500: {"model": ErrorResponse}}
)
async def start_instance(
    instance_id: int,
    client: VastClient = Depends(get_vast_client)
):
    """
    Start a stopped instance.
    """
    try:
        return client.start_instance(instance_id)
    except Exception as e:
        logger.exception(f"Error starting instance {instance_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/instances/{instance_id}/stop", 
    summary="Stop Instance",
    response_model=Dict[str, Any],
    responses={500: {"model": ErrorResponse}}
)
async def stop_instance(
    instance_id: int,
    client: VastClient = Depends(get_vast_client)
):
    """
    Stop a running instance.
    """
    try:
        return client.stop_instance(instance_id)
    except Exception as e:
        logger.exception(f"Error stopping instance {instance_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/instances/{instance_id}/ssh", 
    summary="Get SSH URL",
    response_model=Dict[str, str],
    responses={500: {"model": ErrorResponse}}
)
async def get_ssh_url(
    instance_id: int,
    client: VastClient = Depends(get_vast_client)
):
    """
    Get the SSH URL for an instance.
    """
    try:
        ssh_url = client.get_ssh_url(instance_id)
        return {"ssh_url": ssh_url}
    except Exception as e:
        logger.exception(f"Error getting SSH URL for instance {instance_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/instances/{instance_id}/logs", 
    summary="Get Instance Logs",
    response_model=Dict[str, Any],
    responses={500: {"model": ErrorResponse}}
)
async def get_instance_logs(
    instance_id: int,
    client: VastClient = Depends(get_vast_client)
):
    """
    Get logs for an instance.
    """
    try:
        return client.get_instance_logs(instance_id)
    except Exception as e:
        logger.exception(f"Error getting logs for instance {instance_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch(
    "/instances/{instance_id}/bid", 
    summary="Change Bid Price",
    response_model=Dict[str, Any],
    responses={500: {"model": ErrorResponse}}
)
async def change_bid(
    instance_id: int,
    bid: InstanceBidChange,
    client: VastClient = Depends(get_vast_client)
):
    """
    Change the bid price for a spot/interruptible instance.
    """
    try:
        return client.change_bid(instance_id, bid.price)
    except Exception as e:
        logger.exception(f"Error changing bid for instance {instance_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch(
    "/instances/{instance_id}/label", 
    summary="Label Instance",
    response_model=Dict[str, Any],
    responses={500: {"model": ErrorResponse}}
)
async def label_instance(
    instance_id: int,
    label_data: InstanceLabel,
    client: VastClient = Depends(get_vast_client)
):
    """
    Assign a string label to an instance.
    """
    try:
        return client.label_instance(instance_id, label_data.label)
    except Exception as e:
        logger.exception(f"Error labeling instance {instance_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/debug/filters", 
    summary="Debug Filter Processing",
    response_model=Dict[str, Any],
    responses={500: {"model": ErrorResponse}}
)
async def debug_filters(
    filters: SearchFilters = Depends(),
    client: VastClient = Depends(get_vast_client)
):
    """
    Debug endpoint to see how filters are processed.
    
    This endpoint shows:
    1. The raw filters received from the API request
    2. How they are processed before being sent to the Vast.ai SDK
    3. The number of results that would be returned
    
    This is useful for troubleshooting filter issues.
    """
    try:
        # Convert the filters model to a dictionary, excluding None values
        filter_dict = {k: v for k, v in filters.model_dump().items() if v is not None}
        
        # Handle extra filters if provided
        if filters.extra:
            filter_dict.update(filters.extra)
            del filter_dict["extra"]
        
        # Get a sample of results (limited to 5) to check if filters work
        results = client.search_offers(**filter_dict)
        sample_results = results[:5] if results else []
        
        # Prepare debug information
        debug_info = {
            "received_filters": filter_dict,
            "total_results_count": len(results),
            "sample_results": sample_results,
            "filter_tips": {
                "gpu_name": "For gpu_name, try exact model names like 'RTX 4090', 'A100', etc.",
                "min_gpus": "For min_gpus, use integer values (1, 2, 4, etc.)",
                "max_price": "For max_price, use float values in $/hour (0.5, 1.0, etc.)"
            }
        }
        
        return debug_info
    except Exception as e:
        logger.exception("Error in debug filters endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/search/instances", 
    summary="Search My Instances",
    response_model=List[Dict[str, Any]],
    responses={500: {"model": ErrorResponse}}
)
async def search_instances(
    filters: InstanceSearchFilters = Depends(),
    client: VastClient = Depends(get_vast_client)
):
    """
    Search through your rented instances with filters.
    
    This endpoint allows you to filter your currently rented instances by various criteria:
    
    - **Instance properties**: instance_id, machine_id, num_gpus, disk_space
    - **GPU properties**: gpu_name
    - **Connection properties**: ssh_host, ssh_port
    - **Metadata**: label, status, image
    
    You can combine multiple filters to narrow down your search.
    
    Note: This searches only through instances you have already rented, not available offers.
    For searching available offers, use the `/instances` endpoint.
    """
    try:
        # Convert the filters model to a dictionary, excluding None values
        filter_dict = {k: v for k, v in filters.model_dump().items() if v is not None}
        
        # Handle extra filters if provided
        if filters.extra:
            filter_dict.update(filters.extra)
            del filter_dict["extra"]
        
        logger.debug(f"API received instance search filters: {filter_dict}")
        
        # Get results with filters applied
        results = client.search_instances(**filter_dict)
        
        # Log the number of results for debugging
        logger.debug(f"Found {len(results)} instances matching filters")
        
        return results
    except Exception as e:
        logger.exception("Error searching instances")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/debug/search/instances", 
    summary="Debug Instance Search Filters",
    response_model=Dict[str, Any],
    responses={500: {"model": ErrorResponse}}
)
async def debug_search_instances(
    filters: InstanceSearchFilters = Depends(),
    client: VastClient = Depends(get_vast_client)
):
    """
    Debug endpoint to see how instance search filters are processed.
    
    This endpoint shows:
    1. The raw filters received from the API request
    2. How they are processed
    3. The number of results that would be returned
    4. Sample results
    
    This is useful for troubleshooting filter issues when searching your instances.
    """
    try:
        # Convert the filters model to a dictionary, excluding None values
        filter_dict = {k: v for k, v in filters.model_dump().items() if v is not None}
        
        # Handle extra filters if provided
        if filters.extra:
            filter_dict.update(filters.extra)
            del filter_dict["extra"]
        
        # Get all instances first (for comparison)
        all_instances = client.show_instances()
        
        # Get filtered instances
        filtered_instances = client.search_instances(**filter_dict)
        
        # Prepare sample results (limited to 2 for brevity)
        sample_results = filtered_instances[:2] if filtered_instances else []
        
        # Prepare debug information
        debug_info = {
            "received_filters": filter_dict,
            "total_instances_count": len(all_instances),
            "filtered_instances_count": len(filtered_instances),
            "sample_results": sample_results,
            "filter_tips": {
                "instance_id": "For instance_id, use the exact ID number",
                "gpu_name": "For gpu_name, try values like 'RTX 4090', 'A100', etc. (case-insensitive, partial match)",
                "status": "For status, try values like 'running', 'stopped', etc.",
                "label": "For label, use text that appears in your instance labels (case-insensitive, partial match)"
            }
        }
        
        return debug_info
    except Exception as e:
        logger.exception("Error in debug search instances endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/autoscalers", 
    summary="Get Autoscaler Groups",
    response_model=List[Dict[str, Any]],
    responses={500: {"model": ErrorResponse}}
)
async def get_autoscalers(client: VastClient = Depends(get_vast_client)):
    """
    Get information about user's autoscaler groups.
    """
    try:
        return client.show_autoscalers()
    except Exception as e:
        logger.exception("Error getting autoscaler groups")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/autoscalers", 
    summary="Create Autoscaler Group",
    response_model=Dict[str, Any],
    responses={500: {"model": ErrorResponse}}
)
async def create_autoscaler(
    autoscaler: AutoscalerCreate,
    client: VastClient = Depends(get_vast_client)
):
    """
    Create a new autoscaler group to manage a pool of worker instances.
    
    An autoscaler group automatically manages a pool of instances based on load,
    scaling up or down as needed. This is useful for deploying services that
    need to handle variable load.
    """
    try:
        # Convert the autoscaler model to a dictionary, excluding None values
        autoscaler_dict = {k: v for k, v in autoscaler.model_dump().items() if v is not None}
        
        return client.create_autoscaler(**autoscaler_dict)
    except Exception as e:
        logger.exception("Error creating autoscaler group")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch(
    "/autoscalers/{autoscaler_id}", 
    summary="Update Autoscaler Group",
    response_model=Dict[str, Any],
    responses={500: {"model": ErrorResponse}}
)
async def update_autoscaler(
    autoscaler_id: int,
    autoscaler: AutoscalerCreate,
    client: VastClient = Depends(get_vast_client)
):
    """
    Update an existing autoscaler group.
    """
    try:
        # Convert the autoscaler model to a dictionary, excluding None values
        autoscaler_dict = {k: v for k, v in autoscaler.model_dump().items() if v is not None}
        
        return client.update_autoscaler(autoscaler_id, **autoscaler_dict)
    except Exception as e:
        logger.exception(f"Error updating autoscaler group {autoscaler_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete(
    "/autoscalers/{autoscaler_id}", 
    summary="Delete Autoscaler Group",
    response_model=Dict[str, Any],
    responses={500: {"model": ErrorResponse}}
)
async def delete_autoscaler(
    autoscaler_id: int,
    client: VastClient = Depends(get_vast_client)
):
    """
    Delete an autoscaler group.
    
    Note: This does not automatically destroy the instances that are associated with the autoscaler group.
    """
    try:
        return client.delete_autoscaler(autoscaler_id)
    except Exception as e:
        logger.exception(f"Error deleting autoscaler group {autoscaler_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/search/offers", 
    summary="Search Available Offers",
    response_model=List[Dict[str, Any]],
    responses={500: {"model": ErrorResponse}}
)
async def search_offers(
    params: SearchOffersParams = Depends(),
    client: VastClient = Depends(get_vast_client)
):
    """
    Search for available GPU instances with advanced filtering.
    
    This endpoint allows you to search for available GPU instances that you can rent,
    with advanced filtering options similar to the 'vastai search offers' CLI command.
    
    The query parameter uses the same syntax as the CLI:
    
    - Simple comparisons: 'field op value'
    - Multiple comparisons: 'field1 op1 value1 field2 op2 value2'
    - Operators: <, <=, ==, !=, >=, >, in, notin
    
    Example queries:
    - 'gpu_name=RTX_4090 num_gpus>=2'
    - 'reliability > 0.98 num_gpus=1 gpu_name=RTX_3090'
    - 'compute_cap > 610 total_flops > 5 datacenter=True'
    
    Note: For string values with spaces, replace spaces with underscores
    (e.g., use 'RTX_3090' instead of 'RTX 3090').
    """
    try:
        # Convert the params model to a dictionary, excluding None values
        params_dict = {k: v for k, v in params.model_dump().items() if v is not None}
        
        logger.debug(f"API received search offers params: {params_dict}")
        
        # Get results with params applied
        results = client.search_offers_with_params(**params_dict)
        
        # Log the number of results for debugging
        logger.debug(f"Found {len(results)} offers matching criteria")
        
        return results
    except Exception as e:
        logger.exception("Error searching offers")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/debug/search/offers", 
    summary="Debug Search Offers",
    response_model=Dict[str, Any],
    responses={500: {"model": ErrorResponse}}
)
async def debug_search_offers(
    params: SearchOffersParams = Depends(),
    client: VastClient = Depends(get_vast_client)
):
    """
    Debug endpoint to see how search offers parameters are processed.
    
    This endpoint shows:
    1. The raw parameters received from the API request
    2. How they are processed
    3. The number of results that would be returned
    4. Sample results
    
    This is useful for troubleshooting search issues.
    """
    try:
        # Convert the params model to a dictionary, excluding None values
        params_dict = {k: v for k, v in params.model_dump().items() if v is not None}
        
        logger.debug(f"API received search offers params: {params_dict}")
        
        # Get results with params applied
        results = client.search_offers_with_params(**params_dict)
        
        # Prepare sample results (limited to 3 for brevity)
        sample_results = results[:3] if results else []
        
        # Prepare debug information
        debug_info = {
            "received_params": params_dict,
            "total_results_count": len(results),
            "sample_results": sample_results,
            "query_tips": {
                "gpu_name": "For gpu_name, use values like 'RTX_4090', 'A100', etc. (replace spaces with underscores)",
                "num_gpus": "For num_gpus, use operators like =, >=, <= (e.g., 'num_gpus>=2')",
                "reliability": "For reliability, use values between 0 and 1 (e.g., 'reliability>0.98')",
                "examples": [
                    "gpu_name=RTX_4090 num_gpus>=2",
                    "reliability > 0.98 num_gpus=1 gpu_name=RTX_3090",
                    "compute_cap > 610 total_flops > 5 datacenter=True"
                ]
            }
        }
        
        return debug_info
    except Exception as e:
        logger.exception("Error in debug search offers endpoint")
        raise HTTPException(status_code=500, detail=str(e)) 