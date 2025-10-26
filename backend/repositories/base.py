"""
Base repository class with multi-tenant support
"""

from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, text
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import NoResultFound

from core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with multi-tenant support using RLS"""
    
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session
    
    async def set_org_context(self, org_id: str) -> None:
        """Set organization context for Row Level Security"""
        await self.session.execute(
            text("SELECT set_config('app.current_org', :org_id, true)"),
            {"org_id": str(org_id)}
        )
    
    async def create(self, **kwargs) -> ModelType:
        """Create a new record"""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
    
    async def get_by_id(self, id: UUID, org_id: Optional[str] = None) -> Optional[ModelType]:
        """Get record by ID with optional org context"""
        if org_id:
            await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_id_or_404(self, id: UUID, org_id: Optional[str] = None) -> ModelType:
        """Get record by ID or raise exception"""
        instance = await self.get_by_id(id, org_id)
        if not instance:
            raise NoResultFound(f"{self.model.__name__} with id {id} not found")
        return instance
    
    async def get_all(self, org_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """Get all records with pagination"""
        if org_id:
            await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return result.scalars().all()
    
    async def get_by_filter(self, org_id: Optional[str] = None, **filters) -> List[ModelType]:
        """Get records by filter criteria"""
        if org_id:
            await self.set_org_context(org_id)
        
        query = select(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update(self, id: UUID, org_id: Optional[str] = None, **kwargs) -> Optional[ModelType]:
        """Update record by ID"""
        if org_id:
            await self.set_org_context(org_id)
        
        # First get the record to ensure it exists and is accessible
        instance = await self.get_by_id(id, org_id)
        if not instance:
            return None
        
        # Update the record
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
    
    async def delete(self, id: UUID, org_id: Optional[str] = None) -> bool:
        """Delete record by ID"""
        if org_id:
            await self.set_org_context(org_id)
        
        # First check if record exists and is accessible
        instance = await self.get_by_id(id, org_id)
        if not instance:
            return False
        
        await self.session.delete(instance)
        await self.session.flush()
        return True
    
    async def count(self, org_id: Optional[str] = None, **filters) -> int:
        """Count records with optional filters"""
        if org_id:
            await self.set_org_context(org_id)
        
        query = select(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)
        
        result = await self.session.execute(query)
        return len(result.scalars().all())
    
    async def exists(self, id: UUID, org_id: Optional[str] = None) -> bool:
        """Check if record exists"""
        instance = await self.get_by_id(id, org_id)
        return instance is not None