"""
Models for pod scheduling functionality.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class ScheduleBase(BaseModel):
    """Base model for schedule data."""
    name: str = Field(..., description="Name of the schedule")
    gpu_type: str = Field(..., description="Type of GPU to schedule")
    min_specs: Optional[Dict[str, Any]] = Field(default=None, description="Minimum specifications for the GPU")
    num_gpus: Optional[int] = Field(default=1, description="Number of GPUs to provision")
    disk_size: Optional[int] = Field(default=50, description="Disk size in GB")
    docker_image: Optional[str] = Field(default=None, description="Docker image to use")
    env_params: Optional[Dict[str, str]] = Field(default=None, description="Environment parameters")
    onstart_cmd: Optional[str] = Field(default=None, description="Command to run on startup")
    use_ssh: Optional[bool] = Field(default=True, description="Enable SSH access")
    use_direct: Optional[bool] = Field(default=False, description="Enable direct access")
    template_id: Optional[str] = Field(default=None, description="Template ID to use for the instance")
    start_schedule: str = Field(..., description="Cron expression for when to start the instance")
    stop_schedule: str = Field(..., description="Cron expression for when to stop the instance")
    timezone: str = Field(default="UTC", description="Timezone for the schedule")
    max_price_per_hour: Optional[float] = Field(default=None, description="Maximum price per hour to pay for the GPU")

class ScheduleCreate(ScheduleBase):
    """Model for creating a new schedule."""
    pass

class ScheduleUpdate(BaseModel):
    """Model for updating an existing schedule."""
    name: Optional[str] = None
    gpu_type: Optional[str] = None
    min_specs: Optional[Dict[str, Any]] = None
    num_gpus: Optional[int] = None
    disk_size: Optional[int] = None
    docker_image: Optional[str] = None
    env_params: Optional[Dict[str, str]] = None
    onstart_cmd: Optional[str] = None
    use_ssh: Optional[bool] = None
    use_direct: Optional[bool] = None
    template_id: Optional[str] = None
    start_schedule: Optional[str] = None
    stop_schedule: Optional[str] = None
    timezone: Optional[str] = None
    max_price_per_hour: Optional[float] = None
    is_active: Optional[bool] = None

class ScheduleToggle(BaseModel):
    """Model for toggling a schedule's active status."""
    is_active: bool = Field(..., description="Whether the schedule should be active")
    
class ScheduleResponse(ScheduleBase):
    """Model for schedule response data."""
    id: str = Field(..., description="Schedule ID")
    user_id: str = Field(..., description="User ID")
    is_active: bool = Field(default=True, description="Whether the schedule is active")
    last_instance_id: Optional[str] = Field(default=None, description="ID of the last created instance")
    last_run_time: Optional[datetime] = Field(default=None, description="When the schedule last ran")
    created_at: datetime = Field(..., description="When the schedule was created")
    updated_at: datetime = Field(..., description="When the schedule was last updated")
    
    class Config:
        """Pydantic model configuration."""
        from_attributes = True

class ScheduleList(BaseModel):
    """Model for a list of schedules."""
    schedules: List[ScheduleResponse] = Field(default_factory=list, description="List of schedules") 