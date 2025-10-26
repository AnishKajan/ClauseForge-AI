"""
User repository
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.database import User
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)
    
    async def get_by_email(self, email: str, org_id: Optional[str] = None) -> Optional[User]:
        """Get user by email"""
        if org_id:
            await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(self.model.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_org(self, org_id: UUID) -> List[User]:
        """Get all users in an organization"""
        await self.set_org_context(str(org_id))
        
        result = await self.session.execute(
            select(self.model).where(self.model.org_id == org_id)
        )
        return result.scalars().all()
    
    async def get_by_role(self, role: str, org_id: str) -> List[User]:
        """Get users by role within an organization"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(self.model.role == role)
        )
        return result.scalars().all()
    
    async def get_with_organization(self, user_id: UUID, org_id: Optional[str] = None) -> Optional[User]:
        """Get user with organization loaded"""
        if org_id:
            await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .options(selectinload(self.model.organization))
            .where(self.model.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def update_last_login(self, user_id: UUID, org_id: Optional[str] = None) -> Optional[User]:
        """Update user's last login timestamp"""
        from datetime import datetime
        
        return await self.update(
            user_id, 
            org_id=org_id, 
            last_login=datetime.utcnow()
        )
    
    async def get_by_org_id(self, org_id: str) -> List[User]:
        """Get all users in an organization by org_id string"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(self.model.org_id == UUID(org_id))
        )
        return result.scalars().all()