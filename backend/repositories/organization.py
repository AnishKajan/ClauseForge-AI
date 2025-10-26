"""
Organization repository
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.database import Organization
from .base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    """Repository for Organization model"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Organization, session)
    
    async def get_by_name(self, name: str) -> Optional[Organization]:
        """Get organization by name"""
        result = await self.session.execute(
            select(self.model).where(self.model.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_with_users(self, org_id: UUID) -> Optional[Organization]:
        """Get organization with users loaded"""
        result = await self.session.execute(
            select(self.model)
            .options(selectinload(self.model.users))
            .where(self.model.id == org_id)
        )
        return result.scalar_one_or_none()
    
    async def get_with_documents(self, org_id: UUID) -> Optional[Organization]:
        """Get organization with documents loaded"""
        result = await self.session.execute(
            select(self.model)
            .options(selectinload(self.model.documents))
            .where(self.model.id == org_id)
        )
        return result.scalar_one_or_none()
    
    async def search_by_name(self, name_pattern: str, limit: int = 10) -> List[Organization]:
        """Search organizations by name pattern"""
        result = await self.session.execute(
            select(self.model)
            .where(self.model.name.ilike(f"%{name_pattern}%"))
            .limit(limit)
        )
        return result.scalars().all()