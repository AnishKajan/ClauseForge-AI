"""
Usage record repository
"""

from typing import Optional, List
from uuid import UUID
from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from models.database import UsageRecord
from .base import BaseRepository


class UsageRecordRepository(BaseRepository[UsageRecord]):
    """Repository for UsageRecord model"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(UsageRecord, session)
    
    async def get_by_org_and_period(
        self, 
        org_id: str, 
        period_start: date, 
        period_end: date
    ) -> List[UsageRecord]:
        """Get usage records for organization within period"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.org_id == UUID(org_id),
                    self.model.period_start >= period_start,
                    self.model.period_end <= period_end
                )
            )
        )
        return result.scalars().all()
    
    async def get_current_month_usage(self, org_id: str) -> List[UsageRecord]:
        """Get current month usage for organization"""
        now = datetime.utcnow()
        month_start = date(now.year, now.month, 1)
        
        # Calculate next month start
        if now.month == 12:
            month_end = date(now.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(now.year, now.month + 1, 1) - timedelta(days=1)
        
        return await self.get_by_org_and_period(org_id, month_start, month_end)
    
    async def get_usage_by_type(self, org_id: str, usage_type: str, period_days: int = 30) -> List[UsageRecord]:
        """Get usage records by type for recent period"""
        await self.set_org_context(org_id)
        
        cutoff_date = date.today() - timedelta(days=period_days)
        
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.org_id == UUID(org_id),
                    self.model.usage_type == usage_type,
                    self.model.period_start >= cutoff_date
                )
            )
        )
        return result.scalars().all()
    
    async def get_total_usage(self, org_id: str, usage_type: str, period_days: int = 30) -> int:
        """Get total usage amount for type and period"""
        records = await self.get_usage_by_type(org_id, usage_type, period_days)
        return sum(record.amount for record in records)
    
    async def record_usage(
        self, 
        org_id: str, 
        usage_type: str, 
        amount: int,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None
    ) -> UsageRecord:
        """Record new usage"""
        await self.set_org_context(org_id)
        
        if not period_start:
            period_start = date.today()
        if not period_end:
            period_end = period_start
        
        return await self.create(
            org_id=UUID(org_id),
            usage_type=usage_type,
            amount=amount,
            period_start=period_start,
            period_end=period_end
        )
    
    async def get_usage_summary(self, org_id: str, period_days: int = 30) -> dict:
        """Get usage summary for organization"""
        await self.set_org_context(org_id)
        
        cutoff_date = date.today() - timedelta(days=period_days)
        
        result = await self.session.execute(
            select(
                self.model.usage_type,
                func.sum(self.model.amount).label('total_amount'),
                func.count(self.model.id).label('record_count')
            )
            .where(
                and_(
                    self.model.org_id == UUID(org_id),
                    self.model.period_start >= cutoff_date
                )
            )
            .group_by(self.model.usage_type)
        )
        
        summary = {}
        for row in result.fetchall():
            summary[row.usage_type] = {
                'total_amount': row.total_amount,
                'record_count': row.record_count
            }
        
        return summary
    
    async def get_daily_usage(self, org_id: str, usage_type: str, days: int = 30) -> List[dict]:
        """Get daily usage breakdown"""
        await self.set_org_context(org_id)
        
        cutoff_date = date.today() - timedelta(days=days)
        
        result = await self.session.execute(
            select(
                self.model.period_start,
                func.sum(self.model.amount).label('daily_amount')
            )
            .where(
                and_(
                    self.model.org_id == UUID(org_id),
                    self.model.usage_type == usage_type,
                    self.model.period_start >= cutoff_date
                )
            )
            .group_by(self.model.period_start)
            .order_by(self.model.period_start)
        )
        
        return [
            {
                'date': row.period_start,
                'amount': row.daily_amount
            }
            for row in result.fetchall()
        ]