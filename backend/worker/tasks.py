"""
Celery tasks for document processing.
"""

import logging
from typing import Dict, Any
from uuid import UUID
import asyncio

from celery import current_task
from celery.exceptions import Retry

from worker.celery_app import celery_app
from services.document_processor import DocumentProcessingService
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document(self, document_id: str, org_id: str) -> Dict[str, Any]:
    """
    Celery task to process a document through the AI pipeline.
    
    Args:
        document_id: UUID string of the document to process
        org_id: Organization ID for multi-tenant access
        
    Returns:
        Processing result dictionary
    """
    try:
        logger.info(f"Starting document processing task for {document_id}")
        
        # Update task state
        self.update_state(
            state="PROCESSING",
            meta={
                "document_id": document_id,
                "org_id": org_id,
                "stage": "initializing"
            }
        )
        
        # Create service and process document
        processor = DocumentProcessingService()
        
        # Run async processing in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                processor.process_document(UUID(document_id), org_id)
            )
        finally:
            loop.close()
        
        if result["status"] == "failed":
            logger.error(f"Document processing failed: {result.get('error')}")
            # Don't retry if processing logically failed
            return result
        
        logger.info(f"Document processing completed successfully for {document_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Document processing task failed: {exc}")
        
        # Retry on transient errors
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying document processing (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)
        
        # Max retries reached
        return {
            "status": "failed",
            "document_id": document_id,
            "error": f"Max retries exceeded: {str(exc)}"
        }


@celery_app.task(bind=True)
def cleanup_failed_processing(self, max_age_hours: int = 24) -> Dict[str, Any]:
    """
    Cleanup task to handle documents stuck in processing state.
    
    Args:
        max_age_hours: Maximum age in hours for stuck documents
        
    Returns:
        Cleanup result dictionary
    """
    try:
        logger.info(f"Starting cleanup of documents stuck in processing for {max_age_hours} hours")
        
        # This would need to be implemented with proper database access
        # For now, return a placeholder
        return {
            "status": "completed",
            "cleaned_up": 0,
            "max_age_hours": max_age_hours
        }
        
    except Exception as exc:
        logger.error(f"Cleanup task failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc)
        }


@celery_app.task
def health_check() -> Dict[str, Any]:
    """Health check task for monitoring worker status."""
    return {
        "status": "healthy",
        "worker_id": current_task.request.id if current_task else None,
        "timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
    }