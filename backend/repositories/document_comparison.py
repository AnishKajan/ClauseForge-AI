"""
Document comparison repository
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from models.database import DocumentComparison
from .base import BaseRepository


class DocumentComparisonRepository(BaseRepository[DocumentComparison]):
    """Repository for DocumentComparison model"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(DocumentComparison, session)
    
    async def get_by_documents(self, document_a_id: UUID, document_b_id: UUID, org_id: str) -> Optional[DocumentComparison]:
        """Get comparison between two documents (order independent)"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .options(
                selectinload(self.model.document_a),
                selectinload(self.model.document_b),
                selectinload(self.model.creator)
            )
            .where(
                or_(
                    and_(
                        self.model.document_a_id == document_a_id,
                        self.model.document_b_id == document_b_id
                    ),
                    and_(
                        self.model.document_a_id == document_b_id,
                        self.model.document_b_id == document_a_id
                    )
                )
            )
            .order_by(self.model.created_at.desc())
        )
        return result.scalar_one_or_none()
    
    async def get_by_document(self, document_id: UUID, org_id: str) -> List[DocumentComparison]:
        """Get all comparisons involving a specific document"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .options(
                selectinload(self.model.document_a),
                selectinload(self.model.document_b),
                selectinload(self.model.creator)
            )
            .where(
                or_(
                    self.model.document_a_id == document_id,
                    self.model.document_b_id == document_id
                )
            )
            .order_by(self.model.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_recent(self, org_id: str, limit: int = 10) -> List[DocumentComparison]:
        """Get recent comparisons within organization"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .options(
                selectinload(self.model.document_a),
                selectinload(self.model.document_b),
                selectinload(self.model.creator)
            )
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_user(self, user_id: UUID, org_id: str) -> List[DocumentComparison]:
        """Get comparisons created by a specific user"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .options(
                selectinload(self.model.document_a),
                selectinload(self.model.document_b)
            )
            .where(self.model.created_by == user_id)
            .order_by(self.model.created_at.desc())
        )
        return result.scalars().all()