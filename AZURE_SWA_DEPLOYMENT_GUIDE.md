# Azure Static Web App Deployment Guide

## Manual Verification Commands

After deployment, you can manually verify the Static Web App status using these Azure CLI commands:

```bash
# Show specific Static Web App details
az staticwebapp show -g clauseforge-prod -n clauseforge-frontend --query "{name:name, host:defaultHostname, id:id, region:location, repo:repositoryUrl}"

# List all Static Web Apps in subscription
az staticwebapp list --query "[].{name:name, host:defaultHostname, rg:resourceGroup}" -o table
```

## GitHub Secret Configuration

### Azure Static Web Apps API Token

1. Navigate to the Azure Portal
2. Go to your Static Web App resource: `clauseforge-frontend`
3. Click on "Manage deployment token" in the overview section
4. Copy the deployment token
5. In GitHub, go to your repository settings → Secrets and variables → Actions
6. Update the secret `AZURE_STATIC_WEB_APPS_API_TOKEN` with the copied token
7. **Important**: Paste the token as a single line with no extra spaces or newlines

### Troubleshooting Token Issues

The GitHub Actions workflow now includes debug steps that will help identify token issues:

- **Debug SWA token length**: Should show a nonzero value (typically 200-400 characters)
- **Debug SWA token trailing-bytes**: Should end with `0a` only (indicating proper line ending)

If the token length shows 0, re-save the secret in GitHub. If trailing bytes show unexpected values, the token may have extra whitespace that needs to be removed.

## CORS Configuration

The backend is configured to allow CORS from the Static Web App domain:
- Production domain: `https://orange-ocean-083504e0f.3.azurestaticapps.net/`

If the Static Web App domain changes, update the `CORS_ALLOWED_ORIGINS` environment variable in the `deploy-production` job.

## Deployment Process

1. **Frontend Testing**: Runs linting and type checking
2. **Token Debugging**: Validates the deployment token format
3. **Static Web App Deployment**: Builds and deploys the frontend
4. **Verification**: Confirms deployment status via Azure CLI

## Common Issues

1. **Token length is 0**: Re-save the GitHub secret
2. **Deployment fails with authentication error**: Verify the deployment token in Azure Portal matches the GitHub secret
3. **CORS errors**: Ensure the backend `CORS_ALLOWED_ORIGINS` includes the correct Static Web App domain