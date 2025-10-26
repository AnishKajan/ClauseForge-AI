"""
Authentication service with JWT token management
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.hash import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
import uuid
import secrets

from core.config import settings
from models.database import User, Organization
from repositories.user import UserRepository
from repositories.audit_log import AuditLogRepository


class AuthService:
    """Authentication service for JWT token management and user authentication"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.algorithm = "HS256"
        self.secret_key = settings.SECRET_KEY
        
        # Token expiration settings
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
        
        # In-memory store for refresh tokens (in production, use Redis)
        self._refresh_tokens: Dict[str, Dict[str, Any]] = {}
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, user_id: str, org_id: str) -> str:
        """Create a refresh token and store it"""
        token_id = str(uuid.uuid4())
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        # Store refresh token metadata
        self._refresh_tokens[token_id] = {
            "user_id": user_id,
            "org_id": org_id,
            "expires_at": expire,
            "created_at": datetime.utcnow()
        }
        
        # Create JWT refresh token
        to_encode = {
            "sub": user_id,
            "org_id": org_id,
            "token_id": token_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected {token_type}"
                )
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )
            
            return payload
            
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not validate credentials: {str(e)}"
            )
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """Generate new access token using refresh token"""
        # Verify refresh token
        payload = self.verify_token(refresh_token, "refresh")
        token_id = payload.get("token_id")
        user_id = payload.get("sub")
        org_id = payload.get("org_id")
        
        # Check if refresh token exists and is valid
        if not token_id or token_id not in self._refresh_tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        token_data = self._refresh_tokens[token_id]
        if token_data["expires_at"] < datetime.utcnow():
            # Clean up expired token
            del self._refresh_tokens[token_id]
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )
        
        # Create new access token
        access_token = self.create_access_token({
            "sub": user_id,
            "org_id": org_id,
            "email": payload.get("email"),
            "role": payload.get("role")
        })
        
        # Create new refresh token (rotation)
        new_refresh_token = self.create_refresh_token(user_id, org_id)
        
        # Remove old refresh token
        del self._refresh_tokens[token_id]
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token
        }
    
    def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token"""
        try:
            payload = self.verify_token(refresh_token, "refresh")
            token_id = payload.get("token_id")
            
            if token_id and token_id in self._refresh_tokens:
                del self._refresh_tokens[token_id]
                return True
                
        except HTTPException:
            pass  # Token already invalid
        
        return False
    
    async def authenticate_user(
        self, 
        email: str, 
        password: str, 
        db: AsyncSession
    ) -> Optional[User]:
        """Authenticate user with email and password"""
        user_repo = UserRepository(db)
        
        # Get user by email
        user = await user_repo.get_by_email(email)
        if not user:
            return None
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        # Verify password
        if not user.password_hash or not self.verify_password(password, user.password_hash):
            return None
        
        return user
    
    async def register_user(
        self,
        email: str,
        password: str,
        org_id: str,
        db: AsyncSession,
        role: str = "viewer"
    ) -> User:
        """Register a new user"""
        user_repo = UserRepository(db)
        audit_repo = AuditLogRepository(db)
        
        # Check if user already exists
        existing_user = await user_repo.get_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Hash password
        password_hash = self.hash_password(password)
        
        # Create user
        user_data = {
            "email": email,
            "password_hash": password_hash,
            "org_id": org_id,
            "role": role,
            "provider": "email",
            "is_active": True,
            "email_verified": False
        }
        
        user = await user_repo.create(user_data)
        
        # Log user registration
        await audit_repo.create({
            "org_id": org_id,
            "user_id": str(user.id),
            "action": "user_registered",
            "resource_type": "user",
            "resource_id": str(user.id),
            "payload_json": {"email": email, "role": role}
        })
        
        return user
    
    async def create_token_pair(self, user: User) -> Dict[str, Any]:
        """Create access and refresh token pair for user"""
        # Create access token
        access_token_data = {
            "sub": str(user.id),
            "org_id": str(user.org_id),
            "email": user.email,
            "role": user.role
        }
        access_token = self.create_access_token(access_token_data)
        
        # Create refresh token
        refresh_token = self.create_refresh_token(str(user.id), str(user.org_id))
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60
        }
    
    def generate_secure_password(self, length: int = 12) -> str:
        """Generate a secure random password"""
        return secrets.token_urlsafe(length)


# Global auth service instance
auth_service = AuthService()