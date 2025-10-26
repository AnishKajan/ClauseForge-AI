"""
Admin endpoints for system administration
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
import logging

from core.database import get_db
from core.rbac import (
    require_admin_role,
    require_minimum_role,
    require_permission,
    require_org_access_or_admin,
    protected_route,
    Permission,
    Role
)
from models.database import User
from repositories.user import UserRepository
from repositories.organization import OrganizationRepository

logger = logging.getLogger(__name__)
router = APIRouter()


class UserAdminResponse(BaseModel):
    id: str
    email: str
    role: str
    org_id: str
    is_active: bool
    email_verified: bool
    provider: str
    last_login: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class OrganizationResponse(BaseModel):
    id: str
    name: str
    created_at: str
    user_count: Optional[int] = None

    class Config:
        from_attributes = True


class UpdateUserRoleRequest(BaseModel):
    role: str


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


@router.get("/users", response_model=List[UserAdminResponse])
@protected_route(permissions=[Permission.ADMIN_USERS])
async def list_all_users(
    skip: int = 0,
    limit: int = 100,
    org_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS)),
    _: User = Depends(require_org_access_or_admin)
):
    """List all users (super admin) or organization users (admin)"""
    user_repo = UserRepository(db)
    
    if current_user.role == "super_admin":
        # Super admin can see all users across organizations
        if org_id:
            users = await user_repo.get_by_org(org_id)
        else:
            # TODO: Implement get_all method in repository
            users = []
    else:
        # Regular admin can only see users in their organization
        users = await user_repo.get_by_org(current_user.org_id)
    
    return [UserAdminResponse.from_orm(user) for user in users]


@router.get("/users/{user_id}", response_model=UserAdminResponse)
@protected_route(permissions=[Permission.ADMIN_USERS])
async def get_user_details(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS)),
    _: User = Depends(require_org_access_or_admin)
):
    """Get detailed user information"""
    user_repo = UserRepository(db)
    user = await user_repo.get(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if admin can access this user
    if current_user.role != "super_admin" and str(user.org_id) != str(current_user.org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access user from different organization"
        )
    
    return UserAdminResponse.from_orm(user)


@router.put("/users/{user_id}/role")
@protected_route(permissions=[Permission.USER_MANAGE])
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USER_MANAGE)),
    _: User = Depends(require_org_access_or_admin)
):
    """Update user role"""
    user_repo = UserRepository(db)
    user = await user_repo.get(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if admin can modify this user
    if current_user.role != "super_admin" and str(user.org_id) != str(current_user.org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify user from different organization"
        )
    
    # Validate role
    valid_roles = ["viewer", "reviewer", "admin"]
    if current_user.role == "super_admin":
        valid_roles.append("super_admin")
    
    if request.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Valid roles: {', '.join(valid_roles)}"
        )
    
    # Prevent self-demotion for super admins
    if str(user.id) == str(current_user.id) and request.role != current_user.role:
        if current_user.role == "super_admin" and request.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote yourself from super admin role"
            )
    
    # Update user role
    updated_user = await user_repo.update(user_id, role=request.role)
    return UserAdminResponse.from_orm(updated_user)


@router.put("/users/{user_id}/status")
@protected_route(permissions=[Permission.USER_MANAGE])
async def update_user_status(
    user_id: str,
    request: UpdateUserStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USER_MANAGE)),
    _: User = Depends(require_org_access_or_admin)
):
    """Update user active status"""
    user_repo = UserRepository(db)
    user = await user_repo.get(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if admin can modify this user
    if current_user.role != "super_admin" and str(user.org_id) != str(current_user.org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify user from different organization"
        )
    
    # Prevent self-deactivation
    if str(user.id) == str(current_user.id) and not request.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    # Update user status
    updated_user = await user_repo.update(user_id, is_active=request.is_active)
    return UserAdminResponse.from_orm(updated_user)


@router.get("/organizations", response_model=List[OrganizationResponse])
@protected_route(permissions=[Permission.ADMIN_ORGS])
async def list_organizations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ADMIN_ORGS))
):
    """List all organizations (super admin only)"""
    org_repo = OrganizationRepository(db)
    
    # TODO: Implement get_all method in organization repository
    organizations = []
    
    return [OrganizationResponse.from_orm(org) for org in organizations]


@router.get("/system/health")
@protected_route(permissions=[Permission.ADMIN_SYSTEM])
async def system_health(
    current_user: User = Depends(require_permission(Permission.ADMIN_SYSTEM))
):
    """Get system health information (super admin only)"""
    # TODO: Implement system health checks
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
        "s3": "connected",
        "message": "All systems operational"
    }


@router.get("/system/stats")
@protected_route(permissions=[Permission.ADMIN_SYSTEM])
async def system_stats(
    current_user: User = Depends(require_permission(Permission.ADMIN_SYSTEM)),
    db: AsyncSession = Depends(get_db)
):
    """Get system statistics (super admin only)"""
    # TODO: Implement system statistics
    return {
        "total_users": 0,
        "total_organizations": 0,
        "total_documents": 0,
        "total_analyses": 0,
        "active_sessions": 0
    }