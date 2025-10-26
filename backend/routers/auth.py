"""
Authentication and authorization endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

from core.database import get_db
from core.config import settings
from core.auth_dependencies import get_current_user, get_optional_current_user
from core.rbac import require_user_manage, require_org_access
from services.auth import auth_service
from repositories.user import UserRepository
from repositories.audit_log import AuditLogRepository
from models.database import User

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    org_id: str
    role: Optional[str] = "viewer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
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


class MessageResponse(BaseModel):
    message: str


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """User login endpoint"""
    try:
        # Authenticate user
        user = await auth_service.authenticate_user(
            email=request.email,
            password=request.password,
            db=db
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Update last login
        user_repo = UserRepository(db)
        await user_repo.update_last_login(user.id, str(user.org_id))
        
        # Create token pair
        tokens = await auth_service.create_token_pair(user)
        
        # Log successful login
        audit_repo = AuditLogRepository(db)
        await audit_repo.create({
            "org_id": str(user.org_id),
            "user_id": str(user.id),
            "action": "user_login",
            "resource_type": "user",
            "resource_id": str(user.id),
            "payload_json": {"email": user.email, "provider": user.provider}
        })
        
        logger.info(f"User {user.email} logged in successfully")
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/register", response_model=UserResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """User registration endpoint"""
    try:
        # Register new user
        user = await auth_service.register_user(
            email=request.email,
            password=request.password,
            org_id=request.org_id,
            role=request.role,
            db=db
        )
        
        logger.info(f"User {user.email} registered successfully")
        return UserResponse.from_orm(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    try:
        # Refresh tokens
        tokens = auth_service.refresh_access_token(request.refresh_token)
        
        # Add expires_in and token_type
        tokens.update({
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        })
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse.from_orm(current_user)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """User logout endpoint"""
    try:
        # Try to extract refresh token from request body if provided
        refresh_token = None
        try:
            body = await request.json()
            refresh_token = body.get("refresh_token")
        except:
            pass  # No body or invalid JSON
        
        # Revoke refresh token if provided
        if refresh_token:
            auth_service.revoke_refresh_token(refresh_token)
        
        # Log logout
        audit_repo = AuditLogRepository(db)
        await audit_repo.create({
            "org_id": str(current_user.org_id),
            "user_id": str(current_user.id),
            "action": "user_logout",
            "resource_type": "user",
            "resource_id": str(current_user.id),
            "payload_json": {"email": current_user.email}
        })
        
        logger.info(f"User {current_user.email} logged out")
        return MessageResponse(message="Logged out successfully")
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        # Don't fail logout even if audit logging fails
        return MessageResponse(message="Logged out successfully")


@router.post("/verify-token")
async def verify_token(
    current_user: User = Depends(get_optional_current_user)
):
    """Verify if the provided token is valid"""
    if current_user:
        return {
            "valid": True,
            "user": UserResponse.from_orm(current_user)
        }
    else:
        return {"valid": False}