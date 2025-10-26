"""
Role-Based Access Control (RBAC) system
"""

from typing import List, Dict, Any, Optional, Callable
from functools import wraps
from fastapi import HTTPException, status, Depends, Request
from enum import Enum

from core.auth_dependencies import get_current_user
from models.database import User


class Role(str, Enum):
    """User roles with hierarchy"""
    VIEWER = "viewer"
    REVIEWER = "reviewer"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class Permission(str, Enum):
    """System permissions"""
    # Document permissions
    DOCUMENT_READ = "document:read"
    DOCUMENT_UPLOAD = "document:upload"
    DOCUMENT_DELETE = "document:delete"
    DOCUMENT_SHARE = "document:share"
    
    # Analysis permissions
    ANALYSIS_READ = "analysis:read"
    ANALYSIS_CREATE = "analysis:create"
    ANALYSIS_DELETE = "analysis:delete"
    
    # RAG permissions
    RAG_QUERY = "rag:query"
    RAG_ADVANCED = "rag:advanced"
    
    # Organization permissions
    ORG_READ = "org:read"
    ORG_MANAGE = "org:manage"
    ORG_USERS = "org:users"
    ORG_SETTINGS = "org:settings"
    
    # User permissions
    USER_READ = "user:read"
    USER_MANAGE = "user:manage"
    USER_DELETE = "user:delete"
    
    # Billing permissions
    BILLING_READ = "billing:read"
    BILLING_MANAGE = "billing:manage"
    
    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_ORGS = "admin:orgs"
    ADMIN_SYSTEM = "admin:system"


# Base permissions for each role
_VIEWER_PERMISSIONS = [
    Permission.DOCUMENT_READ,
    Permission.ANALYSIS_READ,
    Permission.RAG_QUERY,
    Permission.USER_READ,
    Permission.BILLING_READ,
]

_REVIEWER_PERMISSIONS = [
    Permission.DOCUMENT_UPLOAD,
    Permission.DOCUMENT_SHARE,
    Permission.ANALYSIS_CREATE,
    Permission.RAG_ADVANCED,
]

_ADMIN_PERMISSIONS = [
    Permission.DOCUMENT_DELETE,
    Permission.ANALYSIS_DELETE,
    Permission.ORG_READ,
    Permission.ORG_MANAGE,
    Permission.ORG_USERS,
    Permission.ORG_SETTINGS,
    Permission.USER_MANAGE,
    Permission.BILLING_MANAGE,
]

_SUPER_ADMIN_PERMISSIONS = [
    Permission.USER_DELETE,
    Permission.ADMIN_USERS,
    Permission.ADMIN_ORGS,
    Permission.ADMIN_SYSTEM,
]

# Role-Permission mapping with inheritance
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.VIEWER: _VIEWER_PERMISSIONS,
    Role.REVIEWER: _VIEWER_PERMISSIONS + _REVIEWER_PERMISSIONS,
    Role.ADMIN: _VIEWER_PERMISSIONS + _REVIEWER_PERMISSIONS + _ADMIN_PERMISSIONS,
    Role.SUPER_ADMIN: _VIEWER_PERMISSIONS + _REVIEWER_PERMISSIONS + _ADMIN_PERMISSIONS + _SUPER_ADMIN_PERMISSIONS,
}


class RBACService:
    """Role-Based Access Control service"""
    
    @staticmethod
    def get_role_permissions(role: str) -> List[Permission]:
        """Get permissions for a role"""
        try:
            role_enum = Role(role)
            return ROLE_PERMISSIONS.get(role_enum, [])
        except ValueError:
            return []
    
    @staticmethod
    def has_permission(user_role: str, permission: Permission) -> bool:
        """Check if a role has a specific permission"""
        role_permissions = RBACService.get_role_permissions(user_role)
        return permission in role_permissions
    
    @staticmethod
    def has_any_permission(user_role: str, permissions: List[Permission]) -> bool:
        """Check if a role has any of the specified permissions"""
        role_permissions = RBACService.get_role_permissions(user_role)
        return any(perm in role_permissions for perm in permissions)
    
    @staticmethod
    def has_all_permissions(user_role: str, permissions: List[Permission]) -> bool:
        """Check if a role has all of the specified permissions"""
        role_permissions = RBACService.get_role_permissions(user_role)
        return all(perm in role_permissions for perm in permissions)
    
    @staticmethod
    def get_role_hierarchy_level(role: str) -> int:
        """Get the hierarchy level of a role (higher number = more permissions)"""
        hierarchy = {
            Role.VIEWER: 1,
            Role.REVIEWER: 2,
            Role.ADMIN: 3,
            Role.SUPER_ADMIN: 4,
        }
        try:
            role_enum = Role(role)
            return hierarchy.get(role_enum, 0)
        except ValueError:
            return 0
    
    @staticmethod
    def has_minimum_role(user_role: str, minimum_role: str) -> bool:
        """Check if user has at least the minimum role level"""
        user_level = RBACService.get_role_hierarchy_level(user_role)
        min_level = RBACService.get_role_hierarchy_level(minimum_role)
        return user_level >= min_level


# Dependency factories for FastAPI
def require_permission(permission: Permission):
    """Dependency factory to require a specific permission"""
    
    async def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if not RBACService.has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission.value}"
            )
        return current_user
    
    return permission_checker


def require_any_permission(permissions: List[Permission]):
    """Dependency factory to require any of the specified permissions"""
    
    async def permissions_checker(current_user: User = Depends(get_current_user)) -> User:
        if not RBACService.has_any_permission(current_user.role, permissions):
            permission_names = [p.value for p in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required any of: {', '.join(permission_names)}"
            )
        return current_user
    
    return permissions_checker


def require_all_permissions(permissions: List[Permission]):
    """Dependency factory to require all of the specified permissions"""
    
    async def permissions_checker(current_user: User = Depends(get_current_user)) -> User:
        if not RBACService.has_all_permissions(current_user.role, permissions):
            permission_names = [p.value for p in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required all of: {', '.join(permission_names)}"
            )
        return current_user
    
    return permissions_checker


def require_minimum_role(minimum_role: Role):
    """Dependency factory to require a minimum role level"""
    
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not RBACService.has_minimum_role(current_user.role, minimum_role.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role level. Required minimum: {minimum_role.value}"
            )
        return current_user
    
    return role_checker


def require_org_membership(allow_cross_org_access: bool = False):
    """Dependency factory to verify organization membership"""
    
    async def org_checker(
        request: Request,
        current_user: User = Depends(get_current_user)
    ) -> User:
        # Get org_id from request (could be from path, query, or body)
        requested_org_id = None
        
        # Try to get from path parameters
        if hasattr(request, 'path_params') and 'org_id' in request.path_params:
            requested_org_id = request.path_params['org_id']
        
        # Try to get from query parameters
        if not requested_org_id:
            requested_org_id = request.query_params.get('org_id')
        
        # Try to get from request state (set by middleware)
        if not requested_org_id:
            requested_org_id = getattr(request.state, 'org_id', None)
        
        # If no org_id specified, use user's org
        if not requested_org_id:
            requested_org_id = str(current_user.org_id)
        
        # Check if user belongs to the requested organization
        if str(current_user.org_id) != requested_org_id:
            if not allow_cross_org_access or not RBACService.has_minimum_role(current_user.role, Role.SUPER_ADMIN.value):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: User does not belong to this organization"
                )
        
        return current_user
    
    return org_checker


# Decorator for route protection
def protected_route(
    permissions: Optional[List[Permission]] = None,
    minimum_role: Optional[Role] = None,
    require_org_membership: bool = True
):
    """Decorator to protect routes with RBAC"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This decorator is mainly for documentation
            # The actual protection is handled by FastAPI dependencies
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# Common permission dependencies
require_document_read = require_permission(Permission.DOCUMENT_READ)
require_document_upload = require_permission(Permission.DOCUMENT_UPLOAD)
require_document_delete = require_permission(Permission.DOCUMENT_DELETE)

require_analysis_read = require_permission(Permission.ANALYSIS_READ)
require_analysis_create = require_permission(Permission.ANALYSIS_CREATE)

require_rag_query = require_permission(Permission.RAG_QUERY)
require_rag_advanced = require_permission(Permission.RAG_ADVANCED)

require_org_manage = require_permission(Permission.ORG_MANAGE)
require_user_manage = require_permission(Permission.USER_MANAGE)

require_admin_role = require_minimum_role(Role.ADMIN)
require_reviewer_role = require_minimum_role(Role.REVIEWER)

# Organization membership checker
require_org_access = require_org_membership(allow_cross_org_access=False)
require_org_access_or_admin = require_org_membership(allow_cross_org_access=True)


# Simple permission check function for services
def check_permission(user_role: str, resource: str, action: str) -> bool:
    """Simple permission check for services"""
    permission_map = {
        ("organization", "read"): Permission.ORG_READ,
        ("organization", "update"): Permission.ORG_MANAGE,
        ("user", "create"): Permission.USER_MANAGE,
        ("user", "read"): Permission.USER_READ,
        ("user", "update"): Permission.USER_MANAGE,
        ("user", "delete"): Permission.USER_DELETE,
        ("document", "read"): Permission.DOCUMENT_READ,
        ("document", "share"): Permission.DOCUMENT_SHARE,
        ("audit", "read"): Permission.ORG_READ,
    }
    
    permission = permission_map.get((resource, action))
    if not permission:
        return False
    
    return RBACService.has_permission(user_role, permission)