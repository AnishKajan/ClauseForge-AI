"""
Subscription repository for database operations
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import date

from models.database import Subscription, UsageRecord
from repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):
    """Repository for subscription operations"""
    
    def __init__(self, db: Session):
        super().__init__(db, Subscription)
    
    def get_by_org_id(self, org_id: str) -> Optional[Subscription]:
        """Get subscription by organization ID"""
        return self.db.query(Subscription).filter(
            Subscription.org_id == org_id
        ).first()
    
    def get_by_stripe_customer_id(self, customer_id: str) -> Optional[Subscription]:
        """Get subscription by Stripe customer ID"""
        return self.db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()
    
    def update_plan(self, org_id: str, plan: str, status: str, usage_limits: Dict[str, Any]) -> bool:
        """Update subscription plan and limits"""
        subscription = self.get_by_org_id(org_id)
        if subscription:
            subscription.plan = plan
            subscription.status = status
            subscription.usage_limits = usage_limits
            self.db.commit()
            return True
        return False
    
    def get_active_subscriptions(self) -> List[Subscription]:
        """Get all active subscriptions"""
        return self.db.query(Subscription).filter(
            Subscription.status == "active"
        ).all()


class UsageRecordRepository(BaseRepository[UsageRecord]):
    """Repository for usage record operations"""
    
    def __init__(self, db: Session):
        super().__init__(db, UsageRecord)
    
    def get_usage_for_period(self, org_id: str, usage_type: str, period_start: date, period_end: date) -> Optional[UsageRecord]:
        """Get usage record for specific period"""
        return self.db.query(UsageRecord).filter(
            and_(
                UsageRecord.org_id == org_id,
                UsageRecord.usage_type == usage_type,
                UsageRecord.period_start == period_start,
                UsageRecord.period_end == period_end
            )
        ).first()
    
    def get_usage_summary_for_org(self, org_id: str, period_start: date, period_end: date) -> List[UsageRecord]:
        """Get all usage records for organization in period"""
        return self.db.query(UsageRecord).filter(
            and_(
                UsageRecord.org_id == org_id,
                UsageRecord.period_start >= period_start,
                UsageRecord.period_end <= period_end
            )
        ).all()
    
    def get_recent_usage(self, org_id: str, limit: int = 10) -> List[UsageRecord]:
        """Get recent usage records for organization"""
        return self.db.query(UsageRecord).filter(
            UsageRecord.org_id == org_id
        ).order_by(desc(UsageRecord.created_at)).limit(limit).all()
    
    def add_usage(self, org_id: str, usage_type: str, amount: int, period_start: date, period_end: date) -> UsageRecord:
        """Add or update usage record"""
        existing = self.get_usage_for_period(org_id, usage_type, period_start, period_end)
        
        if existing:
            existing.amount += amount
            self.db.commit()
            return existing
        else:
            usage_record = UsageRecord(
                org_id=org_id,
                usage_type=usage_type,
                amount=amount,
                period_start=period_start,
                period_end=period_end
            )
            return self.create(usage_record)