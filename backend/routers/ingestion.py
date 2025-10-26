"""
Document ingestion API endpoints.
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_async_session
from core.auth_dependencies import require_role
from models.database import User, DocumentStatus
from repositories.document import DocumentRepository
from services.job_queue import JobQueueService, JobResult, create_job_queue_service
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])


class IngestDocumentRequest(BaseModel):
    """Request model for document ingestion."""
    priority: Optional[str] = "normal"  # "high", "normal", "low"


class IngestDocumentResponse(BaseModel):
    """Response model for document ingestion."""
    job_id: str
    document_id: str
    status: str
    message: str


class ProcessingStatusResponse(BaseModel):
    """Response model for processing status."""
    job_id: str
    status: str
    document_id: str
    org_id: str
    created_at: str
    updated_at: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0


class QueueStatsResponse(BaseModel):
    """Response model for queue statistics."""
    active_tasks: int
    scheduled_tasks: int
    reserved_tasks: int
    workers: list
    timestamp: str


@router.post("/{document_id}", response_model=IngestDocumentResponse)
async def ingest_document(
    document_id: UUID,
    request: IngestDocumentRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
    job_queue: JobQueueService = Depends(create_job_queue_service)
):
    """
    Submit a document for processing through the AI pipeline.
    
    This endpoint:
    1. Validates the document exists and belongs to the user's organization
    2. Checks the document is in a valid state for processing
    3. Submits the document to the processing queue
    4. Returns a job ID for tracking progress
    """
    try:
        logger.info(f"Ingestion request for document {document_id} by user {current_user.id}")
        
        # Get document repository
        doc_repo = DocumentRepository(session)
        
        # Verify document exists and user has access
        document = await doc_repo.get_by_id(document_id, str(current_user.org_id))
        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found or access denied"
            )
        
        # Check document status
        if document.status == DocumentStatus.PROCESSING:
            raise HTTPException(
                status_code=409,
                detail="Document is already being processed"
            )
        
        if document.status == DocumentStatus.COMPLETED:
            # Allow reprocessing of completed documents
            logger.info(f"Reprocessing completed document {document_id}")
        
        # Update document status to processing
        await doc_repo.update(
            document_id,
            org_id=str(current_user.org_id),
            status=DocumentStatus.PROCESSING
        )
        await session.commit()
        
        # Submit to processing queue
        job_id = await job_queue.submit_document_processing(
            document_id=document_id,
            org_id=str(current_user.org_id),
            priority=request.priority
        )
        
        logger.info(f"Document {document_id} submitted for processing with job ID {job_id}")
        
        return IngestDocumentResponse(
            job_id=job_id,
            document_id=str(document_id),
            status="submitted",
            message="Document submitted for processing"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit document for ingestion: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to submit document for processing"
        )


@router.get("/status/{job_id}", response_model=ProcessingStatusResponse)
async def get_processing_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    job_queue: JobQueueService = Depends(create_job_queue_service)
):
    """
    Get the processing status of a document ingestion job.
    
    Returns current status, progress information, and results if completed.
    """
    try:
        logger.info(f"Status request for job {job_id} by user {current_user.id}")
        
        # Get job status
        job_result = await job_queue.get_job_status(job_id)
        
        # Verify user has access to this job (basic check by org_id if available)
        if job_result.org_id and job_result.org_id != str(current_user.org_id):
            raise HTTPException(
                status_code=404,
                detail="Job not found or access denied"
            )
        
        return ProcessingStatusResponse(
            job_id=job_result.job_id,
            status=job_result.status.value,
            document_id=job_result.document_id,
            org_id=job_result.org_id,
            created_at=job_result.created_at.isoformat(),
            updated_at=job_result.updated_at.isoformat(),
            result=job_result.result,
            error=job_result.error,
            retry_count=job_result.retry_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve job status"
        )


@router.delete("/cancel/{job_id}")
async def cancel_processing(
    job_id: str,
    current_user: User = Depends(get_current_user),
    job_queue: JobQueueService = Depends(create_job_queue_service)
):
    """
    Cancel a document processing job.
    
    Note: This may not immediately stop processing if the job is already running.
    """
    try:
        logger.info(f"Cancel request for job {job_id} by user {current_user.id}")
        
        # Get job status first to verify access
        job_result = await job_queue.get_job_status(job_id)
        
        if job_result.org_id and job_result.org_id != str(current_user.org_id):
            raise HTTPException(
                status_code=404,
                detail="Job not found or access denied"
            )
        
        # Cancel the job
        success = await job_queue.cancel_job(job_id)
        
        if success:
            return {"message": "Job cancellation requested", "job_id": job_id}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to cancel job"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to cancel job"
        )


@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_stats(
    current_user: User = Depends(require_role("admin")),
    job_queue: JobQueueService = Depends(create_job_queue_service)
):
    """
    Get processing queue statistics.
    
    Admin only endpoint for monitoring queue health and performance.
    """
    try:
        logger.info(f"Queue stats request by admin user {current_user.id}")
        
        stats = await job_queue.get_queue_stats()
        
        return QueueStatsResponse(
            active_tasks=stats.get("active_tasks", 0),
            scheduled_tasks=stats.get("scheduled_tasks", 0),
            reserved_tasks=stats.get("reserved_tasks", 0),
            workers=stats.get("workers", []),
            timestamp=stats.get("timestamp", "")
        )
        
    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve queue statistics"
        )


@router.post("/webhook/processing-complete")
async def processing_complete_webhook(
    payload: Dict[str, Any],
    session: AsyncSession = Depends(get_async_session)
):
    """
    Webhook endpoint for processing completion notifications.
    
    This endpoint can be called by the worker to notify of processing completion.
    In production, this would be secured with a webhook secret.
    """
    try:
        logger.info(f"Processing complete webhook received: {payload}")
        
        # Extract required fields
        document_id = payload.get("document_id")
        org_id = payload.get("org_id")
        status = payload.get("status")
        
        if not all([document_id, org_id, status]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: document_id, org_id, status"
            )
        
        # Update document status
        doc_repo = DocumentRepository(session)
        
        document_status = DocumentStatus.COMPLETED if status == "completed" else DocumentStatus.FAILED
        
        await doc_repo.update(
            UUID(document_id),
            org_id=org_id,
            status=document_status
        )
        await session.commit()
        
        logger.info(f"Document {document_id} status updated to {document_status}")
        
        return {"message": "Webhook processed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process webhook"
        )


@router.get("/health")
async def ingestion_health_check():
    """Health check endpoint for the ingestion service."""
    return {
        "status": "healthy",
        "service": "document-ingestion",
        "timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
    }