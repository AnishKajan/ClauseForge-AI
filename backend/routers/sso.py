"""
SSO (SAML/OIDC) authentication router
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import uuid

from core.dependencies import get_db
from core.auth_dependencies import get_current_user, get_current_org
from services.sso import sso_service
from services.auth import auth_service
from models.database import User


router = APIRouter(prefix="/sso", tags=["sso"])


class SSOConfigRequest(BaseModel):
    """SSO configuration request model"""
    type: str = Field(..., description="SSO provider type (oidc or saml)")
    name: str = Field(..., description="Provider name")
    
    # OIDC fields
    client_id: Optional[str] = Field(None, description="OIDC client ID")
    client_secret: Optional[str] = Field(None, description="OIDC client secret")
    discovery_url: Optional[str] = Field(None, description="OIDC discovery URL")
    issuer: Optional[str] = Field(None, description="OIDC issuer")
    
    # SAML fields
    entity_id: Optional[str] = Field(None, description="SAML entity ID")
    sso_url: Optional[str] = Field(None, description="SAML SSO URL")
    sls_url: Optional[str] = Field(None, description="SAML SLS URL")
    x509_cert: Optional[str] = Field(None, description="SAML X.509 certificate")
    name_id_format: Optional[str] = Field(None, description="SAML NameID format")
    
    # Role mapping
    role_mapping: Optional[Dict[str, str]] = Field(default_factory=dict, description="Role mapping configuration")
    default_role: str = Field("viewer", description="Default role for new users")
    role_claim: str = Field("role", description="Claim name for user role")
    groups_claim: str = Field("groups", description="Claim name for user groups")


class SSOConfigResponse(BaseModel):
    """SSO configuration response model"""
    success: bool
    message: str
    metadata: Optional[Dict[str, Any]] = None


class SSOLoginResponse(BaseModel):
    """SSO login response model"""
    authorization_url: str
    state: str


@router.post("/configure", response_model=SSOConfigResponse)
async def configure_sso(
    config: SSOConfigRequest,
    current_user: User = Depends(get_current_user),
    current_org: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
):
    """Configure SSO for organization (admin only)"""
    
    # Check if user has admin role
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can configure SSO"
        )
    
    # Validate configuration based on type
    if config.type == "oidc":
        if not config.client_id or not config.client_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OIDC configuration requires client_id and client_secret"
            )
        if not config.discovery_url and not config.issuer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OIDC configuration requires discovery_url or issuer"
            )
    
    elif config.type == "saml":
        if not config.entity_id or not config.sso_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SAML configuration requires entity_id and sso_url"
            )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported SSO type. Must be 'oidc' or 'saml'"
        )
    
    # Configure SSO
    success = await sso_service.configure_sso_provider(
        current_org, 
        config.dict(exclude_none=True), 
        db
    )
    
    if success:
        # Get metadata for response
        try:
            metadata = await sso_service.get_sso_metadata(current_org, db)
        except Exception:
            metadata = None
        
        return SSOConfigResponse(
            success=True,
            message="SSO configured successfully",
            metadata=metadata
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure SSO"
        )


@router.get("/config")
async def get_sso_config(
    current_user: User = Depends(get_current_user),
    current_org: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
):
    """Get SSO configuration for organization"""
    
    # Check if user has admin role
    if current_user.role not in ["admin", "reviewer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view SSO configuration"
        )
    
    sso_config = await sso_service.get_organization_sso_config(current_org, db)
    
    if not sso_config:
        return {"configured": False}
    
    # Remove sensitive information
    safe_config = sso_config.copy()
    if "client_secret" in safe_config:
        safe_config["client_secret"] = "***"
    if "private_key" in safe_config:
        safe_config["private_key"] = "***"
    
    return {
        "configured": True,
        "config": safe_config
    }


@router.get("/metadata/{org_id}")
async def get_sso_metadata(
    org_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get SSO metadata for organization (public endpoint for IdP configuration)"""
    
    try:
        uuid.UUID(org_id)  # Validate org_id format
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID"
        )
    
    metadata = await sso_service.get_sso_metadata(org_id, db)
    
    if metadata.get("type") == "saml":
        return Response(
            content=metadata["metadata"],
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename=metadata-{org_id}.xml"}
        )
    else:
        return metadata


@router.get("/login/{org_id}", response_model=SSOLoginResponse)
async def initiate_sso_login(
    org_id: str,
    redirect_uri: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Initiate SSO login for organization"""
    
    try:
        uuid.UUID(org_id)  # Validate org_id format
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID"
        )
    
    # Default redirect URI
    if not redirect_uri:
        redirect_uri = f"/sso/{org_id}/callback"
    
    authorization_url = await sso_service.initiate_sso_login(org_id, redirect_uri, db)
    
    # Extract state from URL for response
    from urllib.parse import urlparse, parse_qs
    parsed_url = urlparse(authorization_url)
    query_params = parse_qs(parsed_url.query)
    state = query_params.get("state", [""])[0] or query_params.get("RelayState", [""])[0]
    
    return SSOLoginResponse(
        authorization_url=authorization_url,
        state=state
    )


@router.get("/callback/{org_id}")
async def handle_sso_callback(
    org_id: str,
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Handle SSO callback (OIDC)"""
    
    try:
        uuid.UUID(org_id)  # Validate org_id format
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID"
        )
    
    # Check for errors
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SSO error: {error}. {error_description or ''}"
        )
    
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required parameters"
        )
    
    # Handle callback
    redirect_uri = str(request.url).split("?")[0]  # Remove query parameters
    
    result = await sso_service.handle_sso_callback(
        org_id, code, state, redirect_uri, db
    )
    
    user = result["user"]
    
    # Create JWT tokens
    tokens = await auth_service.create_token_pair(user)
    
    # Redirect to frontend with tokens
    frontend_url = f"/auth/sso-success?access_token={tokens['access_token']}&refresh_token={tokens['refresh_token']}"
    
    return RedirectResponse(url=frontend_url)


@router.post("/acs/{org_id}")
async def handle_saml_acs(
    org_id: str,
    request: Request,
    SAMLResponse: str = Form(...),
    RelayState: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle SAML Assertion Consumer Service (ACS)"""
    
    try:
        uuid.UUID(org_id)  # Validate org_id format
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID"
        )
    
    if not SAMLResponse:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing SAML response"
        )
    
    # Handle SAML response
    redirect_uri = str(request.url).split("?")[0]  # Remove query parameters
    
    result = await sso_service.handle_sso_callback(
        org_id, SAMLResponse, RelayState or "", redirect_uri, db
    )
    
    user = result["user"]
    
    # Create JWT tokens
    tokens = await auth_service.create_token_pair(user)
    
    # Return HTML page that posts tokens to parent window
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SSO Success</title>
    </head>
    <body>
        <script>
            // Post tokens to parent window
            if (window.opener) {{
                window.opener.postMessage({{
                    type: 'SSO_SUCCESS',
                    access_token: '{tokens["access_token"]}',
                    refresh_token: '{tokens["refresh_token"]}'
                }}, '*');
                window.close();
            }} else {{
                // Fallback: redirect to frontend
                window.location.href = '/auth/sso-success?access_token={tokens["access_token"]}&refresh_token={tokens["refresh_token"]}';
            }}
        </script>
        <p>Authentication successful. This window should close automatically.</p>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@router.delete("/config")
async def disable_sso(
    current_user: User = Depends(get_current_user),
    current_org: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db)
):
    """Disable SSO for organization"""
    
    # Check if user has admin role
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can disable SSO"
        )
    
    # Remove SSO configuration
    success = await sso_service.configure_sso_provider(current_org, None, db)
    
    if success:
        return {"success": True, "message": "SSO disabled successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable SSO"
        )


@router.get("/test/{org_id}")
async def test_sso_config(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Test SSO configuration (admin only)"""
    
    # Check if user has admin role
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can test SSO configuration"
        )
    
    try:
        uuid.UUID(org_id)  # Validate org_id format
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID"
        )
    
    # Check if SSO is configured
    sso_config = await sso_service.get_organization_sso_config(org_id, db)
    if not sso_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSO not configured for organization"
        )
    
    # Test provider connectivity
    provider = await sso_service.get_sso_provider(org_id, db)
    
    try:
        if hasattr(provider, 'discover_endpoints'):
            # Test OIDC discovery
            discovery_doc = await provider.discover_endpoints()
            return {
                "success": True,
                "provider_type": "oidc",
                "message": "OIDC discovery successful",
                "endpoints": {
                    "issuer": discovery_doc.get("issuer"),
                    "authorization_endpoint": discovery_doc.get("authorization_endpoint"),
                    "token_endpoint": discovery_doc.get("token_endpoint"),
                    "userinfo_endpoint": discovery_doc.get("userinfo_endpoint")
                }
            }
        else:
            # SAML provider
            return {
                "success": True,
                "provider_type": "saml",
                "message": "SAML configuration valid",
                "config": {
                    "entity_id": provider.entity_id,
                    "sso_url": provider.sso_url,
                    "name_id_format": provider.name_id_format
                }
            }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"SSO configuration test failed: {str(e)}"
        }