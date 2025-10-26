"""
Rate limiting middleware and utilities using Redis backend
"""

import time
import json
import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import redis
from redis.exceptions import RedisError

from .config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiter using sliding window algorithm"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window: int,
        identifier: str = "default"
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed based on rate limit
        
        Args:
            key: Unique identifier for the rate limit (e.g., user_id, ip_address)
            limit: Maximum number of requests allowed
            window: Time window in seconds
            identifier: Additional identifier for different rate limit types
            
        Returns:
            Tuple of (is_allowed, metadata)
        """
        try:
            current_time = int(time.time())
            redis_key = f"rate_limit:{identifier}:{key}"
            
            # Use sliding window log algorithm
            pipe = self.redis.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(redis_key, 0, current_time - window)
            
            # Count current requests
            pipe.zcard(redis_key)
            
            # Add current request
            pipe.zadd(redis_key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(redis_key, window + 1)
            
            results = pipe.execute()
            current_requests = results[1]
            
            # Check if limit exceeded
            is_allowed = current_requests < limit
            
            # Calculate reset time
            reset_time = current_time + window
            
            metadata = {
                "limit": limit,
                "remaining": max(0, limit - current_requests - 1),
                "reset_time": reset_time,
                "retry_after": window if not is_allowed else None
            }
            
            return is_allowed, metadata
            
        except RedisError as e:
            logger.error(f"Redis error in rate limiter: {str(e)}")
            # Fail open - allow request if Redis is down
            return True, {"limit": limit, "remaining": limit - 1, "reset_time": current_time + window}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, app, redis_client: redis.Redis):
        super().__init__(app)
        self.rate_limiter = RateLimiter(redis_client)
        
        # Rate limit configurations
        self.rate_limits = {
            # Global rate limits per IP
            "global": {"limit": 1000, "window": 3600},  # 1000 requests per hour
            "auth": {"limit": 10, "window": 300},       # 10 auth attempts per 5 minutes
            "upload": {"limit": 50, "window": 3600},    # 50 uploads per hour
            "query": {"limit": 100, "window": 3600},    # 100 queries per hour
            "api": {"limit": 500, "window": 3600},      # 500 API calls per hour
        }
        
        # Path-based rate limit mapping
        self.path_mappings = {
            "/api/auth/": "auth",
            "/api/upload": "upload",
            "/api/rag/query": "query",
            "/api/documents/": "api",
            "/api/analysis/": "api",
        }
    
    def get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Priority: authenticated user > IP address
        if hasattr(request.state, 'user_id') and request.state.user_id:
            return f"user:{request.state.user_id}"
        
        # Get real IP from headers (considering proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"
    
    def get_rate_limit_type(self, request: Request) -> str:
        """Determine rate limit type based on request path"""
        path = request.url.path
        
        for path_prefix, limit_type in self.path_mappings.items():
            if path.startswith(path_prefix):
                return limit_type
        
        return "global"
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/health/ready", "/health/live"]:
            return await call_next(request)
        
        # Get client identifier and rate limit type
        client_id = self.get_client_identifier(request)
        limit_type = self.get_rate_limit_type(request)
        
        # Get rate limit configuration
        rate_config = self.rate_limits.get(limit_type, self.rate_limits["global"])
        
        # Check rate limit
        is_allowed, metadata = await self.rate_limiter.is_allowed(
            key=client_id,
            limit=rate_config["limit"],
            window=rate_config["window"],
            identifier=limit_type
        )
        
        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded",
                extra={
                    "client_id": client_id,
                    "limit_type": limit_type,
                    "path": request.url.path,
                    "method": request.method,
                    "metadata": metadata
                }
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": metadata["limit"],
                    "retry_after": metadata["retry_after"]
                },
                headers={
                    "X-RateLimit-Limit": str(metadata["limit"]),
                    "X-RateLimit-Remaining": str(metadata["remaining"]),
                    "X-RateLimit-Reset": str(metadata["reset_time"]),
                    "Retry-After": str(metadata["retry_after"]) if metadata["retry_after"] else "3600"
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
        response.headers["X-RateLimit-Remaining"] = str(metadata["remaining"])
        response.headers["X-RateLimit-Reset"] = str(metadata["reset_time"])
        
        return response


def get_redis_client() -> redis.Redis:
    """Get Redis client for rate limiting"""
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=settings.REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30
    )


# Dependency for manual rate limiting in endpoints
async def check_rate_limit(
    request: Request,
    limit_type: str = "api",
    custom_limit: Optional[int] = None,
    custom_window: Optional[int] = None
):
    """Manual rate limit check for specific endpoints"""
    redis_client = get_redis_client()
    rate_limiter = RateLimiter(redis_client)
    
    # Default rate limits
    rate_limits = {
        "api": {"limit": 500, "window": 3600},
        "upload": {"limit": 50, "window": 3600},
        "query": {"limit": 100, "window": 3600},
        "auth": {"limit": 10, "window": 300},
    }
    
    config = rate_limits.get(limit_type, rate_limits["api"])
    if custom_limit:
        config["limit"] = custom_limit
    if custom_window:
        config["window"] = custom_window
    
    # Get client identifier
    if hasattr(request.state, 'user_id') and request.state.user_id:
        client_id = f"user:{request.state.user_id}"
    else:
        client_ip = request.client.host if request.client else "unknown"
        client_id = f"ip:{client_ip}"
    
    is_allowed, metadata = await rate_limiter.is_allowed(
        key=client_id,
        limit=config["limit"],
        window=config["window"],
        identifier=limit_type
    )
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": metadata["limit"],
                "retry_after": metadata["retry_after"]
            }
        )
    
    return metadata