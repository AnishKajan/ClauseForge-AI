"""
Document repository
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from models.database import Document
from .base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document model"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Document, session)
    
    async def get_by_hash(self, file_hash: str, org_id: str) -> Optional[Document]:
        """Get document by file hash within organization"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.file_hash == file_hash,
                    self.model.org_id == UUID(org_id)
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_status(self, status: str, org_id: str, limit: int = 100) -> List[Document]:
        """Get documents by status within organization"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .where(self.model.status == status)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_uploader(self, uploader_id: UUID, org_id: str) -> List[Document]:
        """Get documents uploaded by specific user"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(self.model.uploaded_by == uploader_id)
        )
        return result.scalars().all()
    
    async def get_with_chunks(self, document_id: UUID, org_id: str) -> Optional[Document]:
        """Get document with chunks loaded"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .options(selectinload(self.model.chunks))
            .where(self.model.id == document_id)
        )
        return result.scalar_one_or_none()
    
    async def get_with_analyses(self, document_id: UUID, org_id: str) -> Optional[Document]:
        """Get document with analyses loaded"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .options(selectinload(self.model.analyses))
            .where(self.model.id == document_id)
        )
        return result.scalar_one_or_none()
    
    async def get_recent(self, org_id: str, limit: int = 10) -> List[Document]:
        """Get recent documents within organization"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    async def search_by_title(self, title_pattern: str, org_id: str, limit: int = 20) -> List[Document]:
        """Search documents by title pattern"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .where(self.model.title.ilike(f"%{title_pattern}%"))
            .limit(limit)
        )
        return result.scalars().all()
    
    async def update_status(self, document_id: UUID, status: str, org_id: str) -> Optional[Document]:
        """Update document status"""
        from datetime import datetime
        
        update_data = {"status": status}
        if status == "completed":
            update_data["processed_at"] = datetime.utcnow()
        
        return await self.update(document_id, org_id=org_id, **update_data)
    
    async def get_by_org_id(self, org_id: str, limit: int = 50, offset: int = 0) -> List[Document]:
        """Get documents by organization ID with pagination"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .options(selectinload(self.model.uploader))
            .where(self.model.org_id == UUID(org_id))
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def count_by_org_id(self, org_id: str) -> int:
        """Count documents in organization"""
        await self.set_org_context(org_id)
        
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(self.model.id)).where(self.model.org_id == UUID(org_id))
        )
        return result.scalar() or 0
    
    async def get_organization_stats(self, org_id: str) -> dict:
        """Get document statistics for organization"""
        await self.set_org_context(org_id)
        
        from sqlalchemy import func
        
        # Get total count
        total_result = await self.session.execute(
            select(func.count(self.model.id)).where(self.model.org_id == UUID(org_id))
        )
        total_count = total_result.scalar() or 0
        
        # Get count by status
        status_result = await self.session.execute(
            select(self.model.status, func.count(self.model.id))
            .where(self.model.org_id == UUID(org_id))
            .group_by(self.model.status)
        )
        status_counts = dict(status_result.fetchall())
        
        # Get total file size
        size_result = await self.session.execute(
            select(func.sum(self.model.file_size)).where(self.model.org_id == UUID(org_id))
        )
        total_size = size_result.scalar() or 0
        
        return {
            "total_documents": total_count,
            "status_breakdown": status_counts,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0
        }