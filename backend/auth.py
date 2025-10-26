import os
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient, decode as jwt_decode

TENANT_ID = os.getenv("AZURE_AD_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_AD_CLIENT_ID")

ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
JWKS_URL = f"{ISSUER}/discovery/v2.0/keys"

security = HTTPBearer(auto_error=True)
jwks_client = PyJWKClient(JWKS_URL)

def verify_bearer(auth: HTTPAuthorizationCredentials = Depends(security)):
    token = auth.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token).key
        payload = jwt_decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=CLIENT_ID,
            issuer=ISSUER,
        )
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")