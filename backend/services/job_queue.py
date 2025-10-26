"""
Job queue service for managing document processing tasks.
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError
from celery.result import AsyncResult

from worker.celery_app import celery_app
from worker.tasks import process_document
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class JobResult:
    """Container for job result information."""
    job_id: str
    status: JobStatus
    document_id: str
    org_id: str
    created_at: datetime
    updated_at: datetime
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0


class JobQueueService:
    """Service for managing document processing job queue."""
    
    def __init__(self):
        self.sqs_client = None
        if settings.SQS_QUEUE_URL and settings.AWS_ACCESS_KEY_ID:
            self.sqs_client = boto3.client(
                'sqs',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
    
    async def submit_document_processing(
        self, 
        document_id: UUID, 
        org_id: str,
        priority: str = "normal"
    ) -> str:
        """
        Submit a document for processing.
        
        Args:
            document_id: UUID of the document to process
            org_id: Organization ID
            priority: Task priority ("high", "normal", "low")
            
        Returns:
            Job ID for tracking
        """
        try:
            logger.info(f"Submitting document {document_id} for processing")
            
            # Submit task to Celery
            task_result = process_document.apply_async(
                args=[str(document_id), org_id],
                queue=self._get_queue_for_priority(priority),
                priority=self._get_priority_value(priority)
            )
            
            logger.info(f"Document processing task submitted with ID: {task_result.id}")
            return task_result.id
            
        except Exception as e:
            logger.error(f"Failed to submit document processing task: {e}")
            raise
    
    async def get_job_status(self, job_id: str) -> JobResult:
        """
        Get the status of a processing job.
        
        Args:
            job_id: Job ID returned from submit_document_processing
            
        Returns:
            JobResult with current status and details
        """
        try:
            # Get task result from Celery
            task_result = AsyncResult(job_id, app=celery_app)
            
            # Map Celery states to our JobStatus
            status_mapping = {
                "PENDING": JobStatus.PENDING,
                "PROCESSING": JobStatus.PROCESSING,
                "SUCCESS": JobStatus.COMPLETED,
                "FAILURE": JobStatus.FAILED,
                "RETRY": JobStatus.RETRY,
                "REVOKED": JobStatus.FAILED,
            }
            
            status = status_mapping.get(task_result.state, JobStatus.PENDING)
            
            # Extract metadata from task result
            result_data = None
            error_message = None
            document_id = ""
            org_id = ""
            
            if task_result.state == "SUCCESS":
                result_data = task_result.result
                if isinstance(result_data, dict):
                    document_id = result_data.get("document_id", "")
            elif task_result.state == "FAILURE":
                error_message = str(task_result.info)
            elif task_result.state == "PROCESSING":
                if hasattr(task_result, 'info') and isinstance(task_result.info, dict):
                    document_id = task_result.info.get("document_id", "")
                    org_id = task_result.info.get("org_id", "")
            
            # Create job result
            job_result = JobResult(
                job_id=job_id,
                status=status,
                document_id=document_id,
                org_id=org_id,
                created_at=datetime.utcnow(),  # Would be stored in DB in production
                updated_at=datetime.utcnow(),
                result=result_data,
                error=error_message,
                retry_count=getattr(task_result, 'retries', 0)
            )
            
            return job_result
            
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            # Return failed status if we can't get the actual status
            return JobResult(
                job_id=job_id,
                status=JobStatus.FAILED,
                document_id="",
                org_id="",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                error=f"Failed to retrieve job status: {str(e)}"
            )
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a processing job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if successfully cancelled
        """
        try:
            celery_app.control.revoke(job_id, terminate=True)
            logger.info(f"Job {job_id} cancelled successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Dictionary with queue statistics
        """
        try:
            # Get active tasks
            inspect = celery_app.control.inspect()
            active_tasks = inspect.active()
            scheduled_tasks = inspect.scheduled()
            reserved_tasks = inspect.reserved()
            
            stats = {
                "active_tasks": len(active_tasks or {}),
                "scheduled_tasks": len(scheduled_tasks or {}),
                "reserved_tasks": len(reserved_tasks or {}),
                "workers": list((active_tasks or {}).keys()),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _get_queue_for_priority(self, priority: str) -> str:
        """Get queue name based on priority."""
        if priority == "high":
            return "document_processing"
        else:
            return "document_processing"  # Same queue for now
    
    def _get_priority_value(self, priority: str) -> int:
        """Get numeric priority value."""
        priority_map = {
            "high": 9,
            "normal": 5,
            "low": 1
        }
        return priority_map.get(priority, 5)
    
    async def send_sqs_message(
        self, 
        message_body: Dict[str, Any], 
        delay_seconds: int = 0
    ) -> Optional[str]:
        """
        Send message to SQS queue (for production use).
        
        Args:
            message_body: Message payload
            delay_seconds: Delay before message becomes visible
            
        Returns:
            Message ID if successful
        """
        if not self.sqs_client or not settings.SQS_QUEUE_URL:
            logger.warning("SQS not configured, skipping message send")
            return None
        
        try:
            import json
            
            response = self.sqs_client.send_message(
                QueueUrl=settings.SQS_QUEUE_URL,
                MessageBody=json.dumps(message_body),
                DelaySeconds=delay_seconds
            )
            
            message_id = response.get('MessageId')
            logger.info(f"SQS message sent with ID: {message_id}")
            return message_id
            
        except ClientError as e:
            logger.error(f"Failed to send SQS message: {e}")
            return None


# Factory function
def create_job_queue_service() -> JobQueueService:
    """Create and return a JobQueueService instance."""
    return JobQueueService()