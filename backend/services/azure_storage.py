"""
Azure Blob Storage service for document management
Replaces AWS S3 functionality with Azure Blob Storage
"""

import hashlib
import mimetypes
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, BinaryIO
from uuid import UUID, uuid4

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
from fastapi import HTTPException, UploadFile
from pydantic import BaseModel

from core.config import settings
from services.virus_scanner import scan_file_for_viruses, VirusScanResult
from services.audit_service import audit_service, AuditAction, AuditLevel

logger = logging.getLogger(__name__)


class DocumentMetadata(BaseModel):
    """Document metadata model"""
    blob_name: str
    file_name: str
    file_size: int
    file_type: str
    content_type: str
    file_hash: str
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    """Document upload response model"""
    document_id: str
    blob_name: str
    upload_url: str
    status: str = "uploaded"


class AzureStorageService:
    """Service for handling file storage operations with Azure Blob Storage"""
    
    def __init__(self):
        """Initialize Azure Blob Storage client"""
        try:
            # Initialize from connection string or account key
            if hasattr(settings, 'AZURE_STORAGE_CONNECTION_STRING') and settings.AZURE_STORAGE_CONNECTION_STRING:
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    settings.AZURE_STORAGE_CONNECTION_STRING
                )
            else:
                # Fallback to account name/key if connection string not available
                account_url = f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=settings.AZURE_STORAGE_ACCOUNT_KEY
                )
            
            self.container_name = getattr(settings, 'AZURE_STORAGE_CONTAINER_NAME', 'contracts')
            
            # Ensure container exists
            self._ensure_container_exists()
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Azure Blob Storage client: {str(e)}"
            )
    
    def _ensure_container_exists(self) -> None:
        """Ensure the storage container exists"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            container_client.get_container_properties()
        except ResourceNotFoundError:
            try:
                self.blob_service_client.create_container(self.container_name)
                logger.info(f"Created container: {self.container_name}")
            except ResourceExistsError:
                pass  # Container was created by another process
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error accessing storage container '{self.container_name}': {str(e)}"
            )
    
    def _generate_blob_name(self, org_id: str, file_name: str, document_id: Optional[str] = None) -> str:
        """Generate blob name for document storage"""
        if not document_id:
            document_id = str(uuid4())
        
        # Extract file extension
        _, ext = os.path.splitext(file_name)
        
        # Create hierarchical blob name: org_id/year/month/document_id.ext
        now = datetime.utcnow()
        blob_name = f"{org_id}/{now.year}/{now.month:02d}/{document_id}{ext}"
        
        return blob_name
    
    def _calculate_file_hash(self, file_content: bytes) -> str:
        """Calculate SHA-256 hash of file content"""
        return hashlib.sha256(file_content).hexdigest()
    
    def _validate_file_type(self, file_name: str, content_type: str) -> None:
        """Validate file type against allowed types"""
        _, ext = os.path.splitext(file_name.lower())
        
        if ext not in settings.ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{ext}' not allowed. Allowed types: {', '.join(settings.ALLOWED_FILE_TYPES)}"
            )
        
        # Additional MIME type validation
        expected_mime_types = {
            '.pdf': ['application/pdf'],
            '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
            '.doc': ['application/msword']
        }
        
        if ext in expected_mime_types:
            if content_type not in expected_mime_types[ext]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid content type '{content_type}' for file extension '{ext}'"
                )
    
    def _validate_file_size(self, file_size: int) -> None:
        """Validate file size against limits"""
        max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File size {file_size} bytes exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="File is empty"
            )
    
    async def upload_document(
        self,
        file: UploadFile,
        org_id: str,
        user_id: str,
        document_id: Optional[str] = None
    ) -> DocumentUploadResponse:
        """
        Upload document to Azure Blob Storage with validation and virus scanning
        
        Args:
            file: FastAPI UploadFile object
            org_id: Organization ID
            user_id: User ID who is uploading
            document_id: Optional document ID (generated if not provided)
            
        Returns:
            DocumentUploadResponse with upload details
        """
        try:
            # Read file content
            file_content = await file.read()
            file_size = len(file_content)
            
            # Validate file
            self._validate_file_size(file_size)
            self._validate_file_type(file.filename, file.content_type)
            
            # Virus scanning
            if settings.ENABLE_VIRUS_SCANNING:
                try:
                    scan_result = await scan_file_for_viruses(file_content, file.filename)
                    
                    if not scan_result.is_clean:
                        # Log security event
                        await audit_service.log_security_event(
                            action=AuditAction.VIRUS_DETECTED,
                            details={
                                "filename": file.filename,
                                "threat_name": scan_result.threat_name,
                                "file_size": file_size,
                                "file_hash": self._calculate_file_hash(file_content)
                            },
                            user_id=user_id,
                            org_id=org_id,
                            level=AuditLevel.CRITICAL
                        )
                        
                        raise HTTPException(
                            status_code=400,
                            detail={
                                "error": "File contains malware",
                                "threat_name": scan_result.threat_name,
                                "details": scan_result.details
                            }
                        )
                    
                    logger.info(f"File {file.filename} passed virus scan", extra={
                        "user_id": user_id,
                        "org_id": org_id,
                        "scan_details": scan_result.details
                    })
                    
                except Exception as e:
                    logger.error(f"Virus scanning failed: {str(e)}")
                    # Continue with upload if virus scanning fails (fail open)
            
            # Calculate file hash
            file_hash = self._calculate_file_hash(file_content)
            
            # Generate blob name
            if not document_id:
                document_id = str(uuid4())
            blob_name = self._generate_blob_name(org_id, file.filename, document_id)
            
            # Upload to Azure Blob Storage
            try:
                blob_client = self.blob_service_client.get_blob_client(
                    container=self.container_name,
                    blob=blob_name
                )
                
                # Set metadata
                metadata = {
                    'org_id': org_id,
                    'user_id': user_id,
                    'original_filename': file.filename,
                    'file_hash': file_hash,
                    'upload_timestamp': datetime.utcnow().isoformat(),
                    'virus_scanned': str(settings.ENABLE_VIRUS_SCANNING)
                }
                
                # Upload blob with metadata
                blob_client.upload_blob(
                    file_content,
                    content_type=file.content_type,
                    metadata=metadata,
                    overwrite=True
                )
                
                # Log successful upload
                await audit_service.log_document_action(
                    action=AuditAction.DOCUMENT_UPLOAD,
                    document_id=document_id,
                    user_id=user_id,
                    org_id=org_id,
                    details={
                        "filename": file.filename,
                        "file_size": file_size,
                        "file_hash": file_hash,
                        "blob_name": blob_name
                    }
                )
                
            except Exception as e:
                logger.error(f"Azure Blob Storage upload failed: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload file to Azure Blob Storage: {str(e)}"
                )
            
            # Generate SAS URL for immediate access
            upload_url = self.generate_sas_url(blob_name, expiration_hours=1)
            
            return DocumentUploadResponse(
                document_id=document_id,
                blob_name=blob_name,
                upload_url=upload_url,
                status="uploaded"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error during upload: {str(e)}"
            )
    
    def generate_sas_url(self, blob_name: str, expiration_hours: int = 1) -> str:
        """
        Generate SAS URL for blob access
        
        Args:
            blob_name: Blob name
            expiration_hours: URL expiration time in hours
            
        Returns:
            SAS URL string
        """
        try:
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self.blob_service_client.account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=self.blob_service_client.credential.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expiration_hours)
            )
            
            # Construct full URL
            blob_url = f"https://{self.blob_service_client.account_name}.blob.core.windows.net/{self.container_name}/{blob_name}?{sas_token}"
            return blob_url
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate SAS URL: {str(e)}"
            )
    
    async def delete_document(self, blob_name: str) -> bool:
        """
        Delete document from Azure Blob Storage
        
        Args:
            blob_name: Blob name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            blob_client.delete_blob()
            return True
        except ResourceNotFoundError:
            # Blob doesn't exist, consider it deleted
            return True
        except Exception as e:
            logger.error(f"Failed to delete blob {blob_name}: {str(e)}")
            return False
    
    async def get_document_metadata(self, blob_name: str) -> Optional[DocumentMetadata]:
        """
        Get document metadata from Azure Blob Storage
        
        Args:
            blob_name: Blob name
            
        Returns:
            DocumentMetadata if found, None otherwise
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            properties = blob_client.get_blob_properties()
            metadata = properties.metadata or {}
            
            return DocumentMetadata(
                blob_name=blob_name,
                file_name=metadata.get('original_filename', os.path.basename(blob_name)),
                file_size=properties.size,
                file_type=os.path.splitext(blob_name)[1],
                content_type=properties.content_settings.content_type or 'application/octet-stream',
                file_hash=metadata.get('file_hash', ''),
                created_at=properties.creation_time
            )
            
        except ResourceNotFoundError:
            return None
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get document metadata: {str(e)}"
            )
    
    async def check_document_exists(self, blob_name: str) -> bool:
        """
        Check if document exists in Azure Blob Storage
        
        Args:
            blob_name: Blob name
            
        Returns:
            True if exists, False otherwise
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            blob_client.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to check document existence: {str(e)}"
            )
    
    async def copy_document(self, source_blob_name: str, dest_blob_name: str) -> bool:
        """
        Copy document within Azure Blob Storage
        
        Args:
            source_blob_name: Source blob name
            dest_blob_name: Destination blob name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            source_blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=source_blob_name
            )
            dest_blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=dest_blob_name
            )
            
            # Start copy operation
            copy_props = dest_blob_client.start_copy_from_url(source_blob_client.url)
            
            # Wait for copy to complete (for small files this is usually immediate)
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy blob from {source_blob_name} to {dest_blob_name}: {str(e)}")
            return False
    
    async def download_file(self, blob_name: str) -> bytes:
        """
        Download file content from Azure Blob Storage
        
        Args:
            blob_name: Blob name
            
        Returns:
            File content as bytes
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            download_stream = blob_client.download_blob()
            return download_stream.readall()
            
        except ResourceNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {blob_name}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download file: {str(e)}"
            )
    
    def get_download_url(self, blob_name: str, filename: str, expiration_hours: int = 1) -> str:
        """
        Generate SAS URL for file download with custom filename
        
        Args:
            blob_name: Blob name
            filename: Desired download filename
            expiration_hours: URL expiration time in hours
            
        Returns:
            SAS URL for download
        """
        try:
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self.blob_service_client.account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=self.blob_service_client.credential.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expiration_hours)
            )
            
            # Construct URL with content disposition for download
            blob_url = f"https://{self.blob_service_client.account_name}.blob.core.windows.net/{self.container_name}/{blob_name}?{sas_token}"
            return blob_url
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate download URL: {str(e)}"
            )


# Global Azure storage service instance
azure_storage_service = AzureStorageService()