"""
Clause repository
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.database import Clause
from .base import BaseRepository


class ClauseRepository(BaseRepository[Clause]):
    """Repository for Clause model"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Clause, session)
    
    async def get_by_document(self, document_id: UUID, org_id: str) -> List[Clause]:
        """Get all clauses for a document"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .where(self.model.document_id == document_id)
            .order_by(self.model.page, self.model.created_at)
        )
        return result.scalars().all()
    
    async def get_by_type(self, document_id: UUID, clause_type: str, org_id: str) -> List[Clause]:
        """Get clauses by type for a document"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.document_id == document_id,
                    self.model.clause_type == clause_type
                )
            )
        )
        return result.scalars().all()
    
    async def get_by_risk_level(self, document_id: UUID, risk_level: str, org_id: str) -> List[Clause]:
        """Get clauses by risk level for a document"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.document_id == document_id,
                    self.model.risk_level == risk_level
                )
            )
        )
        return result.scalars().all()
    
    async def get_high_confidence(self, document_id: UUID, org_id: str, min_confidence: float = 0.8) -> List[Clause]:
        """Get high confidence clauses for a document"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.document_id == document_id,
                    self.model.confidence >= min_confidence
                )
            )
        )
        return result.scalars().all()
    
    async def get_by_page(self, document_id: UUID, page: int, org_id: str) -> List[Clause]:
        """Get clauses from a specific page"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.document_id == document_id,
                    self.model.page == page
                )
            )
        )
        return result.scalars().all()
    
    async def search_text(self, document_id: UUID, text_pattern: str, org_id: str) -> List[Clause]:
        """Search clauses by text pattern"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.document_id == document_id,
                    self.model.text.ilike(f"%{text_pattern}%")
                )
            )
        )
        return result.scalars().all()
    
    async def bulk_create_clauses(self, clauses_data: List[dict], org_id: str) -> List[Clause]:
        """Bulk create clauses"""
        await self.set_org_context(org_id)
        
        clauses = []
        for clause_data in clauses_data:
            clause = self.model(**clause_data)
            self.session.add(clause)
            clauses.append(clause)
        
        await self.session.flush()
        
        # Refresh all clauses to get IDs
        for clause in clauses:
            await self.session.refresh(clause)
        
        return clauses
    
    async def delete_by_document(self, document_id: UUID, org_id: str) -> int:
        """Delete all clauses for a document"""
        await self.set_org_context(org_id)
        
        clauses = await self.get_by_document(document_id, org_id)
        count = len(clauses)
        
        for clause in clauses:
            await self.session.delete(clause)
        
        await self.session.flush()
        return count