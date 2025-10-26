"""
Audit log repository
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from models.database import AuditLog
from .base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog model"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(AuditLog, session)
    
    async def log_action(
        self,
        org_id: str,
        user_id: UUID,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        payload: Optional[dict] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log an audit action"""
        await self.set_org_context(org_id)
        
        return await self.create(
            org_id=UUID(org_id),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload_json=payload,
            ip_address=ip_address
        )
    
    async def get_by_user(self, user_id: UUID, org_id: str, limit: int = 100) -> List[AuditLog]:
        """Get audit logs for a specific user"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .where(self.model.user_id == user_id)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_action(self, action: str, org_id: str, limit: int = 100) -> List[AuditLog]:
        """Get audit logs by action type"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .where(self.model.action == action)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_resource(
        self, 
        resource_type: str, 
        resource_id: UUID, 
        org_id: str
    ) -> List[AuditLog]:
        """Get audit logs for a specific resource"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.resource_type == resource_type,
                    self.model.resource_id == resource_id
                )
            ).order_by(self.model.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_recent(self, org_id: str, hours: int = 24, limit: int = 100) -> List[AuditLog]:
        """Get recent audit logs"""
        await self.set_org_context(org_id)
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        result = await self.session.execute(
            select(self.model)
            .where(self.model.created_at >= cutoff_time)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_date_range(
        self, 
        org_id: str,
        start_date: datetime, 
        end_date: datetime,
        limit: int = 1000
    ) -> List[AuditLog]:
        """Get audit logs within date range"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.created_at >= start_date,
                    self.model.created_at <= end_date
                )
            ).order_by(self.model.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    async def search_logs(
        self, 
        org_id: str,
        user_id: Optional[UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        ip_address: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """Search audit logs with multiple filters"""
        await self.set_org_context(org_id)
        
        query = select(self.model)
        conditions = []
        
        if user_id:
            conditions.append(self.model.user_id == user_id)
        if action:
            conditions.append(self.model.action.ilike(f"%{action}%"))
        if resource_type:
            conditions.append(self.model.resource_type == resource_type)
        if ip_address:
            conditions.append(self.model.ip_address == ip_address)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(self.model.created_at.desc()).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_stripe_event_log(self, stripe_event_id: str, org_id: str) -> Optional[AuditLog]:
        """Get audit log for Stripe event (for idempotency)"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(
                self.model.payload_json['stripe_event_id'].astext == stripe_event_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_security_events(self, org_id: str, hours: int = 24) -> List[AuditLog]:
        """Get security-related audit events"""
        await self.set_org_context(org_id)
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        security_actions = [
            'login_failed',
            'login_success',
            'logout',
            'password_change',
            'role_change',
            'permission_denied',
            'suspicious_activity'
        ]
        
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.created_at >= cutoff_time,
                    self.model.action.in_(security_actions)
                )
            ).order_by(self.model.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_by_org_id(self, org_id: str, limit: int = 50, offset: int = 0) -> List[AuditLog]:
        """Get audit logs by organization ID with pagination"""
        await self.set_org_context(org_id)
        
        from sqlalchemy.orm import selectinload
        result = await self.session.execute(
            select(self.model)
            .options(selectinload(self.model.user))
            .where(self.model.org_id == UUID(org_id))
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def count_by_org_id(self, org_id: str) -> int:
        """Count audit logs in organization"""
        await self.set_org_context(org_id)
        
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(self.model.id)).where(self.model.org_id == UUID(org_id))
        )
        return result.scalar() or 0