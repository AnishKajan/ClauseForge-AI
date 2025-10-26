"""
Feature Flag Management System for LexiScan

This module provides a centralized way to manage feature flags for gradual rollouts,
A/B testing, and safe deployment of new features.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import os
import redis
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.config import settings

logger = logging.getLogger(__name__)


class FeatureFlagType(str, Enum):
    """Types of feature flags"""
    BOOLEAN = "boolean"
    STRING = "string"
    NUMBER = "number"
    JSON = "json"


class RolloutStrategy(str, Enum):
    """Rollout strategies for feature flags"""
    ALL_USERS = "all_users"
    PERCENTAGE = "percentage"
    USER_LIST = "user_list"
    ORG_LIST = "org_list"
    GRADUAL = "gradual"


@dataclass
class FeatureFlag:
    """Feature flag configuration"""
    key: str
    name: str
    description: str
    flag_type: FeatureFlagType
    default_value: Any
    enabled: bool = True
    rollout_strategy: RolloutStrategy = RolloutStrategy.ALL_USERS
    rollout_percentage: float = 100.0
    target_users: List[str] = None
    target_orgs: List[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.target_users is None:
            self.target_users = []
        if self.target_orgs is None:
            self.target_orgs = []
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)


class FeatureFlagManager:
    """Manages feature flags with Redis caching and database persistence"""
    
    def __init__(self):
        self.redis_client = None
        self.cache_ttl = 300  # 5 minutes
        self.cache_prefix = "feature_flag:"
        
        # Initialize Redis if available
        try:
            if settings.REDIS_URL:
                self.redis_client = redis.from_url(settings.REDIS_URL)
                self.redis_client.ping()
                logger.info("Feature flags Redis cache initialized")
        except Exception as e:
            logger.warning(f"Redis not available for feature flags: {e}")
    
    def _get_cache_key(self, flag_key: str) -> str:
        """Generate cache key for feature flag"""
        return f"{self.cache_prefix}{flag_key}"
    
    def _get_user_cache_key(self, flag_key: str, user_id: str, org_id: str = None) -> str:
        """Generate user-specific cache key"""
        org_suffix = f":{org_id}" if org_id else ""
        return f"{self.cache_prefix}user:{user_id}{org_suffix}:{flag_key}"
    
    def _cache_get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        
        try:
            cached = self.redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        
        return None
    
    def _cache_set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in cache"""
        if not self.redis_client:
            return
        
        try:
            ttl = ttl or self.cache_ttl
            self.redis_client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    def _cache_delete(self, key: str) -> None:
        """Delete value from cache"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
    
    def _load_flags_from_config(self) -> Dict[str, FeatureFlag]:
        """Load feature flags from configuration file"""
        config_path = os.path.join(os.path.dirname(__file__), "..", "config", "feature_flags.json")
        
        if not os.path.exists(config_path):
            logger.info("No feature flags configuration file found")
            return {}
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            flags = {}
            for flag_data in config.get('flags', []):
                flag = FeatureFlag(**flag_data)
                flags[flag.key] = flag
            
            logger.info(f"Loaded {len(flags)} feature flags from configuration")
            return flags
        
        except Exception as e:
            logger.error(f"Error loading feature flags configuration: {e}")
            return {}
    
    def _is_user_in_rollout(self, flag: FeatureFlag, user_id: str, org_id: str = None) -> bool:
        """Check if user should receive the feature flag"""
        if not flag.enabled:
            return False
        
        # Check date range
        now = datetime.now(timezone.utc)
        if flag.start_date and now < flag.start_date:
            return False
        if flag.end_date and now > flag.end_date:
            return False
        
        # Apply rollout strategy
        if flag.rollout_strategy == RolloutStrategy.ALL_USERS:
            return True
        
        elif flag.rollout_strategy == RolloutStrategy.USER_LIST:
            return user_id in flag.target_users
        
        elif flag.rollout_strategy == RolloutStrategy.ORG_LIST:
            return org_id in flag.target_orgs if org_id else False
        
        elif flag.rollout_strategy == RolloutStrategy.PERCENTAGE:
            # Use consistent hash-based percentage rollout
            import hashlib
            hash_input = f"{flag.key}:{user_id}"
            hash_value = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)
            percentage = (hash_value % 100) + 1
            return percentage <= flag.rollout_percentage
        
        elif flag.rollout_strategy == RolloutStrategy.GRADUAL:
            # Gradual rollout based on user ID hash and time
            import hashlib
            hash_input = f"{flag.key}:{user_id}"
            hash_value = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)
            
            # Calculate rollout percentage based on time since start_date
            if flag.start_date:
                days_since_start = (now - flag.start_date).days
                # Increase rollout by 10% per day, max 100%
                current_percentage = min(100.0, days_since_start * 10)
            else:
                current_percentage = flag.rollout_percentage
            
            percentage = (hash_value % 100) + 1
            return percentage <= current_percentage
        
        return False
    
    def get_flag_value(self, flag_key: str, user_id: str, org_id: str = None, default: Any = None) -> Any:
        """Get feature flag value for a specific user"""
        # Check user-specific cache first
        cache_key = self._get_user_cache_key(flag_key, user_id, org_id)
        cached_value = self._cache_get(cache_key)
        if cached_value is not None:
            return cached_value
        
        # Load flags from configuration
        flags = self._load_flags_from_config()
        
        if flag_key not in flags:
            logger.warning(f"Feature flag '{flag_key}' not found")
            return default
        
        flag = flags[flag_key]
        
        # Check if user is in rollout
        if self._is_user_in_rollout(flag, user_id, org_id):
            value = flag.default_value
        else:
            # Return type-appropriate default
            if flag.flag_type == FeatureFlagType.BOOLEAN:
                value = False
            elif flag.flag_type == FeatureFlagType.STRING:
                value = ""
            elif flag.flag_type == FeatureFlagType.NUMBER:
                value = 0
            elif flag.flag_type == FeatureFlagType.JSON:
                value = {}
            else:
                value = default
        
        # Cache the result
        self._cache_set(cache_key, value, ttl=60)  # Shorter TTL for user-specific values
        
        return value
    
    def is_enabled(self, flag_key: str, user_id: str, org_id: str = None) -> bool:
        """Check if a boolean feature flag is enabled for a user"""
        return bool(self.get_flag_value(flag_key, user_id, org_id, default=False))
    
    def get_string_value(self, flag_key: str, user_id: str, org_id: str = None, default: str = "") -> str:
        """Get string value from feature flag"""
        return str(self.get_flag_value(flag_key, user_id, org_id, default=default))
    
    def get_number_value(self, flag_key: str, user_id: str, org_id: str = None, default: float = 0.0) -> float:
        """Get numeric value from feature flag"""
        value = self.get_flag_value(flag_key, user_id, org_id, default=default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def get_json_value(self, flag_key: str, user_id: str, org_id: str = None, default: Dict = None) -> Dict:
        """Get JSON value from feature flag"""
        if default is None:
            default = {}
        value = self.get_flag_value(flag_key, user_id, org_id, default=default)
        if isinstance(value, dict):
            return value
        return default
    
    def invalidate_cache(self, flag_key: str = None) -> None:
        """Invalidate feature flag cache"""
        if not self.redis_client:
            return
        
        try:
            if flag_key:
                # Invalidate specific flag
                pattern = f"{self.cache_prefix}*:{flag_key}"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            else:
                # Invalidate all feature flag cache
                pattern = f"{self.cache_prefix}*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            
            logger.info(f"Invalidated feature flag cache for: {flag_key or 'all flags'}")
        
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
    
    def get_all_flags_for_user(self, user_id: str, org_id: str = None) -> Dict[str, Any]:
        """Get all feature flag values for a user"""
        flags = self._load_flags_from_config()
        result = {}
        
        for flag_key, flag in flags.items():
            result[flag_key] = self.get_flag_value(flag_key, user_id, org_id)
        
        return result


# Global feature flag manager instance
feature_flags = FeatureFlagManager()


# Convenience functions
def is_feature_enabled(flag_key: str, user_id: str, org_id: str = None) -> bool:
    """Check if a feature is enabled for a user"""
    return feature_flags.is_enabled(flag_key, user_id, org_id)


def get_feature_value(flag_key: str, user_id: str, org_id: str = None, default: Any = None) -> Any:
    """Get feature flag value for a user"""
    return feature_flags.get_flag_value(flag_key, user_id, org_id, default)


def get_user_features(user_id: str, org_id: str = None) -> Dict[str, Any]:
    """Get all feature flags for a user"""
    return feature_flags.get_all_flags_for_user(user_id, org_id)