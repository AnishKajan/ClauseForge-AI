"""
Playbook repository
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.database import Playbook
from .base import BaseRepository


class PlaybookRepository(BaseRepository[Playbook]):
    """Repository for Playbook model"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Playbook, session)
    
    async def get_by_org(self, org_id: str) -> List[Playbook]:
        """Get all playbooks for an organization"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .where(self.model.org_id == UUID(org_id))
            .order_by(self.model.is_default.desc(), self.model.name)
        )
        return result.scalars().all()
    
    async def get_default(self, org_id: str) -> Optional[Playbook]:
        """Get the default playbook for an organization"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.org_id == UUID(org_id),
                    self.model.is_default == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str, org_id: str) -> Optional[Playbook]:
        """Get playbook by name within organization"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.org_id == UUID(org_id),
                    self.model.name == name
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def search_by_name(self, name_pattern: str, org_id: str) -> List[Playbook]:
        """Search playbooks by name pattern"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.org_id == UUID(org_id),
                    self.model.name.ilike(f"%{name_pattern}%")
                )
            )
        )
        return result.scalars().all()
    
    async def set_as_default(self, playbook_id: UUID, org_id: str) -> Optional[Playbook]:
        """Set a playbook as default (and unset others)"""
        await self.set_org_context(org_id)
        
        # First, unset all other defaults
        all_playbooks = await self.get_by_org(org_id)
        for playbook in all_playbooks:
            if playbook.is_default:
                await self.update(playbook.id, org_id=org_id, is_default=False)
        
        # Set the new default
        return await self.update(playbook_id, org_id=org_id, is_default=True)
    
    async def validate_rules_schema(self, rules_json: dict) -> bool:
        """Validate playbook rules JSON schema"""
        # Basic validation - in a real implementation, you'd use a proper JSON schema validator
        required_fields = ["rules", "version"]
        
        if not isinstance(rules_json, dict):
            return False
        
        for field in required_fields:
            if field not in rules_json:
                return False
        
        if not isinstance(rules_json.get("rules"), list):
            return False
        
        return True
    
    async def create_with_validation(self, org_id: str, **kwargs) -> Playbook:
        """Create playbook with rules validation"""
        await self.set_org_context(org_id)
        
        rules_json = kwargs.get("rules_json", {})
        if not await self.validate_rules_schema(rules_json):
            raise ValueError("Invalid playbook rules schema")
        
        kwargs["org_id"] = UUID(org_id)
        return await self.create(**kwargs)