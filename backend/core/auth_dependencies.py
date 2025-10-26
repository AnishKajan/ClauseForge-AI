"""
Authentication dependencies for FastAPI
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.auth import auth_service
from repositories.user import UserRepository
from models.database import User


security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    
    # Verify and decode token
    payload = auth_service.verify_token(credentials.credentials, "access")
    
    user_id = payload.get("sub")
    org_id = payload.get("org_id")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID"
        )
    
    # Get user from database
    user_repo = UserRepository(db)
    user = await user_repo.get(user_id, org_id=org_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )
    
    # Set organization context in request state
    request.state.org_id = org_id
    request.state.user_id = user_id
    request.state.user_role = user.role
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (alias for clarity)"""
    return current_user


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    
    if not credentials:
        return None
    
    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        return None


def require_role(required_role: str):
    """Dependency factory for role-based access control"""
    
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        """Check if user has required role"""
        
        # Define role hierarchy
        role_hierarchy = {
            "viewer": 0,
            "reviewer": 1,
            "admin": 2,
            "super_admin": 3
        }
        
        user_role_level = role_hierarchy.get(current_user.role, -1)
        required_role_level = role_hierarchy.get(required_role, 999)
        
        if user_role_level < required_role_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        
        return current_user
    
    return role_checker


def require_roles(allowed_roles: list[str]):
    """Dependency factory for multiple allowed roles"""
    
    async def roles_checker(current_user: User = Depends(get_current_user)) -> User:
        """Check if user has one of the allowed roles"""
        
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Allowed roles: {', '.join(allowed_roles)}"
            )
        
        return current_user
    
    return roles_checker


async def get_current_org_id(request: Request) -> str:
    """Get current organization ID from request state"""
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context not available"
        )
    return org_id


async def verify_org_membership(
    org_id: str,
    current_user: User = Depends(get_current_user)
) -> bool:
    """Verify user belongs to the specified organization"""
    if str(current_user.org_id) != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: User does not belong to this organization"
        )
    return True


# Common role dependencies
require_admin = require_role("admin")
require_reviewer = require_role("reviewer")
require_viewer = require_role("viewer")

# Multiple role dependencies
require_admin_or_reviewer = require_roles(["admin", "reviewer"])
require_any_role = require_roles(["viewer", "reviewer", "admin", "super_admin"])