"""
Document management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import logging
import hashlib

from core.database import get_db
from core.config import settings
from core.rbac import (
    require_document_read,
    require_document_upload,
    require_document_delete,
    require_org_access,
    protected_route,
    Permission
)
from models.database import User, Document
from repositories.document import DocumentRepository
from services.storage import storage_service

logger = logging.getLogger(__name__)
router = APIRouter()


class DocumentResponse(BaseModel):
    id: str
    title: str
    file_type: str
    file_size: int
    file_hash: str
    status: str
    uploaded_by: str
    uploader_email: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None


class DocumentUploadResponse(BaseModel):
    document_id: str
    s3_key: str
    upload_url: str
    status: str
    file_hash: str
    message: str


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    per_page: int


class UploadStatusResponse(BaseModel):
    document_id: str
    status: str
    progress: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None


@router.post("/upload", response_model=DocumentUploadResponse)
@protected_route(permissions=[Permission.DOCUMENT_UPLOAD])
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_document_upload),
    _: User = Depends(require_org_access)
):
    """Upload a document for processing"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )
        
        # Read file content to calculate hash for deduplication
        file_content = await file.read()
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Reset file pointer for storage service
        await file.seek(0)
        
        # Check for duplicate files in the organization
        doc_repo = DocumentRepository(db)
        existing_doc = await doc_repo.get_by_hash(file_hash, str(current_user.org_id))
        
        if existing_doc:
            # Return existing document info
            upload_url = storage_service.generate_presigned_url(existing_doc.s3_key)
            return DocumentUploadResponse(
                document_id=str(existing_doc.id),
                s3_key=existing_doc.s3_key,
                upload_url=upload_url,
                status=existing_doc.status,
                file_hash=existing_doc.file_hash,
                message="File already exists, returning existing document"
            )
        
        # Upload to S3
        upload_result = await storage_service.upload_document(
            file=file,
            org_id=str(current_user.org_id),
            user_id=str(current_user.id)
        )
        
        # Create document record in database
        document_data = {
            "id": UUID(upload_result.document_id),
            "org_id": current_user.org_id,
            "title": file.filename,
            "s3_key": upload_result.s3_key,
            "file_type": file.content_type,
            "file_size": len(file_content),
            "file_hash": file_hash,
            "status": "uploaded",
            "uploaded_by": current_user.id
        }
        
        document = await doc_repo.create(document_data, org_id=str(current_user.org_id))
        
        logger.info(f"Document uploaded successfully: {document.id} by user {current_user.id}")
        
        return DocumentUploadResponse(
            document_id=str(document.id),
            s3_key=document.s3_key,
            upload_url=upload_result.upload_url,
            status=document.status,
            file_hash=document.file_hash,
            message="Document uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


@router.get("/", response_model=DocumentListResponse)
@protected_route(permissions=[Permission.DOCUMENT_READ])
async def list_documents(
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of documents to return"),
    status_filter: Optional[str] = Query(None, description="Filter by document status"),
    search: Optional[str] = Query(None, description="Search in document titles"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_document_read),
    _: User = Depends(require_org_access)
):
    """List organization's documents with filtering and pagination"""
    try:
        doc_repo = DocumentRepository(db)
        
        if search:
            # Search by title
            documents = await doc_repo.search_by_title(search, str(current_user.org_id), limit)
            total = len(documents)
        elif status_filter:
            # Filter by status
            documents = await doc_repo.get_by_status(status_filter, str(current_user.org_id), limit)
            total = len(documents)
        else:
            # Get recent documents
            documents = await doc_repo.get_recent(str(current_user.org_id), limit)
            total = len(documents)
        
        # Convert to response format
        document_responses = []
        for doc in documents:
            # Get uploader info
            uploader_email = None
            if doc.uploader:
                uploader_email = doc.uploader.email
            
            document_responses.append(DocumentResponse(
                id=str(doc.id),
                title=doc.title,
                file_type=doc.file_type or "",
                file_size=doc.file_size or 0,
                file_hash=doc.file_hash or "",
                status=doc.status,
                uploaded_by=str(doc.uploaded_by),
                uploader_email=uploader_email,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                processed_at=doc.processed_at
            ))
        
        return DocumentListResponse(
            documents=document_responses,
            total=total,
            page=skip // limit + 1,
            per_page=limit
        )
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}"
        )


@router.get("/{document_id}", response_model=DocumentResponse)
@protected_route(permissions=[Permission.DOCUMENT_READ])
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_document_read),
    _: User = Depends(require_org_access)
):
    """Get document details"""
    try:
        doc_repo = DocumentRepository(db)
        document = await doc_repo.get(UUID(document_id), org_id=str(current_user.org_id))
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Get uploader info
        uploader_email = None
        if document.uploader:
            uploader_email = document.uploader.email
        
        return DocumentResponse(
            id=str(document.id),
            title=document.title,
            file_type=document.file_type or "",
            file_size=document.file_size or 0,
            file_hash=document.file_hash or "",
            status=document.status,
            uploaded_by=str(document.uploaded_by),
            uploader_email=uploader_email,
            created_at=document.created_at,
            updated_at=document.updated_at,
            processed_at=document.processed_at
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document: {str(e)}"
        )


@router.get("/{document_id}/status", response_model=UploadStatusResponse)
@protected_route(permissions=[Permission.DOCUMENT_READ])
async def get_upload_status(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_document_read),
    _: User = Depends(require_org_access)
):
    """Get document upload/processing status"""
    try:
        doc_repo = DocumentRepository(db)
        document = await doc_repo.get(UUID(document_id), org_id=str(current_user.org_id))
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Calculate progress based on status
        progress_map = {
            "uploaded": 25,
            "processing": 50,
            "completed": 100,
            "failed": 0
        }
        
        message_map = {
            "uploaded": "Document uploaded successfully",
            "processing": "Document is being processed",
            "completed": "Document processing completed",
            "failed": "Document processing failed"
        }
        
        return UploadStatusResponse(
            document_id=str(document.id),
            status=document.status,
            progress=progress_map.get(document.status, 0),
            message=message_map.get(document.status, "Unknown status"),
            error=None if document.status != "failed" else "Processing failed"
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting upload status for {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get upload status: {str(e)}"
        )


@router.delete("/{document_id}")
@protected_route(permissions=[Permission.DOCUMENT_DELETE])
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_document_delete),
    _: User = Depends(require_org_access)
):
    """Delete a document"""
    try:
        doc_repo = DocumentRepository(db)
        document = await doc_repo.get(UUID(document_id), org_id=str(current_user.org_id))
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Delete from S3
        s3_deleted = await storage_service.delete_document(document.s3_key)
        if not s3_deleted:
            logger.warning(f"Failed to delete S3 object {document.s3_key}")
        
        # Delete from database (this will cascade to related records)
        await doc_repo.delete(UUID(document_id), org_id=str(current_user.org_id))
        
        logger.info(f"Document deleted successfully: {document_id} by user {current_user.id}")
        
        return {"message": "Document deleted successfully"}
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


@router.get("/{document_id}/download")
@protected_route(permissions=[Permission.DOCUMENT_READ])
async def download_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_document_read),
    _: User = Depends(require_org_access)
):
    """Get download URL for a document"""
    try:
        doc_repo = DocumentRepository(db)
        document = await doc_repo.get(UUID(document_id), org_id=str(current_user.org_id))
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Generate download URL
        download_url = storage_service.get_download_url(
            document.s3_key,
            document.title,
            expiration=3600  # 1 hour
        )
        
        return {
            "download_url": download_url,
            "filename": document.title,
            "expires_in": 3600
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating download URL for {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )


@router.post("/{document_id}/process")
@protected_route(permissions=[Permission.DOCUMENT_UPLOAD])
async def process_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_document_upload),
    _: User = Depends(require_org_access)
):
    """Trigger document processing"""
    try:
        doc_repo = DocumentRepository(db)
        document = await doc_repo.get(UUID(document_id), org_id=str(current_user.org_id))
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        if document.status == "processing":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document is already being processed"
            )
        
        if document.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has already been processed"
            )
        
        # Update status to processing
        await doc_repo.update_status(UUID(document_id), "processing", str(current_user.org_id))
        
        # TODO: Queue document for processing (will be implemented in task 5)
        logger.info(f"Document queued for processing: {document_id}")
        
        return {
            "message": "Document queued for processing",
            "document_id": document_id,
            "status": "processing"
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )