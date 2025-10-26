"""
Organization management router for team workspace features
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, EmailStr
import uuid

from core.dependencies import get_db
from core.auth_dependencies import get_current_user, get_current_org
from services.organization import organization_service
from models.database import User


router = APIRouter(prefix="/organization", tags=["organization"])


class OrganizationUpdateRequest(BaseModel):
    """Organization update request model"""
    name: Optional[str] = Field(None, description="Organization name")


class TeamMemberInviteRequest(BaseModel):
    """Team member invitation request model"""
    email: EmailStr = Field(..., description="Email address of the user to invite")
    role: str = Field(..., description="Role to assign (viewer, reviewer, admin)")


class TeamMemberRoleUpdateRequest(BaseModel):
    """Team member role update request model"""
    role: str = Field(..., description="New role (viewer, reviewer, admin)")


class DocumentShareRequest(BaseModel):
    """Document sharing request model"""
    user_ids: List[str] = Field(..., description="List of user IDs to share with")


class OrganizationResponse(BaseModel):
    """Organization details response model"""
    id: str
    name: str
    created_at: str
    updated_at: str
    sso_configured: bool
    team_members: List[Dict[str, Any]]
    document_stats: Dict[str, Any]
    subscription: Optional[Dict[str, Any]]


class TeamMemberResponse(BaseModel):
    """Team member response model"""
    user_id: str
    email: str
    role: str
    status: str
    message: str


class SharedDocumentsResponse(BaseModel):
    """Shared documents response model"""
    documents: List[Dict[str, Any]]
    total_count: int
    limit: int
    offset: int


class TeamActivityResponse(BaseModel):
    """Team activity response model"""
    activities: List[Dict[str, Any]]
    total_count: int
    limit: int
    offset: int


@router.get("/details", response_model=OrganizationResponse)
async def get_organization_details(
    current_user: User = Depends(get_current_user),
    current_org: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
):
    """Get organization details with team information"""
    
    return await organization_service.get_organization_details(
        current_org, current_user, db
    )


@router.put("/settings")
async def update_organization_settings(
    settings: OrganizationUpdateRequest,
    current_user: User = Depends(get_current_user),
    current_org: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
):
    """Update organization settings"""
    
    org = await organization_service.update_organization_settings(
        current_org, settings.dict(exclude_none=True), current_user, db
    )
    
    return {
        "success": True,
        "message": "Organization settings updated successfully",
        "organization": {
            "id": str(org.id),
            "name": org.name,
            "updated_at": org.updated_at
        }
    }


@router.post("/team/invite", response_model=TeamMemberResponse)
async def invite_team_member(
    invite_request: TeamMemberInviteRequest,
    current_user: User = Depends(get_current_user),
    current_org: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
):
    """Invite a new team member to the organization"""
    
    return await organization_service.invite_team_member(
        current_org, invite_request.email, invite_request.role, current_user, db
    )


@router.put("/team/{user_id}/role")
async def update_team_member_role(
    user_id: str,
    role_update: TeamMemberRoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    current_org: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
):
    """Update a team member's role"""
    
    # Validate user_id format
    try:
        uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    updated_user = await organization_service.update_team_member_role(
        current_org, user_id, role_update.role, current_user, db
    )
    
    return {
        "success": True,
        "message": "Team member role updated successfully",
        "user": {
            "id": str(updated_user.id),
            "email": updated_user.email,
            "role": updated_user.role
        }
    }


@router.delete("/team/{user_id}")
async def remove_team_member(
    user_id: str,
    current_user: User = Depends(get_current_user),
    current_org: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
):
    """Remove a team member from the organization"""
    
    # Validate user_id format
    try:
        uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    success = await organization_service.remove_team_member(
        current_org, user_id, current_user, db
    )
    
    if success:
        return {
            "success": True,
            "message": "Team member removed successfully"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove team member"
        )


@router.get("/documents/shared", response_model=SharedDocumentsResponse)
async def get_shared_documents(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    current_org: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
):
    """Get documents shared within the organization"""
    
    return await organization_service.get_shared_documents(
        current_org, current_user, db, limit, offset
    )


@router.post("/documents/{document_id}/share")
async def share_document(
    document_id: str,
    share_request: DocumentShareRequest,
    current_user: User = Depends(get_current_user),
    current_org: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
):
    """Share a document with specific team members"""
    
    # Validate document_id format
    try:
        uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )
    
    # Validate user_ids format
    for user_id in share_request.user_ids:
        try:
            uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user ID format: {user_id}"
            )
    
    return await organization_service.share_document(
        current_org, document_id, share_request.user_ids, current_user, db
    )


@router.get("/activity", response_model=TeamActivityResponse)
async def get_team_activity(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    current_org: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
):
    """Get recent team activity within the organization"""
    
    return await organization_service.get_team_activity(
        current_org, current_user, db, limit, offset
    )


@router.get("/team")
async def get_team_members(
    current_user: User = Depends(get_current_user),
    current_org: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
):
    """Get list of team members"""
    
    org_details = await organization_service.get_organization_details(
        current_org, current_user, db
    )
    
    return {
        "team_members": org_details["team_members"],
        "total_count": len(org_details["team_members"])
    }


@router.get("/stats")
async def get_organization_stats(
    current_user: User = Depends(get_current_user),
    current_org: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
):
    """Get organization statistics"""
    
    org_details = await organization_service.get_organization_details(
        current_org, current_user, db
    )
    
    return {
        "team_size": len(org_details["team_members"]),
        "document_stats": org_details["document_stats"],
        "subscription": org_details["subscription"],
        "sso_configured": org_details["sso_configured"]
    }