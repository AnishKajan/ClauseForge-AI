"""
Stripe integration service for billing and subscription management
"""

import stripe
import structlog
from typing import Dict, Any, Optional, List
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from core.config import settings
from models.database import Organization, Subscription, UsageRecord, AuditLog
from repositories.base import BaseRepository

logger = structlog.get_logger()

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service for managing Stripe billing and subscriptions"""
    
    def __init__(self, db: Session):
        self.db = db
        self.base_repo = BaseRepository(db)
    
    async def create_customer(self, org_id: str, email: str, name: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a Stripe customer for an organization"""
        try:
            # Check if customer already exists
            org = self.db.query(Organization).filter(Organization.id == org_id).first()
            if not org:
                raise ValueError(f"Organization {org_id} not found")
            
            subscription = self.db.query(Subscription).filter(Subscription.org_id == org_id).first()
            if subscription and subscription.stripe_customer_id:
                # Return existing customer
                customer = stripe.Customer.retrieve(subscription.stripe_customer_id)
                return {
                    "customer_id": customer.id,
                    "email": customer.email,
                    "name": customer.name,
                    "created": customer.created
                }
            
            # Create new Stripe customer
            customer_data = {
                "email": email,
                "name": name,
                "metadata": {
                    "org_id": str(org_id),
                    **(metadata or {})
                }
            }
            
            customer = stripe.Customer.create(**customer_data)
            
            # Update or create subscription record
            if subscription:
                subscription.stripe_customer_id = customer.id
            else:
                subscription = Subscription(
                    org_id=org_id,
                    stripe_customer_id=customer.id,
                    plan="free",
                    status="active",
                    usage_limits={
                        "pages_per_month": 50,
                        "tokens_per_month": 10000,
                        "documents_per_month": 10
                    }
                )
                self.db.add(subscription)
            
            self.db.commit()
            
            logger.info("Created Stripe customer", customer_id=customer.id, org_id=org_id)
            
            return {
                "customer_id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "created": customer.created
            }
            
        except stripe.error.StripeError as e:
            logger.error("Stripe API error", error=str(e), org_id=org_id)
            raise Exception(f"Failed to create customer: {str(e)}")
        except Exception as e:
            logger.error("Error creating customer", error=str(e), org_id=org_id)
            self.db.rollback()
            raise
    
    async def create_subscription(self, org_id: str, price_id: str, payment_method_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a Stripe subscription for an organization"""
        try:
            subscription_record = self.db.query(Subscription).filter(Subscription.org_id == org_id).first()
            if not subscription_record or not subscription_record.stripe_customer_id:
                raise ValueError("Customer must be created before subscription")
            
            # Create subscription data
            subscription_data = {
                "customer": subscription_record.stripe_customer_id,
                "items": [{"price": price_id}],
                "payment_behavior": "default_incomplete",
                "payment_settings": {"save_default_payment_method": "on_subscription"},
                "expand": ["latest_invoice.payment_intent"],
                "metadata": {
                    "org_id": str(org_id)
                }
            }
            
            if payment_method_id:
                subscription_data["default_payment_method"] = payment_method_id
            
            stripe_subscription = stripe.Subscription.create(**subscription_data)
            
            # Update subscription record
            plan_name = self._get_plan_name_from_price_id(price_id)
            usage_limits = self._get_usage_limits_for_plan(plan_name)
            
            subscription_record.plan = plan_name
            subscription_record.status = stripe_subscription.status
            subscription_record.usage_limits = usage_limits
            
            self.db.commit()
            
            logger.info("Created Stripe subscription", 
                       subscription_id=stripe_subscription.id, 
                       org_id=org_id, 
                       plan=plan_name)
            
            return {
                "subscription_id": stripe_subscription.id,
                "status": stripe_subscription.status,
                "plan": plan_name,
                "client_secret": stripe_subscription.latest_invoice.payment_intent.client_secret if stripe_subscription.latest_invoice else None
            }
            
        except stripe.error.StripeError as e:
            logger.error("Stripe API error", error=str(e), org_id=org_id)
            raise Exception(f"Failed to create subscription: {str(e)}")
        except Exception as e:
            logger.error("Error creating subscription", error=str(e), org_id=org_id)
            self.db.rollback()
            raise
    
    async def handle_webhook(self, event_data: Dict[str, Any], signature: str) -> Dict[str, Any]:
        """Handle Stripe webhook events with idempotency"""
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                event_data, signature, settings.STRIPE_WEBHOOK_SECRET
            )
            
            event_id = event["id"]
            event_type = event["type"]
            
            # Check for idempotency - prevent duplicate processing
            existing_audit = self.db.query(AuditLog).filter(
                AuditLog.payload_json["stripe_event_id"].astext == event_id
            ).first()
            
            if existing_audit:
                logger.info("Webhook already processed", event_id=event_id, event_type=event_type)
                return {"status": "already_processed", "event_id": event_id}
            
            # Process the event
            result = await self._process_webhook_event(event)
            
            # Log the event for audit trail
            audit_log = AuditLog(
                org_id=result.get("org_id"),
                action=f"stripe_webhook_{event_type}",
                resource_type="subscription",
                payload_json={
                    "stripe_event_id": event_id,
                    "event_type": event_type,
                    "processed_at": datetime.utcnow().isoformat(),
                    "result": result
                }
            )
            self.db.add(audit_log)
            self.db.commit()
            
            logger.info("Processed webhook", event_id=event_id, event_type=event_type)
            
            return {"status": "processed", "event_id": event_id, "result": result}
            
        except stripe.error.SignatureVerificationError as e:
            logger.error("Invalid webhook signature", error=str(e))
            raise Exception("Invalid webhook signature")
        except Exception as e:
            logger.error("Error processing webhook", error=str(e))
            self.db.rollback()
            raise
    
    async def _process_webhook_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process specific webhook event types"""
        event_type = event["type"]
        data = event["data"]["object"]
        
        if event_type == "customer.subscription.created":
            return await self._handle_subscription_created(data)
        elif event_type == "customer.subscription.updated":
            return await self._handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            return await self._handle_subscription_deleted(data)
        elif event_type == "invoice.payment_succeeded":
            return await self._handle_payment_succeeded(data)
        elif event_type == "invoice.payment_failed":
            return await self._handle_payment_failed(data)
        else:
            logger.info("Unhandled webhook event type", event_type=event_type)
            return {"status": "unhandled", "event_type": event_type}
    
    async def _handle_subscription_created(self, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription created webhook"""
        customer_id = subscription_data["customer"]
        subscription_id = subscription_data["id"]
        status = subscription_data["status"]
        
        # Find organization by customer ID
        subscription_record = self.db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()
        
        if subscription_record:
            subscription_record.status = status
            self.db.commit()
            
            return {
                "org_id": str(subscription_record.org_id),
                "subscription_id": subscription_id,
                "status": status,
                "action": "subscription_created"
            }
        
        return {"status": "customer_not_found", "customer_id": customer_id}
    
    async def _handle_subscription_updated(self, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription updated webhook"""
        customer_id = subscription_data["customer"]
        subscription_id = subscription_data["id"]
        status = subscription_data["status"]
        
        subscription_record = self.db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()
        
        if subscription_record:
            subscription_record.status = status
            self.db.commit()
            
            return {
                "org_id": str(subscription_record.org_id),
                "subscription_id": subscription_id,
                "status": status,
                "action": "subscription_updated"
            }
        
        return {"status": "customer_not_found", "customer_id": customer_id}
    
    async def _handle_subscription_deleted(self, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription deleted webhook"""
        customer_id = subscription_data["customer"]
        subscription_id = subscription_data["id"]
        
        subscription_record = self.db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()
        
        if subscription_record:
            # Downgrade to free plan
            subscription_record.plan = "free"
            subscription_record.status = "canceled"
            subscription_record.usage_limits = self._get_usage_limits_for_plan("free")
            self.db.commit()
            
            return {
                "org_id": str(subscription_record.org_id),
                "subscription_id": subscription_id,
                "action": "subscription_canceled"
            }
        
        return {"status": "customer_not_found", "customer_id": customer_id}
    
    async def _handle_payment_succeeded(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful payment webhook"""
        customer_id = invoice_data["customer"]
        amount_paid = invoice_data["amount_paid"]
        
        subscription_record = self.db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()
        
        if subscription_record:
            return {
                "org_id": str(subscription_record.org_id),
                "amount_paid": amount_paid,
                "action": "payment_succeeded"
            }
        
        return {"status": "customer_not_found", "customer_id": customer_id}
    
    async def _handle_payment_failed(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed payment webhook"""
        customer_id = invoice_data["customer"]
        
        subscription_record = self.db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()
        
        if subscription_record:
            # Could implement logic to suspend service or send notifications
            return {
                "org_id": str(subscription_record.org_id),
                "action": "payment_failed"
            }
        
        return {"status": "customer_not_found", "customer_id": customer_id}
    
    async def track_usage(self, org_id: str, usage_type: str, amount: int, period_start: Optional[date] = None, period_end: Optional[date] = None) -> bool:
        """Track usage for billing purposes"""
        try:
            # Default to current month if no period specified
            if not period_start:
                today = date.today()
                period_start = date(today.year, today.month, 1)
            
            if not period_end:
                # Last day of the month
                if period_start.month == 12:
                    period_end = date(period_start.year + 1, 1, 1) - timedelta(days=1)
                else:
                    period_end = date(period_start.year, period_start.month + 1, 1) - timedelta(days=1)
            
            # Check if usage record already exists for this period
            existing_record = self.db.query(UsageRecord).filter(
                and_(
                    UsageRecord.org_id == org_id,
                    UsageRecord.usage_type == usage_type,
                    UsageRecord.period_start == period_start,
                    UsageRecord.period_end == period_end
                )
            ).first()
            
            if existing_record:
                existing_record.amount += amount
            else:
                usage_record = UsageRecord(
                    org_id=org_id,
                    usage_type=usage_type,
                    amount=amount,
                    period_start=period_start,
                    period_end=period_end
                )
                self.db.add(usage_record)
            
            self.db.commit()
            
            logger.info("Tracked usage", 
                       org_id=org_id, 
                       usage_type=usage_type, 
                       amount=amount,
                       period_start=period_start,
                       period_end=period_end)
            
            return True
            
        except Exception as e:
            logger.error("Error tracking usage", error=str(e), org_id=org_id)
            self.db.rollback()
            raise
    
    async def get_usage_summary(self, org_id: str, period_start: Optional[date] = None, period_end: Optional[date] = None) -> Dict[str, Any]:
        """Get usage summary for an organization"""
        try:
            # Default to current month if no period specified
            if not period_start:
                today = date.today()
                period_start = date(today.year, today.month, 1)
            
            if not period_end:
                # Last day of the month
                if period_start.month == 12:
                    period_end = date(period_start.year + 1, 1, 1) - timedelta(days=1)
                else:
                    period_end = date(period_start.year, period_start.month + 1, 1) - timedelta(days=1)
            
            usage_records = self.db.query(UsageRecord).filter(
                and_(
                    UsageRecord.org_id == org_id,
                    UsageRecord.period_start >= period_start,
                    UsageRecord.period_end <= period_end
                )
            ).all()
            
            # Get subscription limits
            subscription = self.db.query(Subscription).filter(Subscription.org_id == org_id).first()
            limits = subscription.usage_limits if subscription else self._get_usage_limits_for_plan("free")
            
            # Aggregate usage by type
            usage_summary = {}
            for record in usage_records:
                if record.usage_type not in usage_summary:
                    usage_summary[record.usage_type] = 0
                usage_summary[record.usage_type] += record.amount
            
            # Calculate percentages and remaining
            result = {
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "plan": subscription.plan if subscription else "free",
                "limits": limits,
                "usage": usage_summary,
                "remaining": {},
                "percentage_used": {}
            }
            
            for usage_type, limit in limits.items():
                used = usage_summary.get(usage_type.replace("_per_month", ""), 0)
                result["remaining"][usage_type] = max(0, limit - used)
                result["percentage_used"][usage_type] = min(100, (used / limit * 100) if limit > 0 else 0)
            
            return result
            
        except Exception as e:
            logger.error("Error getting usage summary", error=str(e), org_id=org_id)
            raise
    
    def _get_plan_name_from_price_id(self, price_id: str) -> str:
        """Map Stripe price ID to plan name"""
        price_plan_mapping = {
            settings.STRIPE_PRO_PRICE_ID: "pro",
            settings.STRIPE_ENTERPRISE_PRICE_ID: "enterprise"
        }
        return price_plan_mapping.get(price_id, "free")
    
    def _get_usage_limits_for_plan(self, plan: str) -> Dict[str, int]:
        """Get usage limits for a specific plan"""
        limits = {
            "free": {
                "pages_per_month": 50,
                "tokens_per_month": 10000,
                "documents_per_month": 10
            },
            "pro": {
                "pages_per_month": 1500,
                "tokens_per_month": 100000,
                "documents_per_month": 100
            },
            "enterprise": {
                "pages_per_month": 10000,
                "tokens_per_month": 1000000,
                "documents_per_month": 1000
            }
        }
        return limits.get(plan, limits["free"])