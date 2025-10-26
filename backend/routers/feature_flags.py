"""
Feature Flags API Router

Provides endpoints for managing and querying feature flags.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import logging

from backend.core.auth_dependencies import get_current_user, require_role
from backend.core.feature_flags import feature_flags, FeatureFlag, FeatureFlagType, RolloutStrategy
from backend.models.database import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feature-flags", tags=["feature-flags"])


class FeatureFlagResponse(BaseModel):
    """Response model for feature flag"""
    key: str
    name: str
    description: str
    flag_type: FeatureFlagType
    value: Any
    enabled: bool


class UserFeaturesResponse(BaseModel):
    """Response model for user's feature flags"""
    user_id: str
    org_id: Optional[str]
    features: Dict[str, Any]


class FeatureFlagUpdateRequest(BaseModel):
    """Request model for updating feature flags"""
    enabled: Optional[bool] = None
    rollout_percentage: Optional[float] = None
    target_users: Optional[List[str]] = None
    target_orgs: Optional[List[str]] = None


@router.get("/user", response_model=UserFeaturesResponse)
async def get_user_features(
    current_user: User = Depends(get_current_user)
):
    """Get all feature flags for the current user"""
    try:
        features = feature_flags.get_all_flags_for_user(
            user_id=str(current_user.id),
            org_id=str(current_user.org_id) if current_user.org_id else None
        )
        
        return UserFeaturesResponse(
            user_id=str(current_user.id),
            org_id=str(current_user.org_id) if current_user.org_id else None,
            features=features
        )
    
    except Exception as e:
        logger.error(f"Error getting user features: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feature flags"
        )


@router.get("/user/{flag_key}")
async def get_user_feature(
    flag_key: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific feature flag value for the current user"""
    try:
        value = feature_flags.get_flag_value(
            flag_key=flag_key,
            user_id=str(current_user.id),
            org_id=str(current_user.org_id) if current_user.org_id else None
        )
        
        return {
            "key": flag_key,
            "value": value,
            "user_id": str(current_user.id),
            "org_id": str(current_user.org_id) if current_user.org_id else None
        }
    
    except Exception as e:
        logger.error(f"Error getting feature flag {flag_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve feature flag: {flag_key}"
        )


@router.get("/check/{flag_key}")
async def check_feature_enabled(
    flag_key: str,
    current_user: User = Depends(get_current_user)
):
    """Check if a boolean feature flag is enabled for the current user"""
    try:
        enabled = feature_flags.is_enabled(
            flag_key=flag_key,
            user_id=str(current_user.id),
            org_id=str(current_user.org_id) if current_user.org_id else None
        )
        
        return {
            "key": flag_key,
            "enabled": enabled,
            "user_id": str(current_user.id),
            "org_id": str(current_user.org_id) if current_user.org_id else None
        }
    
    except Exception as e:
        logger.error(f"Error checking feature flag {flag_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check feature flag: {flag_key}"
        )


# Admin endpoints (require admin role)
@router.get("/admin/all", response_model=List[Dict[str, Any]])
async def get_all_flags(
    current_user: User = Depends(require_role("admin"))
):
    """Get all feature flags configuration (admin only)"""
    try:
        flags = feature_flags._load_flags_from_config()
        
        result = []
        for flag_key, flag in flags.items():
            result.append({
                "key": flag.key,
                "name": flag.name,
                "description": flag.description,
                "flag_type": flag.flag_type,
                "default_value": flag.default_value,
                "enabled": flag.enabled,
                "rollout_strategy": flag.rollout_strategy,
                "rollout_percentage": flag.rollout_percentage,
                "target_users": flag.target_users,
                "target_orgs": flag.target_orgs,
                "created_at": flag.created_at.isoformat() if flag.created_at else None,
                "updated_at": flag.updated_at.isoformat() if flag.updated_at else None
            })
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting all flags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feature flags"
        )


@router.post("/admin/invalidate-cache")
async def invalidate_feature_cache(
    flag_key: Optional[str] = None,
    current_user: User = Depends(require_role("admin"))
):
    """Invalidate feature flag cache (admin only)"""
    try:
        feature_flags.invalidate_cache(flag_key)
        
        return {
            "message": f"Cache invalidated for: {flag_key or 'all flags'}",
            "flag_key": flag_key
        }
    
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invalidate cache"
        )


@router.get("/admin/user/{user_id}")
async def get_user_features_admin(
    user_id: str,
    org_id: Optional[str] = None,
    current_user: User = Depends(require_role("admin"))
):
    """Get feature flags for a specific user (admin only)"""
    try:
        features = feature_flags.get_all_flags_for_user(
            user_id=user_id,
            org_id=org_id
        )
        
        return UserFeaturesResponse(
            user_id=user_id,
            org_id=org_id,
            features=features
        )
    
    except Exception as e:
        logger.error(f"Error getting user features for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user feature flags"
        )


@router.get("/admin/stats")
async def get_feature_flag_stats(
    current_user: User = Depends(require_role("admin"))
):
    """Get feature flag usage statistics (admin only)"""
    try:
        flags = feature_flags._load_flags_from_config()
        
        stats = {
            "total_flags": len(flags),
            "enabled_flags": sum(1 for flag in flags.values() if flag.enabled),
            "disabled_flags": sum(1 for flag in flags.values() if not flag.enabled),
            "rollout_strategies": {},
            "flag_types": {}
        }
        
        # Count by rollout strategy
        for flag in flags.values():
            strategy = flag.rollout_strategy
            stats["rollout_strategies"][strategy] = stats["rollout_strategies"].get(strategy, 0) + 1
        
        # Count by flag type
        for flag in flags.values():
            flag_type = flag.flag_type
            stats["flag_types"][flag_type] = stats["flag_types"].get(flag_type, 0) + 1
        
        return stats
    
    except Exception as e:
        logger.error(f"Error getting feature flag stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feature flag statistics"
        )