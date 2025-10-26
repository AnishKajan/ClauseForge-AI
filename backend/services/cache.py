"""
Redis-based caching service for RAG queries and rate limiting.
"""

import json
import hashlib
import logging
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import redis.asyncio as redis

from core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service."""
    
    def __init__(self):
        self.redis_client = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Redis connection."""
        if self._initialized:
            return
        
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            await self.redis_client.ping()
            self._initialized = True
            logger.info("Redis cache service initialized successfully")
            
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache: {e}")
            self.redis_client = None
            self._initialized = False
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self._initialized = False
    
    def _generate_cache_key(self, prefix: str, data: Dict[str, Any]) -> str:
        """Generate cache key from data."""
        # Create deterministic hash from data
        data_str = json.dumps(data, sort_keys=True)
        data_hash = hashlib.md5(data_str.encode()).hexdigest()
        return f"{prefix}:{data_hash}"
    
    async def get_rag_response(
        self,
        query: str,
        org_id: str,
        document_ids: Optional[list] = None,
        similarity_threshold: float = 0.7
    ) -> Optional[Dict[str, Any]]:
        """Get cached RAG response."""
        if not self._initialized:
            await self.initialize()
        
        if not self.redis_client:
            return None
        
        try:
            cache_data = {
                "query": query.lower().strip(),
                "org_id": org_id,
                "document_ids": sorted(document_ids) if document_ids else None,
                "similarity_threshold": similarity_threshold
            }
            
            cache_key = self._generate_cache_key("rag_response", cache_data)
            cached_response = await self.redis_client.get(cache_key)
            
            if cached_response:
                logger.info(f"Cache hit for RAG query: {cache_key}")
                return json.loads(cached_response)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting cached RAG response: {e}")
            return None
    
    async def set_rag_response(
        self,
        query: str,
        org_id: str,
        response_data: Dict[str, Any],
        document_ids: Optional[list] = None,
        similarity_threshold: float = 0.7,
        ttl_seconds: int = 3600
    ) -> bool:
        """Cache RAG response."""
        if not self._initialized:
            await self.initialize()
        
        if not self.redis_client:
            return False
        
        try:
            cache_data = {
                "query": query.lower().strip(),
                "org_id": org_id,
                "document_ids": sorted(document_ids) if document_ids else None,
                "similarity_threshold": similarity_threshold
            }
            
            cache_key = self._generate_cache_key("rag_response", cache_data)
            
            # Add cache metadata
            cached_data = {
                **response_data,
                "cached_at": datetime.utcnow().isoformat(),
                "cache_key": cache_key
            }
            
            await self.redis_client.setex(
                cache_key,
                ttl_seconds,
                json.dumps(cached_data, default=str)
            )
            
            logger.info(f"Cached RAG response: {cache_key}")
            return True
            
        except Exception as e:
            logger.warning(f"Error caching RAG response: {e}")
            return False
    
    async def check_rate_limit(
        self,
        user_id: str,
        limit: int = 10,
        window_seconds: int = 60,
        action: str = "query"
    ) -> tuple[bool, int]:
        """
        Check rate limit for user action.
        
        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        if not self._initialized:
            await self.initialize()
        
        if not self.redis_client:
            # Fallback to allowing request if Redis is unavailable
            return True, limit
        
        try:
            rate_limit_key = f"rate_limit:{action}:{user_id}"
            current_time = datetime.utcnow()
            window_start = current_time - timedelta(seconds=window_seconds)
            
            # Use Redis sorted set for sliding window rate limiting
            pipe = self.redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(
                rate_limit_key,
                0,
                window_start.timestamp()
            )
            
            # Count current requests
            pipe.zcard(rate_limit_key)
            
            # Add current request
            pipe.zadd(
                rate_limit_key,
                {str(current_time.timestamp()): current_time.timestamp()}
            )
            
            # Set expiration
            pipe.expire(rate_limit_key, window_seconds)
            
            results = await pipe.execute()
            current_count = results[1]  # Count after cleanup
            
            is_allowed = current_count < limit
            remaining = max(0, limit - current_count - 1)
            
            if not is_allowed:
                # Remove the request we just added since it's not allowed
                await self.redis_client.zrem(rate_limit_key, str(current_time.timestamp()))
                remaining = 0
            
            return is_allowed, remaining
            
        except Exception as e:
            logger.warning(f"Error checking rate limit: {e}")
            # Fallback to allowing request
            return True, limit
    
    async def get_user_usage(self, user_id: str, period: str = "daily") -> Dict[str, int]:
        """Get user usage statistics."""
        if not self._initialized:
            await self.initialize()
        
        if not self.redis_client:
            return {}
        
        try:
            usage_key = f"usage:{period}:{user_id}"
            usage_data = await self.redis_client.hgetall(usage_key)
            
            return {
                "queries": int(usage_data.get("queries", 0)),
                "tokens": int(usage_data.get("tokens", 0)),
                "documents_processed": int(usage_data.get("documents_processed", 0))
            }
            
        except Exception as e:
            logger.warning(f"Error getting user usage: {e}")
            return {}
    
    async def increment_usage(
        self,
        user_id: str,
        metric: str,
        amount: int = 1,
        period: str = "daily"
    ) -> bool:
        """Increment usage counter."""
        if not self._initialized:
            await self.initialize()
        
        if not self.redis_client:
            return False
        
        try:
            usage_key = f"usage:{period}:{user_id}"
            
            # Increment counter
            await self.redis_client.hincrby(usage_key, metric, amount)
            
            # Set expiration based on period
            if period == "daily":
                expire_seconds = 86400  # 24 hours
            elif period == "monthly":
                expire_seconds = 2592000  # 30 days
            else:
                expire_seconds = 3600  # 1 hour default
            
            await self.redis_client.expire(usage_key, expire_seconds)
            
            return True
            
        except Exception as e:
            logger.warning(f"Error incrementing usage: {e}")
            return False
    
    async def invalidate_document_cache(self, org_id: str, document_id: str) -> bool:
        """Invalidate cached responses for a specific document."""
        if not self._initialized:
            await self.initialize()
        
        if not self.redis_client:
            return False
        
        try:
            # Find all cache keys that might contain this document
            pattern = f"rag_response:*"
            keys = await self.redis_client.keys(pattern)
            
            deleted_count = 0
            for key in keys:
                try:
                    cached_data = await self.redis_client.get(key)
                    if cached_data:
                        data = json.loads(cached_data)
                        # Check if this cache entry involves the document
                        if (data.get("org_id") == org_id and 
                            document_id in (data.get("document_ids") or [])):
                            await self.redis_client.delete(key)
                            deleted_count += 1
                except Exception:
                    continue
            
            logger.info(f"Invalidated {deleted_count} cache entries for document {document_id}")
            return True
            
        except Exception as e:
            logger.warning(f"Error invalidating document cache: {e}")
            return False


# Global cache service instance
cache_service = CacheService()


async def get_cache_service() -> CacheService:
    """Get cache service instance."""
    if not cache_service._initialized:
        await cache_service.initialize()
    return cache_service