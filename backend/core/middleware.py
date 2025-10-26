"""
FastAPI middleware configuration
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import logging
import uuid

from .config import settings
from .rate_limiting import RateLimitMiddleware, get_redis_client
from .metrics_middleware import MetricsMiddleware, BusinessMetricsMiddleware
from services.audit_service import audit_service, AuditAction, AuditLevel

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request logging and timing"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else None,
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "process_time": f"{process_time:.4f}s",
                }
            )
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}"
            
            return response
            
        except Exception as e:
            # Log errors and security events
            process_time = time.time() - start_time
            logger.error(
                f"Request failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "process_time": f"{process_time:.4f}s",
                }
            )
            
            # Log security events for certain error types
            if isinstance(e, HTTPException):
                if e.status_code == 401:
                    await audit_service.log_security_event(
                        action=AuditAction.UNAUTHORIZED_ACCESS,
                        details={
                            "path": request.url.path,
                            "method": request.method,
                            "status_code": e.status_code,
                            "error": str(e.detail)
                        },
                        level=AuditLevel.WARNING,
                        request=request
                    )
                elif e.status_code == 429:
                    await audit_service.log_security_event(
                        action=AuditAction.RATE_LIMIT_EXCEEDED,
                        details={
                            "path": request.url.path,
                            "method": request.method,
                            "error": str(e.detail)
                        },
                        level=AuditLevel.WARNING,
                        request=request
                    )
            
            raise


class OrganizationContextMiddleware(BaseHTTPMiddleware):
    """Middleware to set organization context for multi-tenancy"""
    
    async def dispatch(self, request: Request, call_next):
        # Extract org_id from JWT token or headers
        # Priority: JWT token > X-Org-ID header > default
        org_id = None
        user_id = None
        user_role = None
        
        # Try to get from Authorization header (JWT)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from services.auth import auth_service
                token = auth_header.split(" ")[1]
                payload = auth_service.verify_token(token, "access")
                
                org_id = payload.get("org_id")
                user_id = payload.get("sub")
                user_role = payload.get("role")
                
            except Exception as e:
                # Don't fail the request if token verification fails
                # Let the auth dependencies handle authentication errors
                logger.debug(f"Token verification failed in middleware: {str(e)}")
        
        # Fallback to custom header for development/testing
        if not org_id:
            org_id = request.headers.get("X-Org-ID")
        
        # Store in request state for use in dependencies
        if org_id:
            request.state.org_id = org_id
        if user_id:
            request.state.user_id = user_id
        if user_role:
            request.state.user_role = user_role
        
        response = await call_next(request)
        return response


def setup_middleware(app: FastAPI):
    """Setup all middleware for the FastAPI application"""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Trusted host middleware
    if settings.ENVIRONMENT == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*.lexiscan.ai", "lexiscan.ai"]
        )
    
    # Rate limiting middleware (before other middleware)
    try:
        redis_client = get_redis_client()
        app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
        logger.info("Rate limiting middleware enabled")
    except Exception as e:
        logger.warning(f"Failed to initialize rate limiting: {str(e)}")
    
    # Usage limit middleware (before auth middleware)
    from core.usage_middleware import UsageLimitMiddleware
    app.add_middleware(UsageLimitMiddleware)
    
    # Metrics middleware (before other custom middleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(BusinessMetricsMiddleware)
    
    # Custom middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(OrganizationContextMiddleware)