"""
SSO (SAML/OIDC) authentication service for enterprise integration
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import base64
import xml.etree.ElementTree as ET
from urllib.parse import urlencode, parse_qs, urlparse
import httpx
from jose import jwt, JWTError
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
import uuid

from core.config import settings
from models.database import Organization, User
from repositories.organization import OrganizationRepository
from repositories.user import UserRepository
from repositories.audit_log import AuditLogRepository


class SSOProvider:
    """Base class for SSO providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider_type = config.get("type")
        self.provider_name = config.get("name", "Unknown")
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate SSO token and return user claims"""
        raise NotImplementedError
    
    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Get authorization URL for SSO flow"""
        raise NotImplementedError
    
    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        raise NotImplementedError


class OIDCProvider(SSOProvider):
    """OpenID Connect provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.discovery_url = config.get("discovery_url")
        self.issuer = config.get("issuer")
        self.jwks_uri = config.get("jwks_uri")
        self.authorization_endpoint = config.get("authorization_endpoint")
        self.token_endpoint = config.get("token_endpoint")
        self.userinfo_endpoint = config.get("userinfo_endpoint")
        
        # Cache for JWKS keys
        self._jwks_cache = {}
        self._jwks_cache_expiry = None
    
    async def discover_endpoints(self) -> Dict[str, Any]:
        """Discover OIDC endpoints from discovery URL"""
        if not self.discovery_url:
            raise ValueError("Discovery URL not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.discovery_url)
            response.raise_for_status()
            discovery_doc = response.json()
        
        # Update configuration with discovered endpoints
        self.issuer = discovery_doc.get("issuer", self.issuer)
        self.authorization_endpoint = discovery_doc.get("authorization_endpoint")
        self.token_endpoint = discovery_doc.get("token_endpoint")
        self.userinfo_endpoint = discovery_doc.get("userinfo_endpoint")
        self.jwks_uri = discovery_doc.get("jwks_uri")
        
        return discovery_doc
    
    async def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set for token validation"""
        if not self.jwks_uri:
            await self.discover_endpoints()
        
        # Check cache
        if (self._jwks_cache and self._jwks_cache_expiry and 
            datetime.utcnow() < self._jwks_cache_expiry):
            return self._jwks_cache
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.jwks_uri)
            response.raise_for_status()
            jwks = response.json()
        
        # Cache for 1 hour
        self._jwks_cache = jwks
        self._jwks_cache_expiry = datetime.utcnow() + timedelta(hours=1)
        
        return jwks
    
    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Get OIDC authorization URL"""
        if not self.authorization_endpoint:
            await self.discover_endpoints()
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid email profile",
            "state": state,
            "prompt": "consent"
        }
        
        return f"{self.authorization_endpoint}?{urlencode(params)}"
    
    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        if not self.token_endpoint:
            await self.discover_endpoints()
        
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate OIDC ID token"""
        try:
            # Get JWKS for validation
            jwks = await self.get_jwks()
            
            # Decode token header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            
            # Find matching key
            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwk
                    break
            
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to find matching key for token"
                )
            
            # Validate token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer
            )
            
            return payload
            
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from userinfo endpoint"""
        if not self.userinfo_endpoint:
            await self.discover_endpoints()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()


class SAMLProvider(SSOProvider):
    """SAML 2.0 provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.entity_id = config.get("entity_id")
        self.sso_url = config.get("sso_url")
        self.sls_url = config.get("sls_url")  # Single Logout Service
        self.x509_cert = config.get("x509_cert")
        self.private_key = config.get("private_key")
        self.name_id_format = config.get("name_id_format", "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress")
    
    def generate_saml_request(self, acs_url: str, relay_state: str = None) -> str:
        """Generate SAML AuthnRequest"""
        request_id = f"_{uuid.uuid4()}"
        issue_instant = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        saml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                    ID="{request_id}"
                    Version="2.0"
                    IssueInstant="{issue_instant}"
                    Destination="{self.sso_url}"
                    AssertionConsumerServiceURL="{acs_url}"
                    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{self.entity_id}</saml:Issuer>
    <samlp:NameIDPolicy Format="{self.name_id_format}" AllowCreate="true"/>
</samlp:AuthnRequest>"""
        
        # Base64 encode and deflate
        import zlib
        compressed = zlib.compress(saml_request.encode('utf-8'))[2:-4]
        encoded = base64.b64encode(compressed).decode('utf-8')
        
        return encoded
    
    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Get SAML SSO URL"""
        saml_request = self.generate_saml_request(redirect_uri, state)
        
        params = {
            "SAMLRequest": saml_request,
            "RelayState": state
        }
        
        return f"{self.sso_url}?{urlencode(params)}"
    
    async def validate_saml_response(self, saml_response: str) -> Dict[str, Any]:
        """Validate SAML response and extract user attributes"""
        try:
            # Decode base64 response
            decoded_response = base64.b64decode(saml_response)
            
            # Parse XML
            root = ET.fromstring(decoded_response)
            
            # Extract namespaces
            namespaces = {
                'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
                'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol'
            }
            
            # Validate signature if certificate is provided
            if self.x509_cert:
                # TODO: Implement signature validation
                pass
            
            # Extract assertion
            assertion = root.find('.//saml:Assertion', namespaces)
            if assertion is None:
                raise ValueError("No assertion found in SAML response")
            
            # Extract subject
            subject = assertion.find('.//saml:Subject/saml:NameID', namespaces)
            if subject is None:
                raise ValueError("No subject found in SAML assertion")
            
            # Extract attributes
            attributes = {}
            attr_statements = assertion.findall('.//saml:AttributeStatement/saml:Attribute', namespaces)
            
            for attr in attr_statements:
                attr_name = attr.get('Name')
                attr_values = [val.text for val in attr.findall('saml:AttributeValue', namespaces)]
                attributes[attr_name] = attr_values[0] if len(attr_values) == 1 else attr_values
            
            return {
                "name_id": subject.text,
                "attributes": attributes,
                "email": attributes.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress", 
                                      attributes.get("email", subject.text)),
                "first_name": attributes.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
                                           attributes.get("first_name")),
                "last_name": attributes.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
                                          attributes.get("last_name")),
                "groups": attributes.get("http://schemas.microsoft.com/ws/2008/06/identity/claims/groups",
                                       attributes.get("groups", []))
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid SAML response: {str(e)}"
            )
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate SAML response (token is the SAML response)"""
        return await self.validate_saml_response(token)
    
    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """SAML doesn't use code exchange, return the response directly"""
        return await self.validate_saml_response(code)


class SSOService:
    """SSO service for managing enterprise authentication"""
    
    def __init__(self):
        self.providers: Dict[str, SSOProvider] = {}
    
    async def get_organization_sso_config(self, org_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """Get SSO configuration for organization"""
        org_repo = OrganizationRepository(db)
        org = await org_repo.get_by_id(org_id)
        
        if not org or not org.sso_config:
            return None
        
        return org.sso_config
    
    async def configure_sso_provider(self, org_id: str, sso_config: Dict[str, Any], db: AsyncSession) -> bool:
        """Configure SSO provider for organization"""
        org_repo = OrganizationRepository(db)
        audit_repo = AuditLogRepository(db)
        
        # Validate configuration
        provider_type = sso_config.get("type")
        if provider_type not in ["oidc", "saml"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported SSO provider type"
            )
        
        # Update organization SSO config
        org = await org_repo.get_by_id(org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        await org_repo.update(org_id, {"sso_config": sso_config})
        
        # Log configuration change
        await audit_repo.create({
            "org_id": org_id,
            "action": "sso_configured",
            "resource_type": "organization",
            "resource_id": org_id,
            "payload_json": {"provider_type": provider_type, "provider_name": sso_config.get("name")}
        })
        
        return True
    
    async def get_sso_provider(self, org_id: str, db: AsyncSession) -> Optional[SSOProvider]:
        """Get configured SSO provider for organization"""
        sso_config = await self.get_organization_sso_config(org_id, db)
        if not sso_config:
            return None
        
        provider_type = sso_config.get("type")
        
        if provider_type == "oidc":
            return OIDCProvider(sso_config)
        elif provider_type == "saml":
            return SAMLProvider(sso_config)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported SSO provider type: {provider_type}"
            )
    
    async def initiate_sso_login(self, org_id: str, redirect_uri: str, db: AsyncSession) -> str:
        """Initiate SSO login flow"""
        provider = await self.get_sso_provider(org_id, db)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SSO not configured for organization"
            )
        
        # Generate state parameter for CSRF protection
        state = base64.urlsafe_b64encode(f"{org_id}:{uuid.uuid4()}".encode()).decode()
        
        return await provider.get_authorization_url(state, redirect_uri)
    
    async def handle_sso_callback(
        self, 
        org_id: str, 
        code_or_response: str, 
        state: str, 
        redirect_uri: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle SSO callback and create/update user"""
        provider = await self.get_sso_provider(org_id, db)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SSO not configured for organization"
            )
        
        # Validate state parameter
        try:
            decoded_state = base64.urlsafe_b64decode(state.encode()).decode()
            state_org_id, _ = decoded_state.split(":", 1)
            if state_org_id != org_id:
                raise ValueError("Invalid state parameter")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter"
            )
        
        # Exchange code/response for user information
        if isinstance(provider, OIDCProvider):
            token_response = await provider.exchange_code(code_or_response, redirect_uri)
            id_token = token_response.get("id_token")
            access_token = token_response.get("access_token")
            
            # Validate ID token
            user_claims = await provider.validate_token(id_token)
            
            # Get additional user info if available
            if access_token and provider.userinfo_endpoint:
                try:
                    user_info = await provider.get_user_info(access_token)
                    user_claims.update(user_info)
                except Exception:
                    pass  # Use claims from ID token
                    
        elif isinstance(provider, SAMLProvider):
            user_claims = await provider.validate_saml_response(code_or_response)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported provider type"
            )
        
        # Create or update user
        return await self._create_or_update_sso_user(org_id, user_claims, provider, db)
    
    async def _create_or_update_sso_user(
        self, 
        org_id: str, 
        user_claims: Dict[str, Any], 
        provider: SSOProvider,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Create or update user from SSO claims"""
        user_repo = UserRepository(db)
        audit_repo = AuditLogRepository(db)
        
        # Extract user information from claims
        email = user_claims.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided in SSO response"
            )
        
        # Map roles from SSO claims
        role = self._map_sso_role(user_claims, provider.config)
        
        # Check if user exists
        existing_user = await user_repo.get_by_email(email)
        
        if existing_user:
            # Update existing user
            if existing_user.org_id != uuid.UUID(org_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User belongs to different organization"
                )
            
            # Update user information
            update_data = {
                "role": role,
                "provider": provider.provider_type,
                "is_active": True,
                "email_verified": True,
                "last_login": datetime.utcnow()
            }
            
            user = await user_repo.update(str(existing_user.id), update_data)
            
            # Log SSO login
            await audit_repo.create({
                "org_id": org_id,
                "user_id": str(user.id),
                "action": "sso_login",
                "resource_type": "user",
                "resource_id": str(user.id),
                "payload_json": {"provider": provider.provider_type, "email": email}
            })
            
        else:
            # Create new user
            user_data = {
                "email": email,
                "org_id": org_id,
                "role": role,
                "provider": provider.provider_type,
                "is_active": True,
                "email_verified": True,
                "last_login": datetime.utcnow()
            }
            
            user = await user_repo.create(user_data)
            
            # Log user creation
            await audit_repo.create({
                "org_id": org_id,
                "user_id": str(user.id),
                "action": "sso_user_created",
                "resource_type": "user",
                "resource_id": str(user.id),
                "payload_json": {"provider": provider.provider_type, "email": email, "role": role}
            })
        
        return {
            "user": user,
            "claims": user_claims
        }
    
    def _map_sso_role(self, user_claims: Dict[str, Any], provider_config: Dict[str, Any]) -> str:
        """Map SSO claims to application roles"""
        role_mapping = provider_config.get("role_mapping", {})
        default_role = provider_config.get("default_role", "viewer")
        
        # Check for role in claims
        role_claim = provider_config.get("role_claim", "role")
        user_role = user_claims.get(role_claim)
        
        if user_role and user_role in role_mapping:
            return role_mapping[user_role]
        
        # Check for group-based role mapping
        groups_claim = provider_config.get("groups_claim", "groups")
        user_groups = user_claims.get(groups_claim, [])
        
        if isinstance(user_groups, str):
            user_groups = [user_groups]
        
        for group in user_groups:
            if group in role_mapping:
                return role_mapping[group]
        
        return default_role
    
    async def get_sso_metadata(self, org_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Get SSO metadata for organization (for SP-initiated flows)"""
        sso_config = await self.get_organization_sso_config(org_id, db)
        if not sso_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SSO not configured for organization"
            )
        
        provider_type = sso_config.get("type")
        
        if provider_type == "saml":
            # Generate SAML SP metadata
            entity_id = f"{settings.BASE_URL}/sso/{org_id}/metadata"
            acs_url = f"{settings.BASE_URL}/sso/{org_id}/acs"
            
            metadata = f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                     entityID="{entity_id}">
    <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                                   Location="{acs_url}"
                                   index="0"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""
            
            return {
                "type": "saml",
                "metadata": metadata,
                "entity_id": entity_id,
                "acs_url": acs_url
            }
        
        elif provider_type == "oidc":
            return {
                "type": "oidc",
                "client_id": sso_config.get("client_id"),
                "redirect_uri": f"{settings.BASE_URL}/sso/{org_id}/callback"
            }
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported SSO provider type"
            )


# Global SSO service instance
sso_service = SSOService()