"""
Document processing service that orchestrates text extraction and embedding generation.
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from services.azure_document_intelligence import AzureDocumentIntelligenceService
from services.text_extraction import TextExtractionService  # Legacy AWS Textract, ExtractedText
from services.embedding import EmbeddingService, EmbeddingResult
from services.storage import StorageService
from repositories.document import DocumentRepository
from repositories.document_chunk import DocumentChunkRepository
from repositories.clause import ClauseRepository
from models.database import DocumentStatus
from core.database import get_async_session

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """Service for processing documents through the AI pipeline."""
    
    def __init__(self):
        self.text_extraction_service = TextExtractionService()
        self.embedding_service = EmbeddingService()
        self.storage_service = StorageService()
    
    async def process_document(self, document_id: UUID, org_id: str) -> Dict[str, Any]:
        """
        Process a document through the complete AI pipeline.
        
        Args:
            document_id: UUID of the document to process
            org_id: Organization ID for multi-tenant access
            
        Returns:
            Processing result with status and metadata
        """
        async with get_async_session() as session:
            try:
                logger.info(f"Starting document processing for {document_id}")
                
                # Initialize repositories
                doc_repo = DocumentRepository(session)
                chunk_repo = DocumentChunkRepository(session)
                clause_repo = ClauseRepository(session)
                
                # Get document
                document = await doc_repo.get_by_id(document_id, org_id)
                if not document:
                    raise ValueError(f"Document {document_id} not found")
                
                # Update status to processing
                await doc_repo.update(
                    document_id, 
                    org_id=org_id,
                    status=DocumentStatus.PROCESSING
                )
                await session.commit()
                
                # Download file from S3
                logger.info(f"Downloading file from S3: {document.s3_key}")
                file_content = await self.storage_service.download_file(document.s3_key)
                
                # Extract text
                logger.info(f"Extracting text from {document.title}")
                extracted_text = await self.text_extraction_service.extract_text(
                    file_content=file_content,
                    file_type=document.file_type,
                    filename=document.title
                )
                
                if not extracted_text.text.strip():
                    logger.warning(f"No text extracted from {document.title}")
                    await doc_repo.update(
                        document_id,
                        org_id=org_id,
                        status=DocumentStatus.FAILED
                    )
                    await session.commit()
                    return {
                        "status": "failed",
                        "error": "No text could be extracted from document"
                    }
                
                # Generate embeddings
                logger.info(f"Generating embeddings for {document.title}")
                embedding_results = await self.embedding_service.process_document(
                    text=extracted_text.text,
                    pages=extracted_text.pages,
                    metadata={
                        "document_id": str(document_id),
                        "filename": document.title,
                        "extraction_method": extracted_text.extraction_method
                    }
                )
                
                # Store chunks with embeddings
                logger.info(f"Storing {len(embedding_results)} chunks")
                chunks_data = []
                for result in embedding_results:
                    chunk_data = {
                        "document_id": document_id,
                        "chunk_no": result.chunk.chunk_no,
                        "text": result.chunk.text,
                        "embedding": result.embedding,
                        "page": result.chunk.page,
                        "metadata": {
                            "model": result.model,
                            "dimensions": result.dimensions,
                            "start_char": result.chunk.start_char,
                            "end_char": result.chunk.end_char,
                            **(result.chunk.metadata or {})
                        }
                    }
                    chunks_data.append(chunk_data)
                
                await chunk_repo.bulk_create_chunks(chunks_data, org_id)
                
                # Identify and store clauses
                logger.info(f"Identifying clauses in {document.title}")
                clause_candidates = self.text_extraction_service.identify_clauses(extracted_text)
                
                clauses_data = []
                for clause in clause_candidates:
                    clause_data = {
                        "document_id": document_id,
                        "clause_type": clause.clause_type,
                        "text": clause.text,
                        "confidence": clause.confidence,
                        "page": clause.page,
                        "risk_level": self._assess_clause_risk(clause.clause_type)
                    }
                    clauses_data.append(clause_data)
                
                if clauses_data:
                    await clause_repo.bulk_create_clauses(clauses_data, org_id)
                
                # Update document status to completed
                await doc_repo.update(
                    document_id,
                    org_id=org_id,
                    status=DocumentStatus.COMPLETED,
                    processed_at=None  # Will be set by database default
                )
                
                await session.commit()
                
                logger.info(f"Successfully processed document {document_id}")
                
                return {
                    "status": "completed",
                    "document_id": str(document_id),
                    "chunks_created": len(embedding_results),
                    "clauses_identified": len(clause_candidates),
                    "extraction_method": extracted_text.extraction_method,
                    "embedding_model": embedding_results[0].model if embedding_results else None,
                    "page_count": extracted_text.page_count
                }
                
            except Exception as e:
                logger.error(f"Document processing failed for {document_id}: {e}")
                
                # Update document status to failed
                try:
                    await doc_repo.update(
                        document_id,
                        org_id=org_id,
                        status=DocumentStatus.FAILED
                    )
                    await session.commit()
                except Exception as update_error:
                    logger.error(f"Failed to update document status: {update_error}")
                
                return {
                    "status": "failed",
                    "document_id": str(document_id),
                    "error": str(e)
                }
    
    def _assess_clause_risk(self, clause_type: str) -> str:
        """Assess risk level for a clause type."""
        high_risk_clauses = {
            'limitation_of_liability',
            'indemnity',
            'termination'
        }
        
        medium_risk_clauses = {
            'confidentiality',
            'governing_law'
        }
        
        if clause_type in high_risk_clauses:
            return 'high'
        elif clause_type in medium_risk_clauses:
            return 'medium'
        else:
            return 'low'