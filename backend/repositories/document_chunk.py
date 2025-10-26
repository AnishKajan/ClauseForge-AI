"""
Document chunk repository with vector search capabilities
"""

from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, and_
from sqlalchemy.orm import selectinload

from models.database import DocumentChunk
from .base import BaseRepository


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    """Repository for DocumentChunk model with vector search"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(DocumentChunk, session)
    
    async def get_by_document(self, document_id: UUID, org_id: str) -> List[DocumentChunk]:
        """Get all chunks for a document"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .where(self.model.document_id == document_id)
            .order_by(self.model.chunk_no)
        )
        return result.scalars().all()
    
    async def get_chunk_by_number(self, document_id: UUID, chunk_no: int, org_id: str) -> Optional[DocumentChunk]:
        """Get specific chunk by document and chunk number"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.document_id == document_id,
                    self.model.chunk_no == chunk_no
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def similarity_search(
        self, 
        query_embedding: List[float], 
        org_id: str,
        document_ids: Optional[List[UUID]] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Tuple[DocumentChunk, float]]:
        """Perform vector similarity search"""
        await self.set_org_context(org_id)
        
        # Build the query
        query = select(
            self.model,
            text("1 - (embedding <=> :query_embedding) as similarity")
        ).where(
            text("1 - (embedding <=> :query_embedding) > :threshold")
        )
        
        # Filter by document IDs if provided
        if document_ids:
            query = query.where(self.model.document_id.in_(document_ids))
        
        # Order by similarity and limit results
        query = query.order_by(text("similarity DESC")).limit(limit)
        
        # Execute query
        result = await self.session.execute(
            query,
            {
                "query_embedding": str(query_embedding),
                "threshold": similarity_threshold
            }
        )
        
        # Return chunks with similarity scores
        return [(row[0], row[1]) for row in result.fetchall()]
    
    async def get_nearby_chunks(
        self, 
        chunk_id: UUID, 
        org_id: str, 
        context_size: int = 2
    ) -> List[DocumentChunk]:
        """Get nearby chunks for context"""
        await self.set_org_context(org_id)
        
        # First get the target chunk
        target_chunk = await self.get_by_id(chunk_id, org_id)
        if not target_chunk:
            return []
        
        # Get chunks before and after
        result = await self.session.execute(
            select(self.model)
            .where(
                and_(
                    self.model.document_id == target_chunk.document_id,
                    self.model.chunk_no >= target_chunk.chunk_no - context_size,
                    self.model.chunk_no <= target_chunk.chunk_no + context_size
                )
            )
            .order_by(self.model.chunk_no)
        )
        return result.scalars().all()
    
    async def get_chunks_by_page(self, document_id: UUID, page: int, org_id: str) -> List[DocumentChunk]:
        """Get chunks from a specific page"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .where(
                and_(
                    self.model.document_id == document_id,
                    self.model.page == page
                )
            )
            .order_by(self.model.chunk_no)
        )
        return result.scalars().all()
    
    async def bulk_create_chunks(self, chunks_data: List[dict], org_id: str) -> List[DocumentChunk]:
        """Bulk create document chunks"""
        await self.set_org_context(org_id)
        
        chunks = []
        for chunk_data in chunks_data:
            chunk = self.model(**chunk_data)
            self.session.add(chunk)
            chunks.append(chunk)
        
        await self.session.flush()
        
        # Refresh all chunks to get IDs
        for chunk in chunks:
            await self.session.refresh(chunk)
        
        return chunks
    
    async def update_embedding(
        self, 
        chunk_id: UUID, 
        embedding: List[float], 
        org_id: str
    ) -> Optional[DocumentChunk]:
        """Update chunk embedding"""
        return await self.update(
            chunk_id,
            org_id=org_id,
            embedding=embedding
        )
    
    async def delete_by_document(self, document_id: UUID, org_id: str) -> int:
        """Delete all chunks for a document"""
        await self.set_org_context(org_id)
        
        chunks = await self.get_by_document(document_id, org_id)
        count = len(chunks)
        
        for chunk in chunks:
            await self.session.delete(chunk)
        
        await self.session.flush()
        return count