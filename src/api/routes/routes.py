"""
API routes for the GPU Proxy API.
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
import requests
import os
from datetime import datetime
from pydantic import BaseModel
import json
import time
import traceback
import uuid

from src.core.vast_client import VastClient
from src.core.instance_manager import get_instance_manager, InstanceManager
from src.core.scheduler import get_scheduler, JobScheduler
from src.core.db import get_supabase_client, log_api_call
from src.core.template_manager import get_template_manager, TemplateManager
from src.core.schedule_manager import get_schedule_manager, ScheduleManager
from src.api.models import (
    ErrorResponse, 
    InstanceCreate, 
    InstanceBidChange, 
    InstanceLabel,
    SearchFilters,
    InstanceSearchFilters,
    AutoscalerCreate,
    SearchOffersParams,
    InstanceTemplateCreate,
    InstanceTemplateUpdate
)
from ...utils.vast_utils import VastUtils, VastInstance

# Models for scheduling
class ScheduleInstanceCreate(BaseModel):
    """Model for scheduling instance creation."""
    instance_params: Dict[str, Any]
    schedule_time: datetime
    
class ScheduleInstanceShutdown(BaseModel):
    """Model for scheduling instance shutdown."""
    instance_id: str
    schedule_time: datetime

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
    responses={500: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}
)
async def create_instance(
    request: Request,
    instance: InstanceCreate,
    client: VastClient = Depends(get_vast_client),
    instance_manager: InstanceManager = Depends(get_instance_manager),
    supabase_client = Depends(get_supabase_client),
    schedule_manager = Depends(get_schedule_manager)
):
    """
    Create a new GPU instance.
    """
    # Record start time for calculating duration
    start_time = time.time()
    
    # Store request payload for logging
    request_payload = instance.model_dump(exclude_none=True)
    response_payload = None
    status = "success"
    status_code = 200
    error_message = None
    vast_id = None
    instance_db_id = None
    schedule_id = None
    
    try:
        # Convert the instance model to a dictionary, excluding None values
        instance_dict = {k: v for k, v in instance.model_dump().items() if v is not None}
        
        # Handle extra options if provided
        if instance.extra:
            instance_dict.update(instance.extra)
            del instance_dict["extra"]
        
        # Check if schedule creation is requested
        create_schedule = instance_dict.get("create_schedule", False)
        schedule_data = instance_dict.get("schedule", {})
        
        # Log scheduling information for debugging
        logger.info(f"[SCHEDULE_DEBUG] create_schedule flag: {create_schedule}")
        logger.info(f"[SCHEDULE_DEBUG] schedule_data: {json.dumps(schedule_data, default=str)}")
        
        # Remove schedule data from instance params before sending to Vast.ai
        if "create_schedule" in instance_dict:
            del instance_dict["create_schedule"]
        if "schedule" in instance_dict:
            del instance_dict["schedule"]
        
        # Create the instance on Vast.ai
        vast_response = client.create_instance(**instance_dict)
        
        # Store the response for logging
        response_payload = vast_response
        vast_id = vast_response.get("new_contract")
        
        # Store the instance data in Supabase
        try:
            # Extract relevant information from the Vast.ai response
            db_instance_data = {
                "vast_id": vast_id,
                "offer_id": instance.id,
                "label": instance.label,
                "image": instance.image,
                "disk_size": instance.disk,
                "status": "creating",
                "provider": "vast.ai",
                "details": vast_response
            }
            
            # Add user_id if authentication is implemented
            # db_instance_data["user_id"] = user.id
            
            # Store in database
            db_result = await instance_manager.create_instance(db_instance_data)
            if db_result and "id" in db_result:
                instance_db_id = db_result["id"]
            
            logger.info(f"Stored instance {vast_id} in database")
            
            # Create schedule if requested
            if create_schedule and schedule_data:
                logger.info(f"[SCHEDULE_DEBUG] Preparing to create schedule for instance {vast_id}")
                try:
                    # Prepare schedule data
                    gpu_type = "Custom"  # Default value
                    if vast_response.get("machine", {}).get("gpu_name"):
                        gpu_type = vast_response["machine"]["gpu_name"]
                    
                    # Make sure we have all required fields
                    if not schedule_data.get("start_schedule"):
                        logger.error("[SCHEDULE_DEBUG] Missing required field: start_schedule")
                        vast_response["schedule_error"] = "Missing required schedule field: start_schedule"
                        return vast_response
                        
                    if not schedule_data.get("stop_schedule"):
                        logger.error("[SCHEDULE_DEBUG] Missing required field: stop_schedule")
                        vast_response["schedule_error"] = "Missing required schedule field: stop_schedule"
                        return vast_response
                        
                    # Create the pod_schedule with all required fields
                    pod_schedule = {
                        "id": str(uuid.uuid4()),  # Generate a UUID for the schedule
                        "name": instance.label or f"Schedule for pod {vast_id}",
                        "gpu_type": gpu_type,
                        "min_specs": {},  # Could extract from the offer
                        "num_gpus": instance_dict.get("num_gpus", 1),
                        "disk_size": instance.disk,
                        "docker_image": instance.image,
                        "use_ssh": True if instance_dict.get("docker_args") and "22:22" in instance_dict.get("docker_args") else False,
                        "start_schedule": schedule_data.get("start_schedule"),
                        "stop_schedule": schedule_data.get("stop_schedule"),
                        "timezone": schedule_data.get("timezone", "UTC"),
                        "last_instance_id": str(vast_id),
                        "is_active": True,
                        # Use a default system user ID instead of null
                        "user_id": "e554e24e-91b9-4db6-ae43-f1d468fc40cf"  # Valid user ID
                    }
                    
                    # Convert any dict/list fields to proper JSON strings for logging
                    log_schedule = pod_schedule.copy()
                    for key, value in log_schedule.items():
                        if isinstance(value, (dict, list)):
                            log_schedule[key] = json.dumps(value)
                    
                    # Log the full schedule data
                    logger.info(f"[SCHEDULE_DEBUG] Final pod_schedule to be created: {json.dumps(log_schedule, default=str)}")
                    
                    # Create the schedule
                    logger.info(f"[SCHEDULE_DEBUG] Calling schedule_manager.create_schedule")
                    schedule_result = await schedule_manager.create_schedule(pod_schedule)
                    
                    if schedule_result and "error" in schedule_result and schedule_result.get("needs_table_creation"):
                        # Special case: Table needs to be created
                        logger.error("[SCHEDULE_DEBUG] Cannot create schedule: pod_schedules table does not exist")
                        logger.error("[SCHEDULE_DEBUG] Please create the table using the SQL in the logs")
                        # Add this info to the response so the frontend can show a useful message
                        vast_response["schedule_error"] = "Database table not ready. Please contact support to set up the scheduling system."
                    elif schedule_result and "id" in schedule_result:
                        schedule_id = schedule_result["id"]
                        logger.info(f"[SCHEDULE_DEBUG] Successfully created schedule {schedule_id} for instance {vast_id}")
                        
                        # Add schedule info to response
                        vast_response["schedule"] = {
                            "id": schedule_id,
                            "start_schedule": schedule_data.get("start_schedule"),
                            "stop_schedule": schedule_data.get("stop_schedule")
                        }
                    else:
                        logger.warning(f"[SCHEDULE_DEBUG] Schedule created but no ID returned for instance {vast_id}")
                        if schedule_result:
                            logger.warning(f"[SCHEDULE_DEBUG] Schedule result: {json.dumps(schedule_result, default=str)}")
                        else:
                            logger.warning("[SCHEDULE_DEBUG] Schedule result is None")
                except Exception as schedule_error:
                    logger.error(f"[SCHEDULE_DEBUG] Failed to create schedule for instance {vast_id}: {str(schedule_error)}")
                    logger.error(f"[SCHEDULE_DEBUG] Exception traceback: {traceback.format_exc()}")
                    # Continue with instance creation even if schedule creation fails
            else:
                logger.info(f"[SCHEDULE_DEBUG] No schedule will be created: create_schedule={create_schedule}, has_schedule_data={bool(schedule_data)}")
        except Exception as db_error:
            # Log the error but don't fail the request
            logger.error(f"Failed to store instance in database: {str(db_error)}")
        
        return vast_response
    except HTTPException as e:
        # Update status for logging
        status = "error"
        status_code = e.status_code
        error_message = str(e.detail)
        # Re-raise existing HTTP exceptions
        raise e
    except requests.exceptions.HTTPError as e:
        # Update status for logging
        status = "error"
        status_code = e.response.status_code if hasattr(e, 'response') and hasattr(e.response, 'status_code') else 500
        
        # Handle different HTTP errors from the Vast.ai API
        if e.response.status_code == 404:
            error_message = f"GPU offer with ID {instance.id} not found or no longer available"
            logger.warning(f"Offer ID {instance.id} not found on Vast.ai")
            raise HTTPException(
                status_code=404, 
                detail=f"GPU offer with ID {instance.id} not found or no longer available. Please select another GPU offer."
            )
        elif e.response.status_code == 400:
            # Try to extract the error message from the response
            try:
                error_json = e.response.json()
                error_msg = error_json.get("msg", str(e))
                error_type = error_json.get("error", "bad_request")
                error_message = f"{error_type}: {error_msg}"
                detail = error_message
            except ValueError:
                detail = str(e)
                error_message = str(e)
            
            logger.warning(f"Bad request error creating instance: {detail}")
            raise HTTPException(status_code=400, detail=detail)
        else:
            # For other HTTP errors
            error_message = str(e)
            logger.exception(f"HTTP error creating instance: {error_message}")
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        # Update status for logging
        status = "error"
        status_code = 500
        error_message = str(e)
        logger.exception("Error creating instance")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Calculate request duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Get client IP address
        client_ip = request.client.host if request and hasattr(request, 'client') else None
        
        # Log the API call
        await log_api_call(
            client=supabase_client,
            endpoint="/instances",
            method="POST",
            request_payload=request_payload,
            response_payload=response_payload,
            status=status,
            status_code=status_code,
            error_message=error_message,
            vast_id=vast_id,
            instance_id=instance_db_id,
            ip_address=client_ip,
            duration_ms=duration_ms
        )

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

@router.post(
    "/instance-records", 
    summary="Create Instance Record",
    response_model=Dict[str, Any],
    responses={500: {"model": ErrorResponse}}
)
async def create_instance_record(
    instance_data: Dict[str, Any],
    instance_manager: InstanceManager = Depends(get_instance_manager)
):
    """
    Create a new instance record in the database.
    
    This endpoint stores information about a GPU instance in the database,
    allowing you to track your instances even after they are destroyed.
    """
    try:
        result = await instance_manager.create_instance(instance_data)
        return result
    except Exception as e:
        logger.exception("Error creating instance record")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/instance-records", 
    summary="List Instance Records",
    response_model=List[Dict[str, Any]],
    responses={500: {"model": ErrorResponse}}
)
async def list_instance_records(
    user_id: Optional[str] = None,
    instance_manager: InstanceManager = Depends(get_instance_manager)
):
    """
    List all instance records, optionally filtered by user ID.
    """
    try:
        return await instance_manager.list_instances(user_id)
    except Exception as e:
        logger.exception("Error listing instance records")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/instance-records/{instance_id}", 
    summary="Get Instance Record",
    response_model=Dict[str, Any],
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_instance_record(
    instance_id: str,
    instance_manager: InstanceManager = Depends(get_instance_manager)
):
    """
    Get an instance record by ID.
    """
    try:
        result = await instance_manager.get_instance(instance_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Instance record with ID {instance_id} not found")
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Error getting instance record {instance_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch(
    "/instance-records/{instance_id}", 
    summary="Update Instance Record",
    response_model=Dict[str, Any],
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def update_instance_record(
    instance_id: str,
    update_data: Dict[str, Any],
    instance_manager: InstanceManager = Depends(get_instance_manager)
):
    """
    Update an instance record.
    """
    try:
        # First check if the instance exists
        existing = await instance_manager.get_instance(instance_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Instance record with ID {instance_id} not found")
        
        # Update the instance
        result = await instance_manager.update_instance(instance_id, update_data)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Error updating instance record {instance_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete(
    "/instance-records/{instance_id}", 
    summary="Delete Instance Record",
    response_model=Dict[str, str],
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def delete_instance_record(
    instance_id: str,
    instance_manager: InstanceManager = Depends(get_instance_manager)
):
    """
    Delete an instance record.
    """
    try:
        # First check if the instance exists
        existing = await instance_manager.get_instance(instance_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Instance record with ID {instance_id} not found")
        
        # Delete the instance
        success = await instance_manager.delete_instance(instance_id)
        if success:
            return {"message": f"Instance record {instance_id} deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to delete instance record {instance_id}")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Error deleting instance record {instance_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/schedule/instances", 
    summary="Schedule Instance Creation",
    response_model=Dict[str, str],
    responses={500: {"model": ErrorResponse}}
)
async def schedule_instance_creation(
    schedule_data: ScheduleInstanceCreate,
    scheduler: JobScheduler = Depends(get_scheduler)
):
    """
    Schedule an instance to be created at a specific time.
    
    This endpoint schedules a job to create a GPU instance at the specified time.
    The instance parameters should be the same as those used for the /instances endpoint.
    """
    try:
        job_id = scheduler.schedule_instance_creation(
            schedule_data.instance_params,
            schedule_data.schedule_time
        )
        
        # Store the scheduled job in the database
        try:
            instance_manager = get_instance_manager()
            await instance_manager.create_instance({
                "scheduled_job_id": job_id,
                "scheduled_time": schedule_data.schedule_time.isoformat(),
                "status": "scheduled",
                "details": schedule_data.instance_params,
                "provider": "vast.ai"
            })
        except Exception as db_error:
            logger.error(f"Failed to store scheduled job in database: {str(db_error)}")
        
        return {"job_id": job_id, "message": f"Instance creation scheduled for {schedule_data.schedule_time}"}
    except Exception as e:
        logger.exception("Error scheduling instance creation")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/schedule/shutdown/{instance_id}", 
    summary="Schedule Instance Shutdown",
    response_model=Dict[str, str],
    responses={500: {"model": ErrorResponse}}
)
async def schedule_instance_shutdown(
    instance_id: str,
    schedule_data: ScheduleInstanceShutdown,
    scheduler: JobScheduler = Depends(get_scheduler)
):
    """
    Schedule an instance to be shut down at a specific time.
    
    This endpoint schedules a job to shut down a GPU instance at the specified time.
    """
    try:
        job_id = scheduler.schedule_instance_shutdown(
            instance_id,
            schedule_data.schedule_time
        )
        
        # Update the instance record in the database
        try:
            instance_manager = get_instance_manager()
            await instance_manager.update_instance(
                instance_id,
                {
                    "shutdown_job_id": job_id,
                    "scheduled_shutdown_time": schedule_data.schedule_time.isoformat()
                }
            )
        except Exception as db_error:
            logger.error(f"Failed to update instance with shutdown schedule: {str(db_error)}")
        
        return {"job_id": job_id, "message": f"Instance shutdown scheduled for {schedule_data.schedule_time}"}
    except Exception as e:
        logger.exception("Error scheduling instance shutdown")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/schedule/jobs", 
    summary="List Scheduled Jobs",
    response_model=Dict[str, Dict[str, Any]],
    responses={500: {"model": ErrorResponse}}
)
async def list_scheduled_jobs(
    scheduler: JobScheduler = Depends(get_scheduler)
):
    """
    List all scheduled jobs.
    """
    try:
        return scheduler.get_jobs()
    except Exception as e:
        logger.exception("Error listing scheduled jobs")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete(
    "/schedule/jobs/{job_id}", 
    summary="Delete Scheduled Job",
    response_model=Dict[str, str],
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def delete_scheduled_job(
    job_id: str,
    scheduler: JobScheduler = Depends(get_scheduler)
):
    """
    Delete a scheduled job.
    """
    try:
        success = scheduler.remove_job(job_id)
        if success:
            return {"message": f"Job {job_id} removed successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("Error deleting scheduled job")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/test/supabase", 
    summary="Test Supabase Connection",
    response_model=Dict[str, str],
    responses={500: {"model": ErrorResponse}}
)
async def test_supabase_connection(
    client = Depends(get_supabase_client)
):
    """
    Test the connection to Supabase.
    """
    try:
        # Try to see if we can connect (this will throw an error if connection fails)
        try:
            # First try instances table if it exists
            result = client.table("instances").select("count").limit(1).execute()
            table_status = "instances table exists"
        except Exception as table_error:
            # Table might not exist yet, but connection works
            table_status = f"Note: {str(table_error)}"
            
        return {
            "status": "connected", 
            "message": "Successfully connected to Supabase", 
            "table_status": table_status
        }
    except Exception as e:
        logger.exception("Error connecting to Supabase")
        raise HTTPException(status_code=500, detail=f"Supabase connection error: {str(e)}")

@router.post(
    "/admin/init", 
    summary="Initialize Application",
    response_model=Dict[str, Any],
    responses={500: {"model": ErrorResponse}}
)
async def init_application(
    supabase_client = Depends(get_supabase_client),
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """
    Initialize the application, creating database tables and default templates.
    
    WARNING: This endpoint should be called once during setup.
    It will attempt to verify database connection and create default templates.
    
    To execute the SQL script to create tables, please use the Supabase SQL Editor
    with the script in the database/setup.sql file.
    """
    try:
        results = {
            "database_connection": "verified",
            "default_templates": []
        }
        
        # Test database connection
        try:
            # First try instances table if it exists
            db_result = supabase_client.table("instances").select("count").limit(1).execute()
            results["instances_table"] = "exists"
        except Exception as table_error:
            # Table might not exist yet
            results["instances_table"] = f"not found: {str(table_error)}"
            
        try:
            # Check templates table
            db_result = supabase_client.table("instance_templates").select("count").limit(1).execute()
            results["templates_table"] = "exists"
        except Exception as table_error:
            # Table might not exist yet
            results["templates_table"] = f"not found: {str(table_error)}"
            
        # Create default templates
        created_templates = await template_manager.create_default_templates()
        if created_templates:
            results["default_templates"] = [
                {"id": t.get("id"), "name": t.get("name")} 
                for t in created_templates
            ]
            results["templates_created"] = len(created_templates)
        else:
            results["templates_created"] = 0
            
        # Add instructions for SQL setup
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                  "database", "setup.sql")
        
        if os.path.exists(script_path):
            results["sql_script_path"] = script_path
            results["sql_instructions"] = "Please run this script in the Supabase SQL Editor to set up database tables"
        else:
            results["sql_script_found"] = False
            
        return results
    except Exception as e:
        logger.exception("Error initializing application")
        raise HTTPException(status_code=500, detail=f"Initialization error: {str(e)}")

@router.get(
    "/admin/api-logs", 
    summary="List API Logs",
    response_model=List[Dict[str, Any]],
    responses={500: {"model": ErrorResponse}}
)
async def list_api_logs(
    endpoint: Optional[str] = None,
    status: Optional[str] = None,
    vast_id: Optional[str] = None,
    instance_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    supabase_client = Depends(get_supabase_client)
):
    """
    List API logs with optional filtering.
    
    This endpoint allows you to retrieve logs of API calls with various filters:
    - endpoint: Filter by API endpoint
    - status: Filter by status (success, error)
    - vast_id: Filter by Vast.ai instance ID
    - instance_id: Filter by internal instance ID
    - limit: Maximum number of logs to return (default: 100)
    - offset: Number of logs to skip (for pagination)
    """
    try:
        query = supabase_client.table("api_logs").select("*")
        
        # Apply filters
        if endpoint:
            query = query.ilike("endpoint", f"%{endpoint}%")
        if status:
            query = query.eq("status", status)
        if vast_id:
            query = query.eq("vast_id", vast_id)
        if instance_id:
            query = query.eq("instance_id", instance_id)
        
        # Apply pagination and ordering
        query = query.order("created_at", desc=True).limit(limit).offset(offset)
        
        # Execute the query
        result = query.execute()
        
        # Extract the data from the response
        logs = result.data if result and hasattr(result, 'data') else []
        
        return logs
    except Exception as e:
        logger.exception("Error retrieving API logs")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/admin/api-logs/{log_id}", 
    summary="Get API Log",
    response_model=Dict[str, Any],
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_api_log(
    log_id: str,
    supabase_client = Depends(get_supabase_client)
):
    """
    Get a specific API log by ID.
    """
    try:
        result = supabase_client.table("api_logs").select("*").eq("id", log_id).execute()
        
        # Extract the data from the response
        logs = result.data if result and hasattr(result, 'data') else []
        
        if not logs:
            raise HTTPException(status_code=404, detail=f"Log with ID {log_id} not found")
        
        return logs[0]
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Error retrieving API log {log_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/admin/api-logs/instance/{instance_id}", 
    summary="Get API Logs for Instance",
    response_model=List[Dict[str, Any]],
    responses={500: {"model": ErrorResponse}}
)
async def get_instance_api_logs(
    instance_id: str,
    limit: int = Query(100, ge=1, le=1000),
    supabase_client = Depends(get_supabase_client)
):
    """
    Get all API logs related to a specific instance.
    """
    try:
        # Check if this is a Vast.ai ID or internal instance ID
        is_uuid = False
        try:
            uuid.UUID(instance_id)
            is_uuid = True
        except ValueError:
            pass
            
        # Query based on ID type
        if is_uuid:
            query = supabase_client.table("api_logs").select("*").eq("instance_id", instance_id)
        else:
            query = supabase_client.table("api_logs").select("*").eq("vast_id", instance_id)
            
        # Apply limit and ordering
        query = query.order("created_at", desc=True).limit(limit)
        
        # Execute the query
        result = query.execute()
        
        # Extract the data from the response
        logs = result.data if result and hasattr(result, 'data') else []
        
        return logs
    except Exception as e:
        logger.exception(f"Error retrieving API logs for instance {instance_id}")
        raise HTTPException(status_code=500, detail=str(e))

# Template management endpoints
@router.post(
    "/templates", 
    summary="Create Instance Template",
    response_model=Dict[str, Any],
    responses={500: {"model": ErrorResponse}}
)
async def create_template(
    template: InstanceTemplateCreate,
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """
    Create a new instance template.
    
    Templates define reusable configurations for launching instances, including
    Docker image, environment parameters, disk size, and more.
    """
    try:
        # Convert the template model to a dictionary
        template_data = template.model_dump()
        
        # Create the template
        result = await template_manager.create_template(template_data)
        return result
    except Exception as e:
        logger.exception("Error creating template")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/templates", 
    summary="List Instance Templates",
    response_model=List[Dict[str, Any]],
    responses={500: {"model": ErrorResponse}}
)
async def list_templates(
    user_id: Optional[str] = None,
    include_public: bool = Query(True, description="Include public templates"),
    template_type: Optional[str] = Query(None, description="Filter by template type"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """
    List all instance templates, with optional filtering.
    """
    try:
        return await template_manager.list_templates(
            user_id=user_id,
            include_public=include_public,
            template_type=template_type,
            tags=tags
        )
    except Exception as e:
        logger.exception("Error listing templates")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/templates/dropdown", 
    summary="List Templates for Dropdown",
    response_model=List[Dict[str, Any]],
    responses={500: {"model": ErrorResponse}}
)
async def list_templates_for_dropdown(
    include_private: bool = Query(False, description="Include private templates"),
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """
    Get a simplified list of templates suitable for dropdown selection.
    Returns only public templates by default.
    """
    try:
        # Get templates using list_templates
        templates = await template_manager.list_templates(include_public=True)
        
        # Format for dropdown
        dropdown_templates = []
        for template in templates:
            # Only include public templates unless specifically requested
            if template.get("is_public") or include_private:
                template_info = {
                    "id": template.get("id"),
                    "name": template.get("name"),
                    "description": template.get("description"),
                    "image": template.get("image"),
                    "disk_size": template.get("disk_size", 50),
                    "tags": template.get("tags", []),
                    "env_params": template.get("env_params"),
                    "onstart_cmd": template.get("onstart_cmd"),
                    "use_ssh": template.get("use_ssh", True),
                    "use_direct": template.get("use_direct", True),
                    "other_params": template.get("other_params", {})
                }
                dropdown_templates.append(template_info)
        
        return dropdown_templates
    except Exception as e:
        logger.exception("Error listing templates for dropdown")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/templates/{template_id}", 
    summary="Get Instance Template",
    response_model=Dict[str, Any],
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_template(
    template_id: str,
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """
    Get an instance template by ID.
    """
    try:
        result = await template_manager.get_template(template_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Template with ID {template_id} not found")
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Error getting template {template_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch(
    "/templates/{template_id}", 
    summary="Update Instance Template",
    response_model=Dict[str, Any],
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def update_template(
    template_id: str,
    template: InstanceTemplateUpdate,
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """
    Update an instance template.
    """
    try:
        # Check if the template exists
        existing = await template_manager.get_template(template_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Template with ID {template_id} not found")
        
        # Convert the template model to a dictionary, excluding None values
        update_data = {k: v for k, v in template.model_dump().items() if v is not None}
        
        # Update the template
        result = await template_manager.update_template(template_id, update_data)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Error updating template {template_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete(
    "/templates/{template_id}", 
    summary="Delete Instance Template",
    response_model=Dict[str, str],
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def delete_template(
    template_id: str,
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """
    Delete an instance template.
    """
    try:
        # Check if the template exists
        existing = await template_manager.get_template(template_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Template with ID {template_id} not found")
        
        # Delete the template
        success = await template_manager.delete_template(template_id)
        if success:
            return {"message": f"Template {template_id} deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to delete template {template_id}")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Error deleting template {template_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/instances/from-template/{template_id}", 
    summary="Create Instance from Template",
    response_model=Dict[str, Any],
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def create_instance_from_template(
    request: Request,
    template_id: str,
    offer_id: str = Query(..., description="ID of the Vast.ai offer to use"),
    override_params: Optional[Dict[str, Any]] = None,
    client: VastClient = Depends(get_vast_client),
    template_manager: TemplateManager = Depends(get_template_manager),
    instance_manager: InstanceManager = Depends(get_instance_manager),
    supabase_client = Depends(get_supabase_client)
):
    """
    Create a new GPU instance using a template.
    
    This endpoint uses a saved template to create an instance with predefined
    parameters, but allows overriding specific values.
    
    Required:
    - template_id: ID of the template to use
    - offer_id: ID of the Vast.ai offer to use for the instance
    
    Optional:
    - override_params: Dictionary of parameters to override from the template
    """
    # Record start time for calculating duration
    start_time = time.time()
    
    # Store request payload for logging
    request_payload = {
        "template_id": template_id,
        "offer_id": offer_id,
        "override_params": override_params
    }
    response_payload = None
    status = "success"
    status_code = 200
    error_message = None
    vast_id = None
    instance_db_id = None
    
    try:
        # Get the template
        template = await template_manager.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template with ID {template_id} not found")
        
        # Prepare instance parameters from the template
        instance_params = {
            "id": offer_id,
            "image": template["image"],
            "disk": template["disk_size"]
        }
        
        # Add environment parameters if available
        if template["env_params"]:
            instance_params["env"] = template["env_params"]
            
        # Add onstart command if available
        if template["onstart_cmd"]:
            instance_params["onstart_cmd"] = template["onstart_cmd"]
            
        # Add SSH and direct options
        if template["use_ssh"]:
            instance_params["ssh"] = True
            
        if template["use_direct"]:
            instance_params["direct"] = True
            
        # Add other parameters if available
        if template["other_params"]:
            for key, value in template["other_params"].items():
                instance_params[key] = value
                
        # Override parameters if specified
        if override_params:
            instance_params.update(override_params)
        
        # Create the instance on Vast.ai
        vast_response = client.create_instance(**instance_params)
        
        # Store the response for logging
        response_payload = vast_response
        vast_id = vast_response.get("new_contract")
        
        # Store the instance data in Supabase
        try:
            # Extract relevant information from the Vast.ai response
            db_instance_data = {
                "vast_id": vast_id,
                "offer_id": offer_id,
                "label": template["name"],  # Use template name as label
                "image": template["image"],
                "disk_size": instance_params.get("disk", template["disk_size"]),
                "status": "creating",
                "provider": "vast.ai",
                "details": vast_response
            }
            
            # Add user_id if authentication is implemented
            # db_instance_data["user_id"] = user.id
            
            # Store in database
            db_result = await instance_manager.create_instance(db_instance_data)
            if db_result and "id" in db_result:
                instance_db_id = db_result["id"]
            
            logger.info(f"Stored instance {vast_id} in database")
        except Exception as db_error:
            # Log the error but don't fail the request
            logger.error(f"Failed to store instance in database: {str(db_error)}")
        
        return vast_response
    except HTTPException as e:
        # Update status for logging
        status = "error"
        status_code = e.status_code
        error_message = str(e.detail)
        # Re-raise existing HTTP exceptions
        raise e
    except requests.exceptions.HTTPError as e:
        # Update status for logging
        status = "error"
        status_code = e.response.status_code if hasattr(e, 'response') and hasattr(e.response, 'status_code') else 500
        
        # Handle different HTTP errors from the Vast.ai API
        if e.response.status_code == 404:
            error_message = f"GPU offer with ID {offer_id} not found or no longer available"
            logger.warning(f"Offer ID {offer_id} not found on Vast.ai")
            raise HTTPException(
                status_code=404, 
                detail=f"GPU offer with ID {offer_id} not found or no longer available. Please select another GPU offer."
            )
        elif e.response.status_code == 400:
            # Try to extract the error message from the response
            try:
                error_json = e.response.json()
                error_msg = error_json.get("msg", str(e))
                error_type = error_json.get("error", "bad_request")
                error_message = f"{error_type}: {error_msg}"
                detail = error_message
            except ValueError:
                detail = str(e)
                error_message = str(e)
            
            logger.warning(f"Bad request error creating instance: {detail}")
            raise HTTPException(status_code=400, detail=detail)
        else:
            # For other HTTP errors
            error_message = str(e)
            logger.exception(f"HTTP error creating instance: {error_message}")
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        # Update status for logging
        status = "error"
        status_code = 500
        error_message = str(e)
        logger.exception("Error creating instance from template")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Calculate request duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Get client IP address
        client_ip = request.client.host if request and hasattr(request, 'client') else None
        
        # Log the API call
        await log_api_call(
            client=supabase_client,
            endpoint=f"/instances/from-template/{template_id}",
            method="POST",
            request_payload=request_payload,
            response_payload=response_payload,
            status=status,
            status_code=status_code,
            error_message=error_message,
            vast_id=vast_id,
            instance_id=instance_db_id,
            ip_address=client_ip,
            duration_ms=duration_ms
        ) 