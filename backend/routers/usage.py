"""
Usage monitoring and analytics API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import date, datetime, timedelta
import structlog

from core.dependencies import get_db, get_current_user
from core.auth_dependencies import require_role
from core.usage_middleware import UsageAnalytics
from services.notification_service import UsageReportGenerator
from models.database import User

logger = structlog.get_logger()

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/analytics", response_model=Dict[str, Any])
async def get_usage_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get usage analytics for the current organization"""
    try:
        analytics_service = UsageAnalytics(db)
        analytics = await analytics_service.get_organization_analytics(
            org_id=str(current_user.org_id),
            days=days
        )
        
        return {"success": True, "data": analytics}
        
    except Exception as e:
        logger.error("Error getting usage analytics", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage analytics: {str(e)}"
        )


@router.get("/report", response_model=Dict[str, Any])
async def generate_usage_report(
    period_start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    period_end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(require_role(["admin", "owner"])),
    db: Session = Depends(get_db)
):
    """Generate detailed usage report for the organization"""
    try:
        # Default to current month if no dates provided
        if not period_start:
            today = date.today()
            start_date = date(today.year, today.month, 1)
        else:
            start_date = date.fromisoformat(period_start)
        
        if not period_end:
            end_date = date.today()
        else:
            end_date = date.fromisoformat(period_end)
        
        report_generator = UsageReportGenerator(db)
        report = await report_generator.generate_organization_report(
            org_id=str(current_user.org_id),
            period_start=start_date,
            period_end=end_date
        )
        
        return {"success": True, "data": report}
        
    except Exception as e:
        logger.error("Error generating usage report", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate usage report: {str(e)}"
        )


@router.get("/limits", response_model=Dict[str, Any])
async def get_usage_limits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current usage limits and remaining quota"""
    try:
        from services.stripe_service import StripeService
        
        stripe_service = StripeService(db)
        usage_summary = await stripe_service.get_usage_summary(str(current_user.org_id))
        
        # Calculate time until reset
        today = date.today()
        if today.month == 12:
            next_reset = date(today.year + 1, 1, 1)
        else:
            next_reset = date(today.year, today.month + 1, 1)
        
        days_until_reset = (next_reset - today).days
        
        limits_info = {
            "plan": usage_summary["plan"],
            "limits": usage_summary["limits"],
            "usage": usage_summary["usage"],
            "remaining": usage_summary["remaining"],
            "percentage_used": usage_summary["percentage_used"],
            "reset_date": next_reset.isoformat(),
            "days_until_reset": days_until_reset,
            "period": {
                "start": usage_summary["period_start"],
                "end": usage_summary["period_end"]
            }
        }
        
        return {"success": True, "data": limits_info}
        
    except Exception as e:
        logger.error("Error getting usage limits", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage limits: {str(e)}"
        )


@router.get("/history", response_model=Dict[str, Any])
async def get_usage_history(
    months: int = Query(6, ge=1, le=24, description="Number of months of history"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get usage history for the organization"""
    try:
        from repositories.subscription import UsageRecordRepository
        
        usage_repo = UsageRecordRepository(db)
        
        # Get usage records for the specified number of months
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 30)  # Approximate
        
        usage_records = usage_repo.get_usage_summary_for_org(
            org_id=str(current_user.org_id),
            period_start=start_date,
            period_end=end_date
        )
        
        # Group by month and usage type
        monthly_usage = {}
        for record in usage_records:
            month_key = f"{record.period_start.year}-{record.period_start.month:02d}"
            if month_key not in monthly_usage:
                monthly_usage[month_key] = {}
            
            monthly_usage[month_key][record.usage_type] = record.amount
        
        # Convert to list format for easier frontend consumption
        history = []
        for month_key in sorted(monthly_usage.keys()):
            history.append({
                "month": month_key,
                "usage": monthly_usage[month_key]
            })
        
        return {"success": True, "data": {"history": history, "months": months}}
        
    except Exception as e:
        logger.error("Error getting usage history", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage history: {str(e)}"
        )


@router.post("/notifications/test", response_model=Dict[str, Any])
async def test_usage_notification(
    notification_type: str = Query(..., description="Type of notification to test"),
    current_user: User = Depends(require_role(["admin", "owner"])),
    db: Session = Depends(get_db)
):
    """Test usage notification system (admin only)"""
    try:
        from services.notification_service import NotificationService
        
        notification_service = NotificationService(db)
        
        if notification_type == "usage_warning":
            await notification_service.send_usage_limit_warning(
                org_id=str(current_user.org_id),
                usage_type="pages",
                current_usage=45,
                limit=50,
                percentage=90.0
            )
        elif notification_type == "usage_exceeded":
            await notification_service.send_usage_limit_exceeded(
                org_id=str(current_user.org_id),
                usage_type="pages",
                current_usage=55,
                limit=50
            )
        elif notification_type == "monthly_report":
            # Get current usage summary for test
            from services.stripe_service import StripeService
            stripe_service = StripeService(db)
            usage_summary = await stripe_service.get_usage_summary(str(current_user.org_id))
            
            await notification_service.send_monthly_usage_report(
                org_id=str(current_user.org_id),
                usage_summary=usage_summary
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown notification type: {notification_type}"
            )
        
        return {"success": True, "message": f"Test {notification_type} notification sent"}
        
    except Exception as e:
        logger.error("Error sending test notification", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test notification: {str(e)}"
        )


@router.get("/alerts", response_model=Dict[str, Any])
async def get_usage_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current usage alerts and warnings"""
    try:
        from services.stripe_service import StripeService
        
        stripe_service = StripeService(db)
        usage_summary = await stripe_service.get_usage_summary(str(current_user.org_id))
        
        alerts = []
        warnings = []
        
        for usage_type, percentage in usage_summary["percentage_used"].items():
            usage_name = usage_type.replace("_per_month", "").replace("_", " ").title()
            
            if percentage >= 100:
                alerts.append({
                    "type": "limit_exceeded",
                    "usage_type": usage_type,
                    "message": f"{usage_name} limit exceeded ({percentage:.1f}%)",
                    "severity": "critical"
                })
            elif percentage >= 90:
                alerts.append({
                    "type": "approaching_limit",
                    "usage_type": usage_type,
                    "message": f"{usage_name} usage is high ({percentage:.1f}%)",
                    "severity": "warning"
                })
            elif percentage >= 75:
                warnings.append({
                    "type": "moderate_usage",
                    "usage_type": usage_type,
                    "message": f"{usage_name} usage is at {percentage:.1f}%",
                    "severity": "info"
                })
        
        return {
            "success": True,
            "data": {
                "alerts": alerts,
                "warnings": warnings,
                "total_alerts": len(alerts),
                "total_warnings": len(warnings)
            }
        }
        
    except Exception as e:
        logger.error("Error getting usage alerts", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage alerts: {str(e)}"
        )