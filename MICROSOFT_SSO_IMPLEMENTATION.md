# Microsoft Entra ID SSO Implementation

This document outlines the complete implementation of Microsoft Entra ID (Azure AD) Single Sign-On (SSO) with NextAuth.js and FastAPI token validation.

## 🔧 Implementation Summary

### Frontend (Next.js)

#### 1. Environment Configuration
**File: `frontend/.env.local`**
```env
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=REPLACE_WITH_RANDOM_32_CHARS
AZURE_AD_CLIENT_ID=4efdaa2c-6bc7-4833-a835-3a73d6a16017
AZURE_AD_CLIENT_SECRET=REPLACE_WITH_AZURE_CLIENT_SECRET_VALUE
AZURE_AD_TENANT_ID=80b23743-3c28-4f99-bd79-f9968120b802
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

#### 2. NextAuth Handler (App Router)
**File: `frontend/src/app/api/auth/[...nextauth]/route.ts`**
- Configured Azure AD provider with proper scopes
- JWT strategy for session management
- Email domain restriction (`.edu` emails only)
- ID token forwarding to session

#### 3. API Helper for Token Forwarding
**File: `frontend/src/lib/api.ts`**
- Automatically includes Azure ID token in Authorization header
- Server-side session retrieval
- Seamless integration with FastAPI backend

#### 4. Enhanced Login Page
**File: `frontend/src/app/login/page.tsx`**
- Microsoft SSO button with proper branding
- Fallback to credentials authentication
- Back navigation support

#### 5. Back Navigation Component
**File: `frontend/src/components/BackNavigation.tsx`**
- Reusable component for consistent navigation
- Router.back() fallback or custom href
- Applied to all feature pages and auth flows

### Backend (FastAPI)

#### 1. Environment Configuration
**File: `backend/.env`**
```env
AZURE_AD_TENANT_ID=80b23743-3c28-4f99-bd79-f9968120b802
AZURE_AD_CLIENT_ID=4efdaa2c-6bc7-4833-a835-3a73d6a16017
```

#### 2. Dependencies Added
**File: `backend/requirements.txt`**
```
pyjwt[crypto]==2.8.0
```

#### 3. JWT Token Verification
**File: `backend/auth.py`**
- PyJWKClient for Azure AD public key retrieval
- RS256 signature verification
- Audience and issuer validation
- FastAPI dependency for protected routes

#### 4. Protected API Endpoint
**File: `backend/main.py`**
- CORS configuration for frontend integration
- `/api/secure` endpoint demonstrating token validation
- Returns user information from JWT claims

### Testing

#### Test Page
**File: `frontend/src/app/test-sso/page.tsx`**
- Session status display
- Secure API endpoint testing
- Error handling and response display
- Step-by-step test instructions

## 🚀 Azure Portal Configuration Required

### App Registration Settings
1. **Redirect URIs:**
   - `http://localhost:3000/api/auth/callback/azure-ad`
   - `https://YOUR_DOMAIN.com/api/auth/callback/azure-ad` (for production)

2. **Authentication Settings:**
   - Enable "ID tokens" under Authentication
   - Set supported account types per tenant policy

3. **Client Secret:**
   - Generate a new client secret in "Certificates & secrets"
   - Update `AZURE_AD_CLIENT_SECRET` in environment files

## 🧪 Smoke Test Instructions

### Local Development Setup
1. **Start Backend:**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000
   ```

2. **Start Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Test Flow:**
   - Navigate to `http://localhost:3000/login`
   - Click "Sign in with Microsoft"
   - Complete Azure AD authentication
   - Visit `http://localhost:3000/test-sso`
   - Click "Test Secure Endpoint"
   - Verify 200 response with user information

### Expected API Response
```json
{
  "message": "ok",
  "user": {
    "sub": "user-azure-id",
    "email": "user@university.edu"
  }
}
```

## 🔒 Security Features

1. **Email Domain Restriction:** Only `.edu` emails allowed (configurable)
2. **JWT Signature Verification:** RS256 with Azure AD public keys
3. **Audience Validation:** Ensures tokens are for this application
4. **Issuer Validation:** Verifies tokens from correct Azure AD tenant
5. **CORS Configuration:** Restricts frontend origins

## 🔄 Navigation Enhancements

### Back Navigation Added To:
- `/pricing` - Back to Home
- `/signup` - Back to Home  
- `/login` - Back to Home
- `/features/analysis` - Back to Home
- `/features/chat` - Back to Home
- `/features/risk` - Back to Home
- `/test-sso` - Back to Dashboard

### Component Features:
- Automatic `router.back()` fallback
- Custom href override option
- Consistent styling with theme
- Accessible button design

## 📝 Next Steps

1. **Replace Placeholders:**
   - Generate and set `NEXTAUTH_SECRET` (32+ characters)
   - Obtain and set `AZURE_AD_CLIENT_SECRET` from Azure Portal

2. **Production Configuration:**
   - Update redirect URIs in Azure Portal
   - Set production domain in CORS origins
   - Configure environment variables in deployment

3. **Optional Enhancements:**
   - Remove email domain restriction if not needed
   - Add role-based access control
   - Implement refresh token handling
   - Add logout functionality

## 🐛 Troubleshooting

### Common Issues:
1. **Invalid redirect URI:** Ensure exact match in Azure Portal
2. **Token validation fails:** Check tenant ID and client ID
3. **CORS errors:** Verify frontend URL in backend CORS settings
4. **Email restriction:** Remove `.edu` check if using different domains

### Debug Tips:
- Check browser network tab for authentication flows
- Verify JWT token structure at jwt.io
- Enable FastAPI debug mode for detailed error messages
- Use `/test-sso` page for systematic testing