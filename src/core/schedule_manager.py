"""
Schedule manager for GPU pod schedules.
"""
import logging
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timezone
import croniter
import pytz
import traceback
import json

from src.core.db import get_supabase_client_async
from src.core.vast_client import VastClient

logger = logging.getLogger(__name__)

class ScheduleManager:
    """
    Manager for handling GPU pod schedules.
    """
    
    def __init__(self, db_client):
        """
        Initialize the schedule manager.
        
        Args:
            db_client: Database client
        """
        self.db_client = db_client
        self.table = "pod_schedules"
        self.vast_client = VastClient()
    
    async def create_schedule(self, schedule_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new schedule for a pod.
        
        Args:
            schedule_data: Schedule data
            
        Returns:
            Created schedule or None if creation failed
        """
        logger.info(f"[SCHEDULE_DEBUG] Starting schedule creation with data: {json.dumps(schedule_data, default=str)}")
        
        try:
            # Generate a UUID for the schedule if not provided
            if "id" not in schedule_data:
                schedule_data["id"] = str(uuid.uuid4())
                logger.info(f"[SCHEDULE_DEBUG] Generated UUID for schedule: {schedule_data['id']}")
            
            # Add timestamps
            now = datetime.now().isoformat()
            schedule_data["created_at"] = now
            schedule_data["updated_at"] = now
            logger.info(f"[SCHEDULE_DEBUG] Added timestamps: created_at={now}, updated_at={now}")
            
            # Validate required fields
            required_fields = ["name", "docker_image", "start_schedule", "stop_schedule", "timezone"]
            missing_fields = [field for field in required_fields if field not in schedule_data]
            
            if missing_fields:
                logger.error(f"[SCHEDULE_DEBUG] Missing required fields: {missing_fields}")
                return None
            
            # Add default values for missing fields
            if "gpu_type" not in schedule_data or not schedule_data["gpu_type"]:
                schedule_data["gpu_type"] = "Unknown"
                logger.warning("[SCHEDULE_DEBUG] No gpu_type provided, using 'Unknown'")
            
            # Ensure specs is a JSON object (as a Python dict for insertion)
            if "min_specs" not in schedule_data or not schedule_data["min_specs"]:
                schedule_data["min_specs"] = {}
            elif isinstance(schedule_data["min_specs"], str):
                try:
                    schedule_data["min_specs"] = json.loads(schedule_data["min_specs"])
                except:
                    schedule_data["min_specs"] = {}
            
            # Ensure user_id is properly formatted or set to NULL
            if "user_id" not in schedule_data or not schedule_data["user_id"]:
                logger.warning("[SCHEDULE_DEBUG] No user_id provided, setting to NULL")
                # Set to None to store as NULL in the database, avoiding foreign key constraint
                schedule_data["user_id"] = None
            else:
                # Make sure it's a string
                schedule_data["user_id"] = str(schedule_data["user_id"])
                
                # Validate UUID format if possible
                try:
                    uuid.UUID(schedule_data["user_id"])
                except ValueError:
                    logger.warning(f"[SCHEDULE_DEBUG] Invalid UUID format for user_id: {schedule_data['user_id']}, setting to NULL")
                    schedule_data["user_id"] = None
            
            # Ensure is_active is set to a boolean
            if "is_active" not in schedule_data:
                schedule_data["is_active"] = True
            else:
                schedule_data["is_active"] = bool(schedule_data["is_active"])
            
            # Clean data for logging (make a copy to not modify the original)
            log_data = schedule_data.copy()
            for key, value in log_data.items():
                if isinstance(value, (dict, list)):
                    log_data[key] = json.dumps(value)
                
            logger.info(f"[SCHEDULE_DEBUG] Prepared schedule data for insertion: {json.dumps(log_data, default=str)}")
            logger.info(f"[SCHEDULE_DEBUG] Attempting insert into pod_schedules table")
            
            try:
                # Make a clean copy of the data for insertion
                insert_data = schedule_data.copy()
                
                # Log the exact SQL statement (approximation)
                fields = ", ".join(insert_data.keys())
                placeholders = ", ".join([f":{k}" for k in insert_data.keys()])
                logger.info(f"[SCHEDULE_DEBUG] INSERT INTO pod_schedules ({fields}) VALUES ({placeholders})")
                
                # Execute the insert
                result = await self.db_client.table("pod_schedules").insert(insert_data).execute()
                
                # Log the raw result
                logger.info(f"[SCHEDULE_DEBUG] Raw insert result: {result}")
                
                if hasattr(result, 'data') and result.data:
                    logger.info(f"[SCHEDULE_DEBUG] Schedule inserted successfully: {json.dumps(result.data, default=str)}")
                    return result.data[0] if result.data else {"id": schedule_data["id"]}
                else:
                    logger.error(f"[SCHEDULE_DEBUG] Failed to get data from insert result: {str(result)}")
                    
                    # Try a direct query to verify if the record was created despite no data returned
                    try:
                        verify_query = await self.db_client.table("pod_schedules").select("*").eq("id", schedule_data["id"]).execute()
                        if verify_query.data and len(verify_query.data) > 0:
                            logger.info(f"[SCHEDULE_DEBUG] Schedule was created but result.data was empty. Found via verification: {json.dumps(verify_query.data, default=str)}")
                            return verify_query.data[0]
                    except Exception as verify_error:
                        logger.error(f"[SCHEDULE_DEBUG] Verification query failed: {str(verify_error)}")
                    
                    return {"id": schedule_data["id"], "warning": "Insert may have succeeded but no data was returned"}
            except Exception as db_error:
                logger.error(f"[SCHEDULE_DEBUG] Database error during insert: {str(db_error)}")
                
                # Try to extract more information from the error
                if hasattr(db_error, 'response'):
                    if hasattr(db_error.response, 'text'):
                        logger.error(f"[SCHEDULE_DEBUG] Error response text: {db_error.response.text}")
                    if hasattr(db_error.response, 'status_code'):
                        logger.error(f"[SCHEDULE_DEBUG] Error status code: {db_error.response.status_code}")
                        
                logger.error(f"[SCHEDULE_DEBUG] Error traceback: {traceback.format_exc()}")
                return None
                
        except Exception as e:
            logger.error(f"[SCHEDULE_DEBUG] Error creating schedule: {str(e)}")
            logger.error(f"[SCHEDULE_DEBUG] Error traceback: {traceback.format_exc()}")
            return None
    
    async def list_schedules(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all schedules for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of schedules
        """
        try:
            result = await self.db_client.table(self.table).select("*").eq("user_id", user_id).execute()
            
            if not result.data:
                return []
                
            return result.data
        except Exception as e:
            logger.exception(f"Error listing schedules for user {user_id}: {str(e)}")
            return []
    
    async def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a schedule by ID.
        
        Args:
            schedule_id: Schedule ID
            
        Returns:
            Schedule or None if not found
        """
        try:
            result = await self.db_client.table(self.table).select("*").eq("id", schedule_id).execute()
            
            if not result.data:
                return None
                
            return result.data[0]
        except Exception as e:
            logger.exception(f"Error getting schedule {schedule_id}: {str(e)}")
            return None
    
    async def update_schedule(self, schedule_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a schedule.
        
        Args:
            schedule_id: Schedule ID
            update_data: Data to update
            
        Returns:
            Updated schedule or None if update failed
        """
        try:
            # Add updated_at timestamp
            update_data["updated_at"] = datetime.utcnow().isoformat()
            
            # Update in database
            result = await self.db_client.table(self.table).update(update_data).eq("id", schedule_id).execute()
            
            if not result.data:
                logger.error(f"Failed to update schedule {schedule_id}: No data returned from database")
                return None
                
            logger.info(f"Updated schedule {schedule_id}")
            return result.data[0]
        except Exception as e:
            logger.exception(f"Error updating schedule {schedule_id}: {str(e)}")
            return None
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule.
        
        Args:
            schedule_id: Schedule ID
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            result = await self.db_client.table(self.table).delete().eq("id", schedule_id).execute()
            
            if not result.data:
                logger.error(f"Failed to delete schedule {schedule_id}: No data returned from database")
                return False
                
            logger.info(f"Deleted schedule {schedule_id}")
            return True
        except Exception as e:
            logger.exception(f"Error deleting schedule {schedule_id}: {str(e)}")
            return False
    
    async def check_pending_actions(self) -> Dict[str, List[str]]:
        """
        Check for schedules that need to be started or stopped.
        
        Returns:
            Dict with lists of schedule IDs that were started and stopped
        """
        logger.info("Checking for pending schedule actions")
        result = {
            "started": [],
            "stopped": []
        }
        
        try:
            # Get all active schedules
            response = await self.db_client.table(self.table).select("*").eq("is_active", True).execute()
            if not response.data:
                logger.info("No active schedules found")
                return result
                
            schedules = response.data
            logger.info(f"Found {len(schedules)} active schedules to check")
            
            # Current time in UTC
            now = datetime.now(timezone.utc)
            
            for schedule in schedules:
                schedule_id = schedule.get("id")
                try:
                    # Get timezone for this schedule
                    tz_str = schedule.get("timezone", "UTC")
                    tz = pytz.timezone(tz_str)
                    
                    # Convert current time to schedule's timezone
                    local_now = now.astimezone(tz)
                    
                    # Check if we need to start the instance
                    if await self._should_start(schedule, local_now):
                        logger.info(f"Schedule {schedule_id} needs to start an instance")
                        success = await self._start_instance(schedule)
                        if success:
                            result["started"].append(schedule_id)
                    
                    # Check if we need to stop the instance
                    if await self._should_stop(schedule, local_now):
                        logger.info(f"Schedule {schedule_id} needs to stop an instance")
                        success = await self._stop_instance(schedule)
                        if success:
                            result["stopped"].append(schedule_id)
                
                except Exception as e:
                    logger.exception(f"Error processing schedule {schedule_id}: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.exception(f"Error checking pending actions: {str(e)}")
            return result
            
    async def _should_start(self, schedule: Dict[str, Any], now: datetime) -> bool:
        """
        Check if an instance should be started based on the schedule.
        
        Args:
            schedule: The schedule data
            now: Current datetime in the schedule's timezone
            
        Returns:
            True if an instance should be started, False otherwise
        """
        try:
            # Get start schedule in cron format
            start_cron = schedule.get("start_schedule")
            if not start_cron:
                return False
                
            # Check if schedule is active
            if not schedule.get("is_active", False):
                return False
                
            # Get the last time this schedule was run
            last_run = schedule.get("last_run_time")
            if last_run:
                last_run = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                # Convert to schedule's timezone
                tz_str = schedule.get("timezone", "UTC")
                tz = pytz.timezone(tz_str)
                last_run = last_run.astimezone(tz)
            
            # Check if there's already an instance running
            last_instance_id = schedule.get("last_instance_id")
            if last_instance_id:
                # Check if the instance is still running
                try:
                    instances = self.vast_client.show_instances()
                    for instance in instances:
                        if str(instance.get("id")) == str(last_instance_id):
                            if instance.get("status") == "running":
                                logger.info(f"Instance {last_instance_id} for schedule {schedule.get('id')} is already running")
                                return False
                except Exception as e:
                    logger.warning(f"Error checking instance status: {str(e)}")
            
            # Create a cron iterator
            iterator = croniter.croniter(start_cron, now)
            
            # Get the previous run time according to the cron schedule
            prev_run = iterator.get_prev(datetime)
            
            # Get the next run time
            next_run = iterator.get_next(datetime)
            
            # Calculate the time since the previous scheduled run
            minutes_since_prev = (now - prev_run).total_seconds() / 60
            
            # Check if we're within 2 minutes of the scheduled start time
            # and the last run was not within the last hour
            if minutes_since_prev <= 2:
                if not last_run or (now - last_run).total_seconds() / 3600 >= 1:
                    return True
                    
            return False
        except Exception as e:
            logger.exception(f"Error in _should_start for schedule {schedule.get('id')}: {str(e)}")
            return False
            
    async def _should_stop(self, schedule: Dict[str, Any], now: datetime) -> bool:
        """
        Check if an instance should be stopped based on the schedule.
        
        Args:
            schedule: The schedule data
            now: Current datetime in the schedule's timezone
            
        Returns:
            True if an instance should be stopped, False otherwise
        """
        try:
            # Get stop schedule in cron format
            stop_cron = schedule.get("stop_schedule")
            if not stop_cron:
                return False
                
            # Check if schedule is active
            if not schedule.get("is_active", False):
                return False
                
            # Get the last instance ID
            last_instance_id = schedule.get("last_instance_id")
            if not last_instance_id:
                # No instance to stop
                return False
                
            # Check if the instance is actually running
            try:
                instances = self.vast_client.show_instances()
                instance_running = False
                for instance in instances:
                    if str(instance.get("id")) == str(last_instance_id):
                        if instance.get("status") == "running":
                            instance_running = True
                            break
                            
                if not instance_running:
                    # No running instance to stop
                    return False
            except Exception as e:
                logger.warning(f"Error checking instance status: {str(e)}")
                # Assume instance is running if we can't check
            
            # Create a cron iterator
            iterator = croniter.croniter(stop_cron, now)
            
            # Get the previous run time according to the cron schedule
            prev_run = iterator.get_prev(datetime)
            
            # Calculate the time since the previous scheduled run
            minutes_since_prev = (now - prev_run).total_seconds() / 60
            
            # Check if we're within 2 minutes of the scheduled stop time
            if minutes_since_prev <= 2:
                return True
                
            return False
        except Exception as e:
            logger.exception(f"Error in _should_stop for schedule {schedule.get('id')}: {str(e)}")
            return False
            
    async def _start_instance(self, schedule: Dict[str, Any]) -> bool:
        """
        Start an instance based on the schedule.
        
        Args:
            schedule: The schedule data
            
        Returns:
            True if an instance was started, False otherwise
        """
        try:
            # Prepare instance creation parameters
            instance_params = {
                "image": schedule.get("docker_image"),
                "disk": schedule.get("disk_size", 50),
                "label": schedule.get("name"),
                "num_gpus": schedule.get("num_gpus", 1),
                # Add other parameters as needed
            }
            
            # Add SSH port mapping if needed
            if schedule.get("use_ssh", True):
                instance_params["docker_args"] = "-p 22:22"
            
            # TODO: Find a matching GPU offer based on schedule requirements
            # For now, we'll need to query for available offers
            search_params = {
                "gpu_name": schedule.get("gpu_type"),
                "num_gpus": schedule.get("num_gpus", 1),
                "order": "score-"  # Sort by best match
            }
            
            # Add price constraints if specified
            if schedule.get("max_price_per_hour"):
                search_params["max_price"] = float(schedule.get("max_price_per_hour"))
                
            # Search for available offers
            offers = self.vast_client.search_offers(**search_params)
            
            if not offers:
                logger.warning(f"No matching GPU offers found for schedule {schedule.get('id')}")
                return False
                
            # Use the best matching offer
            instance_params["id"] = offers[0].get("id")
            
            # Create the instance
            response = self.vast_client.create_instance(**instance_params)
            
            if not response or "new_contract" not in response:
                logger.error(f"Failed to create instance for schedule {schedule.get('id')}")
                return False
                
            # Update the schedule with the instance ID
            last_instance_id = response.get("new_contract")
            update_data = {
                "last_instance_id": str(last_instance_id),
                "last_run_time": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db_client.table(self.table).update(update_data).eq("id", schedule.get("id")).execute()
            logger.info(f"Started instance {last_instance_id} for schedule {schedule.get('id')}")
            
            return True
        except Exception as e:
            logger.exception(f"Error starting instance for schedule {schedule.get('id')}: {str(e)}")
            return False
            
    async def _stop_instance(self, schedule: Dict[str, Any]) -> bool:
        """
        Stop an instance based on the schedule.
        
        Args:
            schedule: The schedule data
            
        Returns:
            True if an instance was stopped, False otherwise
        """
        try:
            # Get the instance ID
            instance_id = schedule.get("last_instance_id")
            if not instance_id:
                logger.warning(f"No instance ID found for schedule {schedule.get('id')}")
                return False
                
            # Stop the instance
            response = self.vast_client.stop_instance(int(instance_id))
            
            if not response:
                logger.error(f"Failed to stop instance {instance_id} for schedule {schedule.get('id')}")
                return False
                
            # Update the schedule with the stop time
            update_data = {
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db_client.table(self.table).update(update_data).eq("id", schedule.get("id")).execute()
            logger.info(f"Stopped instance {instance_id} for schedule {schedule.get('id')}")
            
            return True
        except Exception as e:
            logger.exception(f"Error stopping instance for schedule {schedule.get('id')}: {str(e)}")
            return False

    async def check_table_exists(self) -> bool:
        """
        Check if the pod_schedules table exists in the database.
        
        Returns:
            True if the table exists, False otherwise
        """
        logger.info("[SCHEDULE_DEBUG] Checking if pod_schedules table exists")
        try:
            # Direct query to information_schema instead of using RPC
            query = self.db_client.from_("information_schema.tables").select("table_name") \
                .eq("table_schema", "public") \
                .eq("table_name", "pod_schedules") \
                .execute()
            
            if hasattr(query, 'data') and query.data:
                logger.info(f"[SCHEDULE_DEBUG] pod_schedules table exists: {len(query.data) > 0}")
                return len(query.data) > 0
            
            # If we can't query information_schema, try a simple query with error handling
            try:
                result = await self.db_client.table("pod_schedules").select("id").limit(1).execute()
                logger.info("[SCHEDULE_DEBUG] Table exists check succeeded")
                return True
            except Exception as simple_query_error:
                logger.error(f"[SCHEDULE_DEBUG] Table does not exist based on simple query: {str(simple_query_error)}")
                return False
        except Exception as e:
            logger.error(f"[SCHEDULE_DEBUG] Error checking if table exists: {str(e)}")
            logger.error(f"[SCHEDULE_DEBUG] Error traceback: {traceback.format_exc()}")
            return False

# Singleton instance
_schedule_manager = None

async def get_schedule_manager() -> ScheduleManager:
    """
    Get the schedule manager singleton.
    
    Returns:
        ScheduleManager instance
    """
    global _schedule_manager
    
    if _schedule_manager is None:
        db_client = await get_supabase_client_async()
        _schedule_manager = ScheduleManager(db_client)
    
    return _schedule_manager 