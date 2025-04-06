"""
Job scheduler module for running scheduled tasks.
"""
import logging
import os
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.job import Job

from src.core.instance_manager import get_instance_manager
from src.core.vast_client import VastClient

logger = logging.getLogger(__name__)

class JobScheduler:
    """
    Scheduler for background tasks related to GPU instances.
    """
    
    _instance: Optional['JobScheduler'] = None
    
    def __new__(cls):
        """
        Singleton implementation to ensure only one scheduler instance exists.
        """
        if cls._instance is None:
            cls._instance = super(JobScheduler, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        Initialize the job scheduler.
        """
        if self._initialized:
            return
            
        # Set up the scheduler
        jobstores = {
            'default': MemoryJobStore()
        }
        
        self.scheduler = BackgroundScheduler(jobstores=jobstores)
        self._initialized = True
        logger.info("Initialized job scheduler")
    
    def start(self):
        """
        Start the scheduler.
        """
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Job scheduler started")
    
    def shutdown(self):
        """
        Shut down the scheduler.
        """
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Job scheduler shut down")
    
    def schedule_instance_creation(
        self, 
        instance_params: Dict[str, Any], 
        run_time: datetime
    ) -> str:
        """
        Schedule an instance to be created at a specific time.
        
        Args:
            instance_params: Parameters for creating the instance.
            run_time: The time to run the job.
        
        Returns:
            The ID of the scheduled job.
        """
        trigger = DateTrigger(run_date=run_time)
        job = self.scheduler.add_job(
            self._create_instance_job,
            trigger=trigger,
            args=[instance_params],
            id=f"create_instance_{datetime.now().timestamp()}",
            replace_existing=True
        )
        logger.info(f"Scheduled instance creation job {job.id} to run at {run_time}")
        return job.id
    
    def schedule_instance_shutdown(
        self, 
        instance_id: str, 
        run_time: datetime
    ) -> str:
        """
        Schedule an instance to be shut down at a specific time.
        
        Args:
            instance_id: The ID of the instance to shut down.
            run_time: The time to run the job.
        
        Returns:
            The ID of the scheduled job.
        """
        trigger = DateTrigger(run_date=run_time)
        job = self.scheduler.add_job(
            self._shutdown_instance_job,
            trigger=trigger,
            args=[instance_id],
            id=f"shutdown_instance_{instance_id}_{datetime.now().timestamp()}",
            replace_existing=True
        )
        logger.info(f"Scheduled instance shutdown job {job.id} for instance {instance_id} to run at {run_time}")
        return job.id
    
    def schedule_recurring_job(
        self, 
        job_function: Callable, 
        cron_expression: str, 
        args: list = None, 
        kwargs: dict = None,
        job_id: str = None
    ) -> str:
        """
        Schedule a recurring job using a cron expression.
        
        Args:
            job_function: The function to run.
            cron_expression: A cron expression (e.g., "0 0 * * *" for daily at midnight).
            args: Arguments to pass to the job function.
            kwargs: Keyword arguments to pass to the job function.
            job_id: Optional ID for the job.
        
        Returns:
            The ID of the scheduled job.
        """
        args = args or []
        kwargs = kwargs or {}
        job_id = job_id or f"recurring_job_{datetime.now().timestamp()}"
        
        trigger = CronTrigger.from_crontab(cron_expression)
        job = self.scheduler.add_job(
            job_function,
            trigger=trigger,
            args=args,
            kwargs=kwargs,
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Scheduled recurring job {job.id} with cron expression {cron_expression}")
        return job.id
    
    def remove_job(self, job_id: str) -> bool:
        """
        Remove a scheduled job.
        
        Args:
            job_id: The ID of the job to remove.
        
        Returns:
            True if the job was removed, False otherwise.
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {str(e)}")
            return False
    
    def get_jobs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all scheduled jobs.
        
        Returns:
            A dictionary of job IDs to job details.
        """
        jobs = {}
        for job in self.scheduler.get_jobs():
            jobs[job.id] = {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
        return jobs
    
    async def _create_instance_job(self, instance_params: Dict[str, Any]):
        """
        Job to create an instance.
        
        Args:
            instance_params: Parameters for creating the instance.
        """
        try:
            logger.info(f"Running scheduled instance creation job with params: {instance_params}")
            
            # Create a new VastClient
            client = VastClient()
            
            # Create the instance
            response = client.create_instance(**instance_params)
            
            # Get instance manager
            instance_manager = get_instance_manager()
            
            # Store the result in the database
            db_instance_data = {
                "vast_id": response.get("new_contract"),
                "offer_id": instance_params.get("id"),
                "label": instance_params.get("label"),
                "image": instance_params.get("image"),
                "disk_size": instance_params.get("disk"),
                "status": "creating",
                "provider": "vast.ai",
                "details": response,
                "scheduled": True
            }
            
            await instance_manager.create_instance(db_instance_data)
            
            logger.info(f"Successfully created scheduled instance: {response.get('new_contract')}")
        except Exception as e:
            logger.exception(f"Error in scheduled instance creation job: {str(e)}")
    
    async def _shutdown_instance_job(self, instance_id: str):
        """
        Job to shut down an instance.
        
        Args:
            instance_id: The ID of the instance to shut down.
        """
        try:
            logger.info(f"Running scheduled instance shutdown job for instance {instance_id}")
            
            # Create a new VastClient
            client = VastClient()
            
            # Stop the instance
            response = client.stop_instance(instance_id)
            
            # Get instance manager
            instance_manager = get_instance_manager()
            
            # Update the status in the database
            await instance_manager.update_instance(
                instance_id, 
                {"status": "stopped", "shutdown_time": datetime.utcnow().isoformat()}
            )
            
            logger.info(f"Successfully shut down scheduled instance: {instance_id}")
        except Exception as e:
            logger.exception(f"Error in scheduled instance shutdown job: {str(e)}")

# Global instance
scheduler = JobScheduler()

def get_scheduler() -> JobScheduler:
    """
    Get the job scheduler.
    
    Returns:
        The job scheduler instance.
    """
    return scheduler 