"""
Storage migration service to handle transition from AWS S3 to Azure Blob Storage
"""

import logging
from typing import Optional, Union
from fastapi import UploadFile

from core.config import settings
from services.storage import StorageService, DocumentUploadResponse
from services.azure_storage import AzureStorageService

logger = logging.getLogger(__name__)


class StorageMigrationService:
    """
    Service that handles storage operations during AWS to Azure migration.
    Can route to either AWS S3 or Azure Blob Storage based on configuration.
    """
    
    def __init__(self):
        self.aws_storage = None
        self.azure_storage = None
        
        # Initialize AWS storage if credentials are available
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            try:
                self.aws_storage = StorageService()
                logger.info("AWS S3 storage service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS storage: {e}")
        
        # Initialize Azure storage if credentials are available
        if (settings.AZURE_STORAGE_CONNECTION_STRING or 
            (settings.AZURE_STORAGE_ACCOUNT_NAME and settings.AZURE_STORAGE_ACCOUNT_KEY)):
            try:
                self.azure_storage = AzureStorageService()
                logger.info("Azure Blob storage service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Azure storage: {e}")
        
        # Determine primary storage provider
        self.primary_provider = self._determine_primary_provider()
        logger.info(f"Primary storage provider: {self.primary_provider}")
    
    def _determine_primary_provider(self) -> str:
        """Determine which storage provider to use as primary"""
        # Prefer Azure if available (migration target)
        if self.azure_storage:
            return "azure"
        elif self.aws_storage:
            return "aws"
        else:
            raise RuntimeError("No storage provider available. Configure either AWS or Azure credentials.")
    
    def get_primary_storage(self) -> Union[StorageService, AzureStorageService]:
        """Get the primary storage service"""
        if self.primary_provider == "azure":
            return self.azure_storage
        else:
            return self.aws_storage
    
    async def upload_document(
        self,
        file: UploadFile,
        org_id: str,
        user_id: str,
        document_id: Optional[str] = None
    ) -> DocumentUploadResponse:
        """
        Upload document using the primary storage provider
        """
        storage_service = self.get_primary_storage()
        return await storage_service.upload_document(file, org_id, user_id, document_id)
    
    async def download_file(self, storage_key: str) -> bytes:
        """
        Download file from appropriate storage provider
        
        Args:
            storage_key: Either S3 key or Azure blob name
        """
        # Try primary provider first
        try:
            storage_service = self.get_primary_storage()
            return await storage_service.download_file(storage_key)
        except Exception as e:
            logger.warning(f"Failed to download from primary provider: {e}")
            
            # Try fallback provider
            fallback_service = self.azure_storage if self.primary_provider == "aws" else self.aws_storage
            if fallback_service:
                try:
                    return await fallback_service.download_file(storage_key)
                except Exception as fallback_e:
                    logger.error(f"Failed to download from fallback provider: {fallback_e}")
                    raise e  # Raise original exception
            else:
                raise e
    
    async def delete_document(self, storage_key: str) -> bool:
        """
        Delete document from appropriate storage provider
        """
        success = False
        
        # Try to delete from both providers (in case of duplicates during migration)
        if self.aws_storage:
            try:
                aws_success = await self.aws_storage.delete_document(storage_key)
                success = success or aws_success
            except Exception as e:
                logger.warning(f"Failed to delete from AWS: {e}")
        
        if self.azure_storage:
            try:
                azure_success = await self.azure_storage.delete_document(storage_key)
                success = success or azure_success
            except Exception as e:
                logger.warning(f"Failed to delete from Azure: {e}")
        
        return success
    
    async def migrate_document(self, storage_key: str, org_id: str, user_id: str) -> Optional[str]:
        """
        Migrate a document from AWS S3 to Azure Blob Storage
        
        Args:
            storage_key: S3 key of the document to migrate
            org_id: Organization ID
            user_id: User ID
            
        Returns:
            New Azure blob name if successful, None otherwise
        """
        if not self.aws_storage or not self.azure_storage:
            logger.error("Both AWS and Azure storage services required for migration")
            return None
        
        try:
            # Download from S3
            logger.info(f"Downloading document from S3: {storage_key}")
            file_content = await self.aws_storage.download_file(storage_key)
            
            # Get metadata from S3
            s3_metadata = await self.aws_storage.get_document_metadata(storage_key)
            if not s3_metadata:
                logger.error(f"Could not get metadata for S3 object: {storage_key}")
                return None
            
            # Create a mock UploadFile for Azure upload
            from fastapi import UploadFile
            from io import BytesIO
            
            mock_file = UploadFile(
                filename=s3_metadata.file_name,
                file=BytesIO(file_content),
                size=s3_metadata.file_size,
                headers={"content-type": s3_metadata.content_type}
            )
            
            # Upload to Azure
            logger.info(f"Uploading document to Azure: {s3_metadata.file_name}")
            upload_response = await self.azure_storage.upload_document(
                mock_file, org_id, user_id
            )
            
            logger.info(f"Successfully migrated document: {storage_key} -> {upload_response.blob_name}")
            return upload_response.blob_name
            
        except Exception as e:
            logger.error(f"Failed to migrate document {storage_key}: {e}")
            return None
    
    async def verify_migration(self, s3_key: str, blob_name: str) -> bool:
        """
        Verify that a document was successfully migrated by comparing hashes
        
        Args:
            s3_key: Original S3 key
            blob_name: New Azure blob name
            
        Returns:
            True if migration is verified, False otherwise
        """
        if not self.aws_storage or not self.azure_storage:
            return False
        
        try:
            # Get metadata from both providers
            s3_metadata = await self.aws_storage.get_document_metadata(s3_key)
            azure_metadata = await self.azure_storage.get_document_metadata(blob_name)
            
            if not s3_metadata or not azure_metadata:
                return False
            
            # Compare file hashes
            return s3_metadata.file_hash == azure_metadata.file_hash
            
        except Exception as e:
            logger.error(f"Failed to verify migration: {e}")
            return False
    
    def get_storage_info(self) -> dict:
        """Get information about available storage providers"""
        return {
            "primary_provider": self.primary_provider,
            "aws_available": self.aws_storage is not None,
            "azure_available": self.azure_storage is not None,
            "migration_capable": self.aws_storage is not None and self.azure_storage is not None
        }


# Global migration service instance
storage_migration_service = StorageMigrationService()