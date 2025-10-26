"""
Tests for Role-Based Access Control (RBAC) system
"""

import pytest
from core.rbac import RBACService, Role, Permission


class TestRBACService:
    """Test RBAC service functionality"""
    
    def test_get_role_permissions(self):
        """Test getting permissions for a role"""
        viewer_permissions = RBACService.get_role_permissions("viewer")
        assert Permission.DOCUMENT_READ in viewer_permissions
        assert Permission.DOCUMENT_DELETE not in viewer_permissions
        
        admin_permissions = RBACService.get_role_permissions("admin")
        assert Permission.DOCUMENT_READ in admin_permissions
        assert Permission.DOCUMENT_DELETE in admin_permissions
        assert Permission.ORG_MANAGE in admin_permissions
    
    def test_has_permission(self):
        """Test permission checking"""
        # Viewer should have read permission
        assert RBACService.has_permission("viewer", Permission.DOCUMENT_READ)
        assert not RBACService.has_permission("viewer", Permission.DOCUMENT_DELETE)
        
        # Admin should have both
        assert RBACService.has_permission("admin", Permission.DOCUMENT_READ)
        assert RBACService.has_permission("admin", Permission.DOCUMENT_DELETE)
    
    def test_role_hierarchy(self):
        """Test role hierarchy levels"""
        assert RBACService.get_role_hierarchy_level("viewer") == 1
        assert RBACService.get_role_hierarchy_level("reviewer") == 2
        assert RBACService.get_role_hierarchy_level("admin") == 3
        assert RBACService.get_role_hierarchy_level("super_admin") == 4
        assert RBACService.get_role_hierarchy_level("invalid") == 0
    
    def test_has_minimum_role(self):
        """Test minimum role checking"""
        # Admin should have minimum reviewer role
        assert RBACService.has_minimum_role("admin", "reviewer")
        assert RBACService.has_minimum_role("admin", "viewer")
        
        # Viewer should not have minimum admin role
        assert not RBACService.has_minimum_role("viewer", "admin")
        assert not RBACService.has_minimum_role("viewer", "reviewer")
        
        # Same role should pass
        assert RBACService.has_minimum_role("reviewer", "reviewer")
    
    def test_has_any_permission(self):
        """Test checking for any of multiple permissions"""
        permissions = [Permission.DOCUMENT_DELETE, Permission.ORG_MANAGE]
        
        # Viewer should not have any of these
        assert not RBACService.has_any_permission("viewer", permissions)
        
        # Admin should have both
        assert RBACService.has_any_permission("admin", permissions)
    
    def test_has_all_permissions(self):
        """Test checking for all of multiple permissions"""
        permissions = [Permission.DOCUMENT_READ, Permission.ANALYSIS_READ]
        
        # Viewer should have both
        assert RBACService.has_all_permissions("viewer", permissions)
        
        # Test with mixed permissions
        mixed_permissions = [Permission.DOCUMENT_READ, Permission.DOCUMENT_DELETE]
        assert not RBACService.has_all_permissions("viewer", mixed_permissions)
        assert RBACService.has_all_permissions("admin", mixed_permissions)


class TestRolePermissionMapping:
    """Test role-permission mappings"""
    
    def test_viewer_permissions(self):
        """Test viewer role permissions"""
        permissions = RBACService.get_role_permissions("viewer")
        
        # Should have read permissions
        assert Permission.DOCUMENT_READ in permissions
        assert Permission.ANALYSIS_READ in permissions
        assert Permission.RAG_QUERY in permissions
        assert Permission.USER_READ in permissions
        assert Permission.BILLING_READ in permissions
        
        # Should not have write/delete permissions
        assert Permission.DOCUMENT_UPLOAD not in permissions
        assert Permission.DOCUMENT_DELETE not in permissions
        assert Permission.ORG_MANAGE not in permissions
    
    def test_reviewer_permissions(self):
        """Test reviewer role permissions"""
        permissions = RBACService.get_role_permissions("reviewer")
        
        # Should inherit viewer permissions
        assert Permission.DOCUMENT_READ in permissions
        assert Permission.ANALYSIS_READ in permissions
        
        # Should have additional permissions
        assert Permission.DOCUMENT_UPLOAD in permissions
        assert Permission.DOCUMENT_SHARE in permissions
        assert Permission.ANALYSIS_CREATE in permissions
        assert Permission.RAG_ADVANCED in permissions
        
        # Should not have admin permissions
        assert Permission.DOCUMENT_DELETE not in permissions
        assert Permission.ORG_MANAGE not in permissions
    
    def test_admin_permissions(self):
        """Test admin role permissions"""
        permissions = RBACService.get_role_permissions("admin")
        
        # Should inherit reviewer permissions
        assert Permission.DOCUMENT_READ in permissions
        assert Permission.DOCUMENT_UPLOAD in permissions
        assert Permission.ANALYSIS_CREATE in permissions
        
        # Should have admin permissions
        assert Permission.DOCUMENT_DELETE in permissions
        assert Permission.ORG_MANAGE in permissions
        assert Permission.USER_MANAGE in permissions
        assert Permission.BILLING_MANAGE in permissions
        
        # Should not have super admin permissions
        assert Permission.ADMIN_SYSTEM not in permissions
    
    def test_super_admin_permissions(self):
        """Test super admin role permissions"""
        permissions = RBACService.get_role_permissions("super_admin")
        
        # Should inherit admin permissions
        assert Permission.DOCUMENT_DELETE in permissions
        assert Permission.ORG_MANAGE in permissions
        assert Permission.USER_MANAGE in permissions
        
        # Should have super admin permissions
        assert Permission.USER_DELETE in permissions
        assert Permission.ADMIN_USERS in permissions
        assert Permission.ADMIN_ORGS in permissions
        assert Permission.ADMIN_SYSTEM in permissions


if __name__ == "__main__":
    pytest.main([__file__])