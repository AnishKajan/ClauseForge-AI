"""
Middleware for tracking API metrics and performance
"""

import time
import logging
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.telemetry import get_tracer, get_meter
from services.metrics_service import metrics_service
from core.logging_config import log_performance_metric

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking API metrics and performance"""
    
    def __init__(self, app):
        super().__init__(app)
        self.tracer = get_tracer()
        self.meter = get_meter()
    
    async def dispatch(self, request: Request, call_next):
        # Skip metrics for health checks and metrics endpoints
        if request.url.path in ["/health", "/health/ready", "/health/live", "/metrics"]:
            return await call_next(request)
        
        start_time = time.time()
        
        # Extract request information
        method = request.method
        path = request.url.path
        user_id = getattr(request.state, 'user_id', None)
        org_id = getattr(request.state, 'org_id', None)
        
        # Create span for tracing
        span_name = f"{method} {path}"
        
        try:
            if self.tracer:
                with self.tracer.start_as_current_span(span_name) as span:
                    # Add request attributes to span
                    span.set_attribute("http.method", method)
                    span.set_attribute("http.url", str(request.url))
                    span.set_attribute("http.scheme", request.url.scheme)
                    span.set_attribute("http.host", request.url.hostname or "unknown")
                    
                    if user_id:
                        span.set_attribute("user.id", user_id)
                    if org_id:
                        span.set_attribute("org.id", org_id)
                    
                    # Process request
                    response = await call_next(request)
                    
                    # Add response attributes
                    span.set_attribute("http.status_code", response.status_code)
                    
                    # Track metrics
                    await self._track_metrics(
                        request, response, start_time, user_id, org_id
                    )
                    
                    return response
            else:
                # No tracing available, just process request
                response = await call_next(request)
                await self._track_metrics(
                    request, response, start_time, user_id, org_id
                )
                return response
                
        except Exception as e:
            # Track error metrics
            response_time = time.time() - start_time
            
            # Track error in metrics
            metrics_service.track_error(
                error_type=type(e).__name__,
                error_message=str(e),
                user_id=user_id,
                org_id=org_id,
                endpoint=path
            )
            
            # Log performance even for errors
            log_performance_metric(
                metric_name="api_request_duration",
                value=response_time,
                endpoint=path,
                method=method,
                status="error",
                user_id=user_id,
                org_id=org_id
            )
            
            # Add error attributes to span if available
            if self.tracer:
                span = self.tracer.get_current_span()
                if span:
                    span.set_attribute("error", True)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
            
            raise
    
    async def _track_metrics(
        self,
        request: Request,
        response: Response,
        start_time: float,
        user_id: Optional[str],
        org_id: Optional[str]
    ):
        """Track API metrics"""
        try:
            response_time = time.time() - start_time
            
            # Track API request metrics
            metrics_service.track_api_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_time=response_time,
                user_id=user_id,
                org_id=org_id
            )
            
            # Log performance metric
            log_performance_metric(
                metric_name="api_request_duration",
                value=response_time,
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                user_id=user_id,
                org_id=org_id
            )
            
            # Add response time header
            response.headers["X-Response-Time"] = f"{response_time:.4f}"
            
        except Exception as e:
            logger.error(f"Failed to track API metrics: {str(e)}")


class BusinessMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking business-specific metrics"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        try:
            # Track specific business events based on endpoints
            path = request.url.path
            method = request.method
            status_code = response.status_code
            user_id = getattr(request.state, 'user_id', None)
            org_id = getattr(request.state, 'org_id', None)
            
            # Document upload events
            if path.startswith("/api/documents") and method == "POST" and status_code == 201:
                # This will be tracked in the actual upload service
                pass
            
            # RAG query events
            elif path.startswith("/api/rag/query") and method == "POST" and status_code == 200:
                # This will be tracked in the RAG service
                pass
            
            # Analysis events
            elif path.startswith("/api/analysis") and method == "POST" and status_code == 201:
                # This will be tracked in the analysis service
                pass
            
            # User registration events
            elif path.startswith("/api/auth/register") and method == "POST" and status_code == 201:
                if user_id and org_id:
                    metrics_service.track_user_registration(
                        user_id=user_id,
                        org_id=org_id,
                        provider="email"  # Default, can be enhanced
                    )
            
        except Exception as e:
            logger.error(f"Failed to track business metrics: {str(e)}")
        
        return response