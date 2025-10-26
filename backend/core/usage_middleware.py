"""
Usage monitoring and limits enforcement middleware
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import structlog
from datetime import date, datetime, timedelta

from core.dependencies import get_db
from services.stripe_service import StripeService
from models.database import User, Subscription

logger = structlog.get_logger()


class UsageLimitMiddleware:
    """Middleware for enforcing usage limits"""
    
    # Define which endpoints consume what resources
    USAGE_MAPPING = {
        "/api/documents": {"usage_type": "documents", "amount": 1},
        "/api/ingestion": {"usage_type": "pages", "amount": 1},  # Will be updated with actual page count
        "/api/rag/query": {"usage_type": "tokens", "amount": 100},  # Estimated, will be updated with actual
        "/api/analysis": {"usage_type": "pages", "amount": 1},  # Will be updated with actual page count
    }
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Skip usage checking for certain endpoints
            if self._should_skip_usage_check(request):
                await self.app(scope, receive, send)
                return
            
            # Check usage limits before processing request
            try:
                await self._check_usage_limits(request)
            except HTTPException as e:
                response = JSONResponse(
                    status_code=e.status_code,
                    content={"error": {"code": "USAGE_LIMIT_EXCEEDED", "message": e.detail}}
                )
                await response(scope, receive, send)
                return
            except Exception as e:
                logger.error("Error checking usage limits", error=str(e))
                # Continue processing if usage check fails (fail open)
        
        await self.app(scope, receive, send)
    
    def _should_skip_usage_check(self, request: Request) -> bool:
        """Determine if usage checking should be skipped for this request"""
        path = request.url.path
        method = request.method
        
        # Skip for non-consuming endpoints
        skip_paths = [
            "/api/health",
            "/api/auth",
            "/api/billing",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        
        # Skip for GET requests that don't consume resources
        if method == "GET" and any(path.startswith(skip_path) for skip_path in skip_paths):
            return True
        
        # Skip for webhook endpoints
        if "webhook" in path:
            return True
        
        return False
    
    async def _check_usage_limits(self, request: Request):
        """Check if the user has exceeded their usage limits"""
        # Get current user from request (this assumes auth middleware has run)
        user = getattr(request.state, "user", None)
        if not user:
            return  # No user, skip usage check
        
        # Get database session
        db = next(get_db())
        try:
            stripe_service = StripeService(db)
            
            # Get usage type for this endpoint
            usage_info = self._get_usage_info(request)
            if not usage_info:
                return  # No usage tracking for this endpoint
            
            # Get current usage summary
            usage_summary = await stripe_service.get_usage_summary(str(user.org_id))
            
            # Check if limit would be exceeded
            usage_type = usage_info["usage_type"]
            amount = usage_info["amount"]
            
            # Map usage type to limit key
            limit_key = f"{usage_type}_per_month"
            current_usage = usage_summary["usage"].get(usage_type, 0)
            limit = usage_summary["limits"].get(limit_key, 0)
            
            if current_usage + amount > limit:
                # Send notification if approaching limit (90% threshold)
                if current_usage / limit >= 0.9:
                    await self._send_limit_notification(user, usage_type, current_usage, limit)
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Usage limit exceeded for {usage_type}. Current: {current_usage}, Limit: {limit}"
                )
            
            # Track the usage (this will be called after successful processing)
            request.state.usage_to_track = usage_info
            
        finally:
            db.close()
    
    def _get_usage_info(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get usage information for the current request"""
        path = request.url.path
        
        # Find matching usage mapping
        for endpoint_pattern, usage_info in self.USAGE_MAPPING.items():
            if path.startswith(endpoint_pattern):
                return usage_info
        
        return None
    
    async def _send_limit_notification(self, user: User, usage_type: str, current_usage: int, limit: int):
        """Send notification when approaching usage limits"""
        try:
            # This could be extended to send actual notifications (email, in-app, etc.)
            logger.warning(
                "User approaching usage limit",
                user_id=str(user.id),
                org_id=str(user.org_id),
                usage_type=usage_type,
                current_usage=current_usage,
                limit=limit,
                percentage_used=round((current_usage / limit) * 100, 2)
            )
            
            # TODO: Implement actual notification system
            # - Email notifications
            # - In-app notifications
            # - Slack/Teams integration for enterprise customers
            
        except Exception as e:
            logger.error("Error sending limit notification", error=str(e))


class UsageTracker:
    """Utility class for tracking usage after successful operations"""
    
    @staticmethod
    async def track_usage(request: Request, actual_amount: Optional[int] = None):
        """Track usage for a completed operation"""
        try:
            user = getattr(request.state, "user", None)
            usage_info = getattr(request.state, "usage_to_track", None)
            
            if not user or not usage_info:
                return
            
            # Use actual amount if provided, otherwise use estimated amount
            amount = actual_amount or usage_info["amount"]
            
            # Get database session
            db = next(get_db())
            try:
                stripe_service = StripeService(db)
                await stripe_service.track_usage(
                    org_id=str(user.org_id),
                    usage_type=usage_info["usage_type"],
                    amount=amount
                )
                
                logger.info(
                    "Tracked usage",
                    user_id=str(user.id),
                    org_id=str(user.org_id),
                    usage_type=usage_info["usage_type"],
                    amount=amount
                )
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error("Error tracking usage", error=str(e))


class UsageAnalytics:
    """Service for usage analytics and reporting"""
    
    def __init__(self, db: Session):
        self.db = db
        self.stripe_service = StripeService(db)
    
    async def get_organization_analytics(self, org_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage analytics for an organization"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # Get usage summary for the period
            usage_summary = await self.stripe_service.get_usage_summary(
                org_id=org_id,
                period_start=start_date,
                period_end=end_date
            )
            
            # Get subscription info
            subscription = self.db.query(Subscription).filter(
                Subscription.org_id == org_id
            ).first()
            
            # Calculate trends and insights
            analytics = {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "days": days
                },
                "subscription": {
                    "plan": subscription.plan if subscription else "free",
                    "status": subscription.status if subscription else "active"
                },
                "usage": usage_summary["usage"],
                "limits": usage_summary["limits"],
                "remaining": usage_summary["remaining"],
                "percentage_used": usage_summary["percentage_used"],
                "insights": self._generate_insights(usage_summary),
                "recommendations": self._generate_recommendations(usage_summary)
            }
            
            return analytics
            
        except Exception as e:
            logger.error("Error getting organization analytics", error=str(e), org_id=org_id)
            raise
    
    def _generate_insights(self, usage_summary: Dict[str, Any]) -> List[str]:
        """Generate insights based on usage patterns"""
        insights = []
        
        for usage_type, percentage in usage_summary["percentage_used"].items():
            if percentage >= 90:
                insights.append(f"High usage alert: {usage_type.replace('_per_month', '')} usage is at {percentage:.1f}%")
            elif percentage >= 75:
                insights.append(f"Approaching limit: {usage_type.replace('_per_month', '')} usage is at {percentage:.1f}%")
        
        # Check for underutilization
        for usage_type, percentage in usage_summary["percentage_used"].items():
            if percentage < 25:
                insights.append(f"Low utilization: {usage_type.replace('_per_month', '')} usage is only {percentage:.1f}%")
        
        return insights
    
    def _generate_recommendations(self, usage_summary: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on usage patterns"""
        recommendations = []
        plan = usage_summary["plan"]
        
        # Check if user should upgrade
        high_usage_count = sum(1 for p in usage_summary["percentage_used"].values() if p >= 80)
        if high_usage_count >= 2 and plan == "free":
            recommendations.append("Consider upgrading to Pro plan for higher limits and advanced features")
        elif high_usage_count >= 2 and plan == "pro":
            recommendations.append("Consider upgrading to Enterprise plan for unlimited usage and premium features")
        
        # Check if user should downgrade
        low_usage_count = sum(1 for p in usage_summary["percentage_used"].values() if p < 30)
        if low_usage_count >= 2 and plan in ["pro", "enterprise"]:
            recommendations.append("You might be able to save costs with a lower-tier plan based on your usage")
        
        return recommendations