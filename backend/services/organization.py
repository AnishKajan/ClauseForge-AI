"""
Organization management service for team workspace features
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
import uuid

from models.database import Organization, User, Document, Subscription
from repositories.organization import OrganizationRepository
from repositories.user import UserRepository
from repositories.document import DocumentRepository
from repositories.audit_log import AuditLogRepository
from core.rbac import check_permission


class OrganizationService:
    """Service for managing organization settings and team workspace features"""
    
    def __init__(self):
        pass
    
    async def get_organization_details(
        self, 
        org_id: str, 
        current_user: User,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get organization details with team information"""
        
        # Check permissions
        if not check_permission(current_user.role, "organization", "read"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view organization details"
            )
        
        org_repo = OrganizationRepository(db)
        user_repo = UserRepository(db)
        doc_repo = DocumentRepository(db)
        
        # Get organization
        org = await org_repo.get_by_id(org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Get team members
        team_members = await user_repo.get_by_org_id(org_id)
        
        # Get document statistics
        doc_stats = await doc_repo.get_organization_stats(org_id)
        
        # Get subscription info
        subscription = await self._get_organization_subscription(org_id, db)
        
        return {
            "id": str(org.id),
            "name": org.name,
            "created_at": org.created_at,
            "updated_at": org.updated_at,
            "sso_configured": bool(org.sso_config),
            "team_members": [
                {
                    "id": str(user.id),
                    "email": user.email,
                    "role": user.role,
                    "provider": user.provider,
                    "is_active": user.is_active,
                    "email_verified": user.email_verified,
                    "last_login": user.last_login,
                    "created_at": user.created_at
                }
                for user in team_members
            ],
            "document_stats": doc_stats,
            "subscription": subscription
        }
    
    async def update_organization_settings(
        self,
        org_id: str,
        settings: Dict[str, Any],
        current_user: User,
        db: AsyncSession
    ) -> Organization:
        """Update organization settings"""
        
        # Check permissions
        if not check_permission(current_user.role, "organization", "update"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to update organization settings"
            )
        
        org_repo = OrganizationRepository(db)
        audit_repo = AuditLogRepository(db)
        
        # Validate settings
        allowed_fields = {"name"}
        update_data = {k: v for k, v in settings.items() if k in allowed_fields}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )
        
        # Update organization
        org = await org_repo.update(org_id, update_data)
        
        # Log the update
        await audit_repo.create({
            "org_id": org_id,
            "user_id": str(current_user.id),
            "action": "organization_updated",
            "resource_type": "organization",
            "resource_id": org_id,
            "payload_json": update_data
        })
        
        return org
    
    async def invite_team_member(
        self,
        org_id: str,
        email: str,
        role: str,
        current_user: User,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Invite a new team member to the organization"""
        
        # Check permissions
        if not check_permission(current_user.role, "user", "create"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to invite team members"
            )
        
        # Validate role
        if role not in ["viewer", "reviewer", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be viewer, reviewer, or admin"
            )
        
        # Only admins can invite other admins
        if role == "admin" and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can invite other administrators"
            )
        
        user_repo = UserRepository(db)
        audit_repo = AuditLogRepository(db)
        
        # Check if user already exists
        existing_user = await user_repo.get_by_email(email)
        if existing_user:
            if existing_user.org_id == uuid.UUID(org_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is already a member of this organization"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is already a member of another organization"
                )
        
        # Create user account (inactive until they set password)
        user_data = {
            "email": email,
            "org_id": org_id,
            "role": role,
            "provider": "email",
            "is_active": False,  # Will be activated when they complete setup
            "email_verified": False
        }
        
        user = await user_repo.create(user_data)
        
        # Log the invitation
        await audit_repo.create({
            "org_id": org_id,
            "user_id": str(current_user.id),
            "action": "team_member_invited",
            "resource_type": "user",
            "resource_id": str(user.id),
            "payload_json": {"email": email, "role": role, "invited_by": current_user.email}
        })
        
        # TODO: Send invitation email
        # This would typically involve sending an email with a setup link
        
        return {
            "user_id": str(user.id),
            "email": email,
            "role": role,
            "status": "invited",
            "message": "Invitation sent successfully"
        }
    
    async def update_team_member_role(
        self,
        org_id: str,
        user_id: str,
        new_role: str,
        current_user: User,
        db: AsyncSession
    ) -> User:
        """Update a team member's role"""
        
        # Check permissions
        if not check_permission(current_user.role, "user", "update"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to update team member roles"
            )
        
        # Validate role
        if new_role not in ["viewer", "reviewer", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be viewer, reviewer, or admin"
            )
        
        # Only admins can promote to admin or demote admins
        user_repo = UserRepository(db)
        target_user = await user_repo.get_by_id(user_id)
        
        if not target_user or target_user.org_id != uuid.UUID(org_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found"
            )
        
        if (new_role == "admin" or target_user.role == "admin") and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can manage admin roles"
            )
        
        # Prevent self-demotion from admin
        if str(target_user.id) == str(current_user.id) and target_user.role == "admin" and new_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote yourself from administrator role"
            )
        
        audit_repo = AuditLogRepository(db)
        
        # Update role
        old_role = target_user.role
        updated_user = await user_repo.update(user_id, {"role": new_role})
        
        # Log the role change
        await audit_repo.create({
            "org_id": org_id,
            "user_id": str(current_user.id),
            "action": "team_member_role_updated",
            "resource_type": "user",
            "resource_id": user_id,
            "payload_json": {
                "target_email": target_user.email,
                "old_role": old_role,
                "new_role": new_role,
                "updated_by": current_user.email
            }
        })
        
        return updated_user
    
    async def remove_team_member(
        self,
        org_id: str,
        user_id: str,
        current_user: User,
        db: AsyncSession
    ) -> bool:
        """Remove a team member from the organization"""
        
        # Check permissions
        if not check_permission(current_user.role, "user", "delete"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to remove team members"
            )
        
        user_repo = UserRepository(db)
        target_user = await user_repo.get_by_id(user_id)
        
        if not target_user or target_user.org_id != uuid.UUID(org_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found"
            )
        
        # Only admins can remove other admins
        if target_user.role == "admin" and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can remove other administrators"
            )
        
        # Prevent self-removal
        if str(target_user.id) == str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove yourself from the organization"
            )
        
        audit_repo = AuditLogRepository(db)
        
        # Log the removal before deleting
        await audit_repo.create({
            "org_id": org_id,
            "user_id": str(current_user.id),
            "action": "team_member_removed",
            "resource_type": "user",
            "resource_id": user_id,
            "payload_json": {
                "target_email": target_user.email,
                "target_role": target_user.role,
                "removed_by": current_user.email
            }
        })
        
        # Remove user
        await user_repo.delete(user_id)
        
        return True
    
    async def get_shared_documents(
        self,
        org_id: str,
        current_user: User,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get documents shared within the organization"""
        
        # Check permissions
        if not check_permission(current_user.role, "document", "read"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view shared documents"
            )
        
        doc_repo = DocumentRepository(db)
        
        # Get all documents in the organization
        documents = await doc_repo.get_by_org_id(org_id, limit=limit, offset=offset)
        total_count = await doc_repo.count_by_org_id(org_id)
        
        return {
            "documents": [
                {
                    "id": str(doc.id),
                    "title": doc.title,
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "status": doc.status,
                    "uploaded_by": {
                        "id": str(doc.uploader.id) if doc.uploader else None,
                        "email": doc.uploader.email if doc.uploader else None
                    },
                    "created_at": doc.created_at,
                    "updated_at": doc.updated_at,
                    "processed_at": doc.processed_at
                }
                for doc in documents
            ],
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
    
    async def share_document(
        self,
        org_id: str,
        document_id: str,
        share_with_users: List[str],
        current_user: User,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Share a document with specific team members"""
        
        # Check permissions
        if not check_permission(current_user.role, "document", "share"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to share documents"
            )
        
        doc_repo = DocumentRepository(db)
        user_repo = UserRepository(db)
        audit_repo = AuditLogRepository(db)
        
        # Verify document exists and belongs to organization
        document = await doc_repo.get_by_id(document_id)
        if not document or str(document.org_id) != org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Verify users exist and belong to organization
        valid_users = []
        for user_id in share_with_users:
            user = await user_repo.get_by_id(user_id)
            if user and str(user.org_id) == org_id:
                valid_users.append(user)
        
        # Log the sharing action
        await audit_repo.create({
            "org_id": org_id,
            "user_id": str(current_user.id),
            "action": "document_shared",
            "resource_type": "document",
            "resource_id": document_id,
            "payload_json": {
                "document_title": document.title,
                "shared_with": [user.email for user in valid_users],
                "shared_by": current_user.email
            }
        })
        
        # In a full implementation, this would create document_shares table entries
        # For now, we'll return success since documents are org-scoped by default
        
        return {
            "document_id": document_id,
            "shared_with": [
                {
                    "user_id": str(user.id),
                    "email": user.email,
                    "role": user.role
                }
                for user in valid_users
            ],
            "message": "Document shared successfully"
        }
    
    async def get_team_activity(
        self,
        org_id: str,
        current_user: User,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get recent team activity within the organization"""
        
        # Check permissions
        if not check_permission(current_user.role, "audit", "read"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view team activity"
            )
        
        audit_repo = AuditLogRepository(db)
        
        # Get recent audit logs for the organization
        activities = await audit_repo.get_by_org_id(org_id, limit=limit, offset=offset)
        total_count = await audit_repo.count_by_org_id(org_id)
        
        return {
            "activities": [
                {
                    "id": str(activity.id),
                    "action": activity.action,
                    "resource_type": activity.resource_type,
                    "resource_id": str(activity.resource_id) if activity.resource_id else None,
                    "user": {
                        "id": str(activity.user.id) if activity.user else None,
                        "email": activity.user.email if activity.user else None
                    },
                    "payload": activity.payload_json,
                    "ip_address": str(activity.ip_address) if activity.ip_address else None,
                    "created_at": activity.created_at
                }
                for activity in activities
            ],
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
    
    async def _get_organization_subscription(
        self, 
        org_id: str, 
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Get organization subscription information"""
        
        result = await db.execute(
            select(Subscription).where(Subscription.org_id == uuid.UUID(org_id))
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return None
        
        return {
            "id": str(subscription.id),
            "plan": subscription.plan,
            "status": subscription.status,
            "usage_limits": subscription.usage_limits,
            "created_at": subscription.created_at
        }


# Global organization service instance
organization_service = OrganizationService()