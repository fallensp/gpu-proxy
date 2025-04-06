"""
API endpoints for managing pod schedules.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any

from src.core.auth import get_current_user
from src.core.schedule_manager import get_schedule_manager
from src.models.schedule import (
    ScheduleCreate,
    ScheduleResponse,
    ScheduleList,
    ScheduleUpdate,
    ScheduleToggle
)

router = APIRouter(tags=["schedules"])
logger = logging.getLogger(__name__)

@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule: ScheduleCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new schedule for a pod deployment.
    """
    try:
        # Add user ID to schedule data
        schedule_data = schedule.dict()
        schedule_data["user_id"] = current_user.get("id")
        
        # Create the schedule
        schedule_manager = get_schedule_manager()
        result = await schedule_manager.create_schedule(schedule_data)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create schedule"
            )
        
        return result
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Error creating schedule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating schedule: {str(e)}"
        )

@router.get("/", response_model=ScheduleList)
async def list_schedules(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List all schedules for the current user.
    """
    try:
        schedule_manager = get_schedule_manager()
        schedules = await schedule_manager.list_schedules(current_user.get("id"))
        
        return {"schedules": schedules}
    except Exception as e:
        logger.exception(f"Error listing schedules: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing schedules: {str(e)}"
        )

@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a specific schedule by ID.
    """
    try:
        schedule_manager = get_schedule_manager()
        schedule = await schedule_manager.get_schedule(schedule_id)
        
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
            )
        
        # Ensure the user can only access their own schedules
        if schedule.get("user_id") != current_user.get("id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this schedule"
            )
        
        return schedule
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting schedule {schedule_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting schedule: {str(e)}"
        )

@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    schedule_update: ScheduleUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update an existing schedule.
    """
    try:
        schedule_manager = get_schedule_manager()
        
        # Check if the schedule exists and belongs to the user
        existing_schedule = await schedule_manager.get_schedule(schedule_id)
        
        if not existing_schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
            )
        
        # Ensure the user can only update their own schedules
        if existing_schedule.get("user_id") != current_user.get("id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this schedule"
            )
        
        # Update the schedule
        update_data = schedule_update.dict(exclude_unset=True)
        updated_schedule = await schedule_manager.update_schedule(schedule_id, update_data)
        
        if not updated_schedule:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update schedule"
            )
        
        return updated_schedule
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating schedule {schedule_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating schedule: {str(e)}"
        )

@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a schedule.
    """
    try:
        schedule_manager = get_schedule_manager()
        
        # Check if the schedule exists and belongs to the user
        existing_schedule = await schedule_manager.get_schedule(schedule_id)
        
        if not existing_schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
            )
        
        # Ensure the user can only delete their own schedules
        if existing_schedule.get("user_id") != current_user.get("id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this schedule"
            )
        
        # Delete the schedule
        success = await schedule_manager.delete_schedule(schedule_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete schedule"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting schedule {schedule_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting schedule: {str(e)}"
        )

@router.patch("/{schedule_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule(
    schedule_id: str,
    toggle_data: ScheduleToggle,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Enable or disable a schedule.
    """
    try:
        schedule_manager = get_schedule_manager()
        
        # Check if the schedule exists and belongs to the user
        existing_schedule = await schedule_manager.get_schedule(schedule_id)
        
        if not existing_schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
            )
        
        # Ensure the user can only toggle their own schedules
        if existing_schedule.get("user_id") != current_user.get("id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to toggle this schedule"
            )
        
        # Toggle the schedule
        updated_schedule = await schedule_manager.toggle_schedule(schedule_id, toggle_data.is_active)
        
        if not updated_schedule:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to toggle schedule"
            )
        
        return updated_schedule
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error toggling schedule {schedule_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error toggling schedule: {str(e)}"
        ) 