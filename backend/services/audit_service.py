"""
Comprehensive audit logging service for security and compliance
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.database import AuditLog
from repositories.audit_log import AuditLogRepository
from core.database import get_db

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Enumeration of audit actions"""
    # Authentication actions
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    
    # Document actions
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_DOWNLOAD = "document_download"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_VIEW = "document_view"
    DOCUMENT_SHARE = "document_share"
    
    # Analysis actions
    ANALYSIS_START = "analysis_start"
    ANALYSIS_COMPLETE = "analysis_complete"
    ANALYSIS_VIEW = "analysis_view"
    ANALYSIS_EXPORT = "analysis_export"
    
    # Query actions
    RAG_QUERY = "rag_query"
    SEARCH_QUERY = "search_query"
    
    # Administrative actions
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_ROLE_CHANGE = "user_role_change"
    
    # Organization actions
    ORG_CREATE = "org_create"
    ORG_UPDATE = "org_update"
    ORG_SETTINGS_CHANGE = "org_settings_change"
    
    # Billing actions
    SUBSCRIPTION_CREATE = "subscription_create"
    SUBSCRIPTION_UPDATE = "subscription_update"
    SUBSCRIPTION_CANCEL = "subscription_cancel"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    
    # Security actions
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    VIRUS_DETECTED = "virus_detected"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    
    # System actions
    SYSTEM_ERROR = "system_error"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"


class AuditLevel(str, Enum):
    """Audit log levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditService:
    """Service for creating and managing audit logs"""
    
    def __init__(self):
        self.audit_repo = AuditLogRepository()
    
    async def log_action(
        self,
        action: AuditAction,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        level: AuditLevel = AuditLevel.INFO,
        request: Optional[Request] = None
    ) -> Optional[str]:
        """
        Log an audit action
        
        Args:
            action: The action being performed
            user_id: ID of the user performing the action
            org_id: ID of the organization
            resource_type: Type of resource being acted upon
            resource_id: ID of the specific resource
            details: Additional details about the action
            ip_address: IP address of the client
            user_agent: User agent string
            level: Severity level of the audit log
            request: FastAPI request object (for extracting context)
            
        Returns:
            Audit log ID if successful, None otherwise
        """
        try:
            # Extract information from request if provided
            if request:
                if not ip_address:
                    ip_address = self._get_client_ip(request)
                if not user_agent:
                    user_agent = request.headers.get("User-Agent")
                if not user_id and hasattr(request.state, 'user_id'):
                    user_id = request.state.user_id
                if not org_id and hasattr(request.state, 'org_id'):
                    org_id = request.state.org_id
            
            # Prepare audit log data
            audit_data = {
                "action": action.value,
                "user_id": user_id,
                "org_id": org_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "level": level.value,
                "details": details or {},
                "timestamp": datetime.utcnow()
            }
            
            # Add request context if available
            if request:
                audit_data["details"].update({
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": dict(request.query_params),
                    "request_id": getattr(request.state, 'request_id', None)
                })
            
            # Store in database
            db = next(get_db())
            audit_log_id = await self.audit_repo.create_audit_log(db, audit_data)
            
            # Also log to application logger for immediate visibility
            log_message = f"AUDIT: {action.value}"
            if user_id:
                log_message += f" by user {user_id}"
            if resource_type and resource_id:
                log_message += f" on {resource_type} {resource_id}"
            
            logger_method = getattr(logger, level.value.lower(), logger.info)
            logger_method(log_message, extra=audit_data)
            
            return audit_log_id
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}", extra={
                "action": action.value,
                "user_id": user_id,
                "org_id": org_id,
                "error": str(e)
            })
            return None
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request"""
        # Check for forwarded headers (load balancer/proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else None
    
    async def log_authentication(
        self,
        action: AuditAction,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        success: bool = True,
        failure_reason: Optional[str] = None,
        request: Optional[Request] = None
    ):
        """Log authentication-related actions"""
        details = {
            "email": email,
            "success": success
        }
        
        if not success and failure_reason:
            details["failure_reason"] = failure_reason
        
        level = AuditLevel.INFO if success else AuditLevel.WARNING
        
        await self.log_action(
            action=action,
            user_id=user_id,
            resource_type="user",
            resource_id=user_id,
            details=details,
            level=level,
            request=request
        )
    
    async def log_document_action(
        self,
        action: AuditAction,
        document_id: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ):
        """Log document-related actions"""
        await self.log_action(
            action=action,
            user_id=user_id,
            org_id=org_id,
            resource_type="document",
            resource_id=document_id,
            details=details,
            request=request
        )
    
    async def log_security_event(
        self,
        action: AuditAction,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        level: AuditLevel = AuditLevel.WARNING,
        request: Optional[Request] = None
    ):
        """Log security-related events"""
        await self.log_action(
            action=action,
            user_id=user_id,
            org_id=org_id,
            resource_type="security",
            details=details,
            level=level,
            request=request
        )
    
    async def log_billing_event(
        self,
        action: AuditAction,
        org_id: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        request: Optional[Request] = None
    ):
        """Log billing-related events"""
        await self.log_action(
            action=action,
            user_id=user_id,
            org_id=org_id,
            resource_type="billing",
            details=details,
            request=request
        )
    
    async def get_audit_logs(
        self,
        db: Session,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """Retrieve audit logs with filtering"""
        return await self.audit_repo.get_audit_logs(
            db=db,
            org_id=org_id,
            user_id=user_id,
            action=action.value if action else None,
            resource_type=resource_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
    
    async def get_security_events(
        self,
        db: Session,
        org_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get security-related audit events"""
        security_actions = [
            AuditAction.RATE_LIMIT_EXCEEDED.value,
            AuditAction.UNAUTHORIZED_ACCESS.value,
            AuditAction.VIRUS_DETECTED.value,
            AuditAction.SUSPICIOUS_ACTIVITY.value,
            AuditAction.LOGIN_FAILED.value
        ]
        
        return await self.audit_repo.get_audit_logs_by_actions(
            db=db,
            actions=security_actions,
            org_id=org_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )


# Global audit service instance
audit_service = AuditService()


# Convenience functions for common audit operations
async def log_user_action(
    action: AuditAction,
    user_id: str,
    org_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
):
    """Log a user action"""
    await audit_service.log_action(
        action=action,
        user_id=user_id,
        org_id=org_id,
        details=details,
        request=request
    )


async def log_security_event(
    action: AuditAction,
    details: Dict[str, Any],
    user_id: Optional[str] = None,
    org_id: Optional[str] = None,
    level: AuditLevel = AuditLevel.WARNING,
    request: Optional[Request] = None
):
    """Log a security event"""
    await audit_service.log_security_event(
        action=action,
        details=details,
        user_id=user_id,
        org_id=org_id,
        level=level,
        request=request
    )