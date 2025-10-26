"""
Storage service for S3 integration and file management
"""

import hashlib
import mimetypes
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, BinaryIO
from uuid import UUID, uuid4

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import HTTPException, UploadFile
from pydantic import BaseModel

from core.config import settings
from services.virus_scanner import scan_file_for_viruses, VirusScanResult
from services.audit_service import audit_service, AuditAction, AuditLevel

logger = logging.getLogger(__name__)


class DocumentMetadata(BaseModel):
    """Document metadata model"""
    s3_key: str
    file_name: str
    file_size: int
    file_type: str
    content_type: str
    file_hash: str
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    """Document upload response model"""
    document_id: str
    s3_key: str
    upload_url: str
    status: str = "uploaded"


class StorageService:
    """Service for handling file storage operations with AWS S3"""
    
    def __init__(self):
        """Initialize S3 client"""
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            self.bucket_name = settings.S3_BUCKET_NAME
            
            # Validate bucket access on initialization
            self._validate_bucket_access()
            
        except NoCredentialsError:
            raise HTTPException(
                status_code=500,
                detail="AWS credentials not configured"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize S3 client: {str(e)}"
            )
    
    def _validate_bucket_access(self) -> None:
        """Validate that we can access the S3 bucket"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise HTTPException(
                    status_code=500,
                    detail=f"S3 bucket '{self.bucket_name}' not found"
                )
            elif error_code == '403':
                raise HTTPException(
                    status_code=500,
                    detail=f"Access denied to S3 bucket '{self.bucket_name}'"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error accessing S3 bucket: {str(e)}"
                )
    
    def _generate_s3_key(self, org_id: str, file_name: str, document_id: Optional[str] = None) -> str:
        """Generate S3 key for document storage"""
        if not document_id:
            document_id = str(uuid4())
        
        # Extract file extension
        _, ext = os.path.splitext(file_name)
        
        # Create hierarchical key: org_id/year/month/document_id.ext
        now = datetime.utcnow()
        s3_key = f"{org_id}/{now.year}/{now.month:02d}/{document_id}{ext}"
        
        return s3_key
    
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
        Upload document to S3 with validation and virus scanning
        
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
            
            # Generate S3 key
            if not document_id:
                document_id = str(uuid4())
            s3_key = self._generate_s3_key(org_id, file.filename, document_id)
            
            # Upload to S3
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=file_content,
                    ContentType=file.content_type,
                    Metadata={
                        'org_id': org_id,
                        'user_id': user_id,
                        'original_filename': file.filename,
                        'file_hash': file_hash,
                        'upload_timestamp': datetime.utcnow().isoformat(),
                        'virus_scanned': str(settings.ENABLE_VIRUS_SCANNING)
                    },
                    ServerSideEncryption='AES256'
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
                        "s3_key": s3_key
                    }
                )
                
            except ClientError as e:
                logger.error(f"S3 upload failed: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload file to S3: {str(e)}"
                )
            
            # Generate presigned URL for immediate access
            upload_url = self.generate_presigned_url(s3_key, expiration=3600)
            
            return DocumentUploadResponse(
                document_id=document_id,
                s3_key=s3_key,
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
    
    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Generate presigned URL for S3 object access
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL string
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate presigned URL: {str(e)}"
            )
    
    def generate_presigned_upload_url(
        self,
        s3_key: str,
        content_type: str,
        expiration: int = 3600
    ) -> Dict[str, Any]:
        """
        Generate presigned URL for direct S3 upload
        
        Args:
            s3_key: S3 object key
            content_type: File content type
            expiration: URL expiration time in seconds
            
        Returns:
            Dictionary with presigned POST data
        """
        try:
            response = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=s3_key,
                Fields={'Content-Type': content_type},
                Conditions=[
                    {'Content-Type': content_type},
                    ['content-length-range', 1, settings.MAX_FILE_SIZE_MB * 1024 * 1024]
                ],
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate presigned upload URL: {str(e)}"
            )
    
    async def delete_document(self, s3_key: str) -> bool:
        """
        Delete document from S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError as e:
            # Log error but don't raise exception for delete operations
            print(f"Failed to delete S3 object {s3_key}: {str(e)}")
            return False
    
    async def get_document_metadata(self, s3_key: str) -> Optional[DocumentMetadata]:
        """
        Get document metadata from S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            DocumentMetadata if found, None otherwise
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            # Extract metadata
            metadata = response.get('Metadata', {})
            
            return DocumentMetadata(
                s3_key=s3_key,
                file_name=metadata.get('original_filename', os.path.basename(s3_key)),
                file_size=response['ContentLength'],
                file_type=os.path.splitext(s3_key)[1],
                content_type=response['ContentType'],
                file_hash=metadata.get('file_hash', ''),
                created_at=response['LastModified']
            )
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get document metadata: {str(e)}"
            )
    
    async def check_document_exists(self, s3_key: str) -> bool:
        """
        Check if document exists in S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise HTTPException(
                status_code=500,
                detail=f"Failed to check document existence: {str(e)}"
            )
    
    async def copy_document(self, source_s3_key: str, dest_s3_key: str) -> bool:
        """
        Copy document within S3
        
        Args:
            source_s3_key: Source S3 object key
            dest_s3_key: Destination S3 object key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            copy_source = {'Bucket': self.bucket_name, 'Key': source_s3_key}
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=dest_s3_key,
                ServerSideEncryption='AES256'
            )
            return True
        except ClientError as e:
            print(f"Failed to copy S3 object from {source_s3_key} to {dest_s3_key}: {str(e)}")
            return False
    
    async def download_file(self, s3_key: str) -> bytes:
        """
        Download file content from S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            File content as bytes
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise HTTPException(
                    status_code=404,
                    detail=f"File not found: {s3_key}"
                )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download file: {str(e)}"
            )
    
    def get_download_url(self, s3_key: str, filename: str, expiration: int = 3600) -> str:
        """
        Generate presigned URL for file download with custom filename
        
        Args:
            s3_key: S3 object key
            filename: Desired download filename
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL for download
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                    'ResponseContentDisposition': f'attachment; filename="{filename}"'
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate download URL: {str(e)}"
            )


# Global storage service instance (legacy AWS)
# Use storage_migration_service for new implementations
storage_service = StorageService()