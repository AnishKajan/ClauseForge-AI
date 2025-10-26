"""
Notification service for usage alerts and billing notifications
"""

import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import json

from models.database import User, Organization, Subscription
from core.config import settings

logger = structlog.get_logger()


class NotificationService:
    """Service for sending various types of notifications"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def send_usage_limit_warning(self, org_id: str, usage_type: str, current_usage: int, limit: int, percentage: float):
        """Send warning when usage approaches limit"""
        try:
            # Get organization and admin users
            org = self.db.query(Organization).filter(Organization.id == org_id).first()
            if not org:
                return
            
            admin_users = self.db.query(User).filter(
                User.org_id == org_id,
                User.role.in_(["admin", "owner"])
            ).all()
            
            if not admin_users:
                return
            
            # Create notification content
            subject = f"Usage Alert: {usage_type.replace('_', ' ').title()} Limit Approaching"
            
            message = f"""
            Dear {org.name} Administrator,
            
            Your organization is approaching the usage limit for {usage_type.replace('_', ' ')}.
            
            Current Usage: {current_usage:,}
            Monthly Limit: {limit:,}
            Percentage Used: {percentage:.1f}%
            
            To avoid service interruption, consider upgrading your plan or monitoring your usage.
            
            You can view detailed usage analytics in your dashboard: {settings.FRONTEND_URL}/billing
            
            Best regards,
            The LexiScan Team
            """
            
            # Send to all admin users
            for user in admin_users:
                await self._send_email(user.email, subject, message)
                await self._create_in_app_notification(
                    user.id,
                    "usage_warning",
                    subject,
                    {
                        "usage_type": usage_type,
                        "current_usage": current_usage,
                        "limit": limit,
                        "percentage": percentage
                    }
                )
            
            logger.info("Sent usage limit warning", org_id=org_id, usage_type=usage_type, percentage=percentage)
            
        except Exception as e:
            logger.error("Error sending usage limit warning", error=str(e), org_id=org_id)
    
    async def send_usage_limit_exceeded(self, org_id: str, usage_type: str, current_usage: int, limit: int):
        """Send notification when usage limit is exceeded"""
        try:
            org = self.db.query(Organization).filter(Organization.id == org_id).first()
            if not org:
                return
            
            admin_users = self.db.query(User).filter(
                User.org_id == org_id,
                User.role.in_(["admin", "owner"])
            ).all()
            
            subject = f"Usage Limit Exceeded: {usage_type.replace('_', ' ').title()}"
            
            message = f"""
            Dear {org.name} Administrator,
            
            Your organization has exceeded the usage limit for {usage_type.replace('_', ' ')}.
            
            Current Usage: {current_usage:,}
            Monthly Limit: {limit:,}
            
            Service has been temporarily restricted for this resource type. To restore full access:
            
            1. Upgrade your plan: {settings.FRONTEND_URL}/billing
            2. Contact support for assistance: support@lexiscan.ai
            
            Best regards,
            The LexiScan Team
            """
            
            for user in admin_users:
                await self._send_email(user.email, subject, message)
                await self._create_in_app_notification(
                    user.id,
                    "usage_exceeded",
                    subject,
                    {
                        "usage_type": usage_type,
                        "current_usage": current_usage,
                        "limit": limit
                    }
                )
            
            logger.warning("Sent usage limit exceeded notification", org_id=org_id, usage_type=usage_type)
            
        except Exception as e:
            logger.error("Error sending usage limit exceeded notification", error=str(e), org_id=org_id)
    
    async def send_billing_notification(self, org_id: str, event_type: str, data: Dict[str, Any]):
        """Send billing-related notifications"""
        try:
            org = self.db.query(Organization).filter(Organization.id == org_id).first()
            if not org:
                return
            
            admin_users = self.db.query(User).filter(
                User.org_id == org_id,
                User.role.in_(["admin", "owner"])
            ).all()
            
            subject, message = self._get_billing_notification_content(event_type, org.name, data)
            
            for user in admin_users:
                await self._send_email(user.email, subject, message)
                await self._create_in_app_notification(
                    user.id,
                    f"billing_{event_type}",
                    subject,
                    data
                )
            
            logger.info("Sent billing notification", org_id=org_id, event_type=event_type)
            
        except Exception as e:
            logger.error("Error sending billing notification", error=str(e), org_id=org_id)
    
    async def send_monthly_usage_report(self, org_id: str, usage_summary: Dict[str, Any]):
        """Send monthly usage report"""
        try:
            org = self.db.query(Organization).filter(Organization.id == org_id).first()
            if not org:
                return
            
            admin_users = self.db.query(User).filter(
                User.org_id == org_id,
                User.role.in_(["admin", "owner"])
            ).all()
            
            subject = f"Monthly Usage Report - {org.name}"
            
            # Format usage data
            usage_lines = []
            for usage_type, amount in usage_summary["usage"].items():
                limit_key = f"{usage_type}_per_month"
                limit = usage_summary["limits"].get(limit_key, 0)
                percentage = usage_summary["percentage_used"].get(limit_key, 0)
                
                usage_lines.append(f"  • {usage_type.replace('_', ' ').title()}: {amount:,} / {limit:,} ({percentage:.1f}%)")
            
            message = f"""
            Dear {org.name} Administrator,
            
            Here's your monthly usage report for {usage_summary['period_start']} to {usage_summary['period_end']}:
            
            Plan: {usage_summary['plan'].title()}
            
            Usage Summary:
            {chr(10).join(usage_lines)}
            
            View detailed analytics: {settings.FRONTEND_URL}/billing
            
            Best regards,
            The LexiScan Team
            """
            
            for user in admin_users:
                await self._send_email(user.email, subject, message)
            
            logger.info("Sent monthly usage report", org_id=org_id)
            
        except Exception as e:
            logger.error("Error sending monthly usage report", error=str(e), org_id=org_id)
    
    async def _send_email(self, to_email: str, subject: str, message: str):
        """Send email notification (placeholder implementation)"""
        try:
            # This is a placeholder implementation
            # In production, you would integrate with:
            # - AWS SES
            # - SendGrid
            # - Mailgun
            # - Or another email service
            
            logger.info("Email notification sent", to=to_email, subject=subject)
            
            # TODO: Implement actual email sending
            # Example with AWS SES:
            # import boto3
            # ses = boto3.client('ses', region_name=settings.AWS_REGION)
            # ses.send_email(
            #     Source='noreply@lexiscan.ai',
            #     Destination={'ToAddresses': [to_email]},
            #     Message={
            #         'Subject': {'Data': subject},
            #         'Body': {'Text': {'Data': message}}
            #     }
            # )
            
        except Exception as e:
            logger.error("Error sending email", error=str(e), to=to_email)
    
    async def _create_in_app_notification(self, user_id: str, notification_type: str, title: str, data: Dict[str, Any]):
        """Create in-app notification (placeholder implementation)"""
        try:
            # This would typically store notifications in a database table
            # for display in the application UI
            
            notification = {
                "user_id": user_id,
                "type": notification_type,
                "title": title,
                "data": data,
                "created_at": datetime.utcnow().isoformat(),
                "read": False
            }
            
            logger.info("In-app notification created", notification=notification)
            
            # TODO: Implement actual in-app notification storage
            # This could be:
            # - Database table for notifications
            # - Redis for real-time notifications
            # - WebSocket push to connected clients
            
        except Exception as e:
            logger.error("Error creating in-app notification", error=str(e), user_id=user_id)
    
    def _get_billing_notification_content(self, event_type: str, org_name: str, data: Dict[str, Any]) -> tuple[str, str]:
        """Get subject and message content for billing notifications"""
        if event_type == "payment_succeeded":
            subject = "Payment Successful"
            message = f"""
            Dear {org_name} Administrator,
            
            Your payment has been processed successfully.
            
            Amount: ${data.get('amount_paid', 0) / 100:.2f}
            
            Thank you for your continued subscription to LexiScan.
            
            Best regards,
            The LexiScan Team
            """
        
        elif event_type == "payment_failed":
            subject = "Payment Failed - Action Required"
            message = f"""
            Dear {org_name} Administrator,
            
            We were unable to process your payment. Please update your payment method to avoid service interruption.
            
            Update payment method: {settings.FRONTEND_URL}/billing
            
            If you need assistance, please contact support: support@lexiscan.ai
            
            Best regards,
            The LexiScan Team
            """
        
        elif event_type == "subscription_canceled":
            subject = "Subscription Canceled"
            message = f"""
            Dear {org_name} Administrator,
            
            Your subscription has been canceled. Your account has been downgraded to the free plan.
            
            You can reactivate your subscription at any time: {settings.FRONTEND_URL}/billing
            
            Best regards,
            The LexiScan Team
            """
        
        else:
            subject = f"Billing Update - {event_type.replace('_', ' ').title()}"
            message = f"""
            Dear {org_name} Administrator,
            
            There has been an update to your billing information.
            
            Event: {event_type.replace('_', ' ').title()}
            
            View your billing details: {settings.FRONTEND_URL}/billing
            
            Best regards,
            The LexiScan Team
            """
        
        return subject, message


class UsageReportGenerator:
    """Generate usage reports and analytics"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def generate_organization_report(self, org_id: str, period_start: date, period_end: date) -> Dict[str, Any]:
        """Generate comprehensive usage report for organization"""
        try:
            from services.stripe_service import StripeService
            
            stripe_service = StripeService(self.db)
            usage_summary = await stripe_service.get_usage_summary(org_id, period_start, period_end)
            
            # Get organization details
            org = self.db.query(Organization).filter(Organization.id == org_id).first()
            subscription = self.db.query(Subscription).filter(Subscription.org_id == org_id).first()
            
            report = {
                "organization": {
                    "id": str(org.id),
                    "name": org.name,
                    "created_at": org.created_at.isoformat()
                },
                "subscription": {
                    "plan": subscription.plan if subscription else "free",
                    "status": subscription.status if subscription else "active",
                    "created_at": subscription.created_at.isoformat() if subscription else None
                },
                "period": {
                    "start": period_start.isoformat(),
                    "end": period_end.isoformat()
                },
                "usage_summary": usage_summary,
                "recommendations": self._generate_usage_recommendations(usage_summary),
                "cost_analysis": self._calculate_cost_analysis(usage_summary),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error("Error generating organization report", error=str(e), org_id=org_id)
            raise
    
    def _generate_usage_recommendations(self, usage_summary: Dict[str, Any]) -> List[str]:
        """Generate usage-based recommendations"""
        recommendations = []
        plan = usage_summary["plan"]
        
        # Analyze usage patterns
        high_usage_types = []
        low_usage_types = []
        
        for usage_type, percentage in usage_summary["percentage_used"].items():
            if percentage >= 80:
                high_usage_types.append(usage_type.replace("_per_month", ""))
            elif percentage < 30:
                low_usage_types.append(usage_type.replace("_per_month", ""))
        
        # Generate recommendations
        if len(high_usage_types) >= 2:
            if plan == "free":
                recommendations.append("Consider upgrading to Pro plan for higher limits and advanced AI features")
            elif plan == "pro":
                recommendations.append("Consider upgrading to Enterprise plan for unlimited usage and premium features")
        
        if len(low_usage_types) >= 2 and plan in ["pro", "enterprise"]:
            recommendations.append("You might save costs with a lower-tier plan based on your current usage patterns")
        
        if "pages" in high_usage_types:
            recommendations.append("Consider optimizing document processing by combining smaller documents")
        
        if "tokens" in high_usage_types:
            recommendations.append("Consider using more specific queries to reduce token consumption")
        
        return recommendations
    
    def _calculate_cost_analysis(self, usage_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate cost analysis and projections"""
        plan = usage_summary["plan"]
        
        # Plan costs (monthly)
        plan_costs = {
            "free": 0,
            "pro": 29,
            "enterprise": 199
        }
        
        current_cost = plan_costs.get(plan, 0)
        
        # Calculate potential overage costs (if applicable)
        overage_cost = 0
        for usage_type, amount in usage_summary["usage"].items():
            limit_key = f"{usage_type}_per_month"
            limit = usage_summary["limits"].get(limit_key, 0)
            
            if amount > limit:
                overage = amount - limit
                # Example overage pricing (would be configurable)
                if usage_type == "pages":
                    overage_cost += overage * 0.10  # $0.10 per page
                elif usage_type == "tokens":
                    overage_cost += overage * 0.001  # $0.001 per token
        
        return {
            "current_plan_cost": current_cost,
            "overage_cost": overage_cost,
            "total_cost": current_cost + overage_cost,
            "projected_monthly_cost": current_cost + overage_cost,
            "cost_per_usage": {
                "cost_per_page": current_cost / max(usage_summary["usage"].get("pages", 1), 1),
                "cost_per_token": current_cost / max(usage_summary["usage"].get("tokens", 1), 1)
            }
        }