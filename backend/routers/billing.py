"""
Billing and subscription management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import date
import structlog

from core.dependencies import get_db, get_current_user
from core.auth_dependencies import require_role
from services.stripe_service import StripeService
from models.database import User

logger = structlog.get_logger()

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/customers", response_model=Dict[str, Any])
async def create_customer(
    customer_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe customer for the current organization"""
    try:
        stripe_service = StripeService(db)
        
        result = await stripe_service.create_customer(
            org_id=str(current_user.org_id),
            email=customer_data.get("email", current_user.email),
            name=customer_data.get("name", current_user.organization.name),
            metadata=customer_data.get("metadata")
        )
        
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error("Error creating customer", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create customer: {str(e)}"
        )


@router.post("/subscriptions", response_model=Dict[str, Any])
async def create_subscription(
    subscription_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe subscription for the current organization"""
    try:
        stripe_service = StripeService(db)
        
        result = await stripe_service.create_subscription(
            org_id=str(current_user.org_id),
            price_id=subscription_data["price_id"],
            payment_method_id=subscription_data.get("payment_method_id")
        )
        
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error("Error creating subscription", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create subscription: {str(e)}"
        )


@router.post("/webhooks")
async def handle_stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Stripe webhook events"""
    try:
        payload = await request.body()
        signature = request.headers.get("stripe-signature")
        
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe signature"
            )
        
        stripe_service = StripeService(db)
        result = await stripe_service.handle_webhook(payload.decode(), signature)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error("Error handling webhook", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.post("/usage", response_model=Dict[str, Any])
async def track_usage(
    usage_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Track usage for billing purposes"""
    try:
        stripe_service = StripeService(db)
        
        period_start = None
        period_end = None
        
        if usage_data.get("period_start"):
            period_start = date.fromisoformat(usage_data["period_start"])
        if usage_data.get("period_end"):
            period_end = date.fromisoformat(usage_data["period_end"])
        
        success = await stripe_service.track_usage(
            org_id=str(current_user.org_id),
            usage_type=usage_data["usage_type"],
            amount=usage_data["amount"],
            period_start=period_start,
            period_end=period_end
        )
        
        return {"success": success}
        
    except Exception as e:
        logger.error("Error tracking usage", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to track usage: {str(e)}"
        )


@router.get("/usage", response_model=Dict[str, Any])
async def get_usage_summary(
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get usage summary for the current organization"""
    try:
        stripe_service = StripeService(db)
        
        start_date = None
        end_date = None
        
        if period_start:
            start_date = date.fromisoformat(period_start)
        if period_end:
            end_date = date.fromisoformat(period_end)
        
        summary = await stripe_service.get_usage_summary(
            org_id=str(current_user.org_id),
            period_start=start_date,
            period_end=end_date
        )
        
        return {"success": True, "data": summary}
        
    except Exception as e:
        logger.error("Error getting usage summary", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get usage summary: {str(e)}"
        )


@router.get("/subscription", response_model=Dict[str, Any])
async def get_subscription_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current subscription information"""
    try:
        from models.database import Subscription
        
        subscription = db.query(Subscription).filter(
            Subscription.org_id == current_user.org_id
        ).first()
        
        if not subscription:
            return {
                "success": True,
                "data": {
                    "plan": "free",
                    "status": "active",
                    "usage_limits": {
                        "pages_per_month": 50,
                        "tokens_per_month": 10000,
                        "documents_per_month": 10
                    }
                }
            }
        
        return {
            "success": True,
            "data": {
                "plan": subscription.plan,
                "status": subscription.status,
                "usage_limits": subscription.usage_limits,
                "stripe_customer_id": subscription.stripe_customer_id,
                "created_at": subscription.created_at.isoformat()
            }
        }
        
    except Exception as e:
        logger.error("Error getting subscription info", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subscription info: {str(e)}"
        )


@router.get("/plans", response_model=Dict[str, Any])
async def get_available_plans():
    """Get available billing plans"""
    plans = {
        "free": {
            "name": "Free",
            "price": 0,
            "currency": "usd",
            "interval": "month",
            "features": [
                "50 pages per month",
                "10,000 tokens per month",
                "10 documents per month",
                "Basic AI analysis",
                "Email support"
            ],
            "limits": {
                "pages_per_month": 50,
                "tokens_per_month": 10000,
                "documents_per_month": 10
            }
        },
        "pro": {
            "name": "Pro",
            "price": 29,
            "currency": "usd",
            "interval": "month",
            "features": [
                "1,500 pages per month",
                "100,000 tokens per month",
                "100 documents per month",
                "Advanced AI analysis",
                "Claude 3 Sonnet access",
                "Priority support"
            ],
            "limits": {
                "pages_per_month": 1500,
                "tokens_per_month": 100000,
                "documents_per_month": 100
            }
        },
        "enterprise": {
            "name": "Enterprise",
            "price": 199,
            "currency": "usd",
            "interval": "month",
            "features": [
                "10,000 pages per month",
                "1,000,000 tokens per month",
                "1,000 documents per month",
                "Claude 3 Opus access",
                "SSO integration",
                "Team workspaces",
                "Priority queue",
                "Dedicated support"
            ],
            "limits": {
                "pages_per_month": 10000,
                "tokens_per_month": 1000000,
                "documents_per_month": 1000
            }
        }
    }
    
    return {"success": True, "data": plans}