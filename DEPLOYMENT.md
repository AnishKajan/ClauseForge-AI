# ClauseForge Azure Deployment Guide

## Overview

ClauseForge is deployed on Azure using the following architecture:
- **Backend**: Azure Container Apps (ACA) with images from Azure Container Registry (ACR)
- **Frontend**: Azure Static Web Apps (SWA) with static export from Next.js
- **Database**: Azure PostgreSQL Flexible Server
- **Storage**: Azure Blob Storage
- **Secrets**: Azure Key Vault

## Azure Resources

### Resource Group: `clauseforge-prod`
- **Location**: East US 2
- **Container Registry**: `clauseforgeacr`
- **Container App**: `clauseforge-api`
- **Key Vault**: `clauseforge-kv`

### Key Vault Secrets
The following secrets must be configured in Azure Key Vault (`clauseforge-kv`):

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `database-url` | PostgreSQL connection string | `postgresql://user:pass@server.postgres.database.azure.com:5432/clauseforge` |
| `storage-conn` | Azure Storage connection string | `DefaultEndpointsProtocol=https;AccountName=...` |
| `stripe-secret-key` | Stripe API secret key | `sk_live_...` |
| `claude-api-key` | Anthropic Claude API key | `sk-ant-...` |

## GitHub Secrets

The following secrets must be configured in GitHub repository settings:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AZURE_CREDENTIALS` | Azure service principal credentials | JSON object with clientId, clientSecret, etc. |
| `PROD_API_URL` | Container App FQDN | `https://clauseforge-api.azurecontainerapps.io` |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | SWA deployment token | Generated from Azure portal |

## Deployment Pipeline

### Triggers
- **Main branch**: Deploys to production
- **Pull requests**: Runs tests and security scans only

### Pipeline Steps
1. **Tests**: Backend (Python) and Frontend (Node.js) tests
2. **Security Scan**: Trivy vulnerability scanner
3. **Build**: ACR builds for both backend and frontend images
4. **Deploy Backend**: Updates Container App with new image and secret references
5. **Deploy Frontend**: Builds and deploys to Static Web Apps

### Environment Variables in Container App

The Container App uses secret references (not direct Key Vault references):

```bash
DATABASE_URL=secretref:database-url
AZURE_STORAGE_CONNECTION_STRING=secretref:storage-conn
STRIPE_SECRET_KEY=secretref:stripe-secret-key
CLAUDE_API_KEY=secretref:claude-api-key
ENVIRONMENT=production
PORT=8000
```

## Adding New Secrets

### 1. Add to Azure Key Vault
```bash
az keyvault secret set \
  --vault-name clauseforge-kv \
  --name "new-secret-name" \
  --value "secret-value"
```

### 2. Update Container App Secret Reference
```bash
az containerapp secret set \
  -g clauseforge-prod \
  -n clauseforge-api \
  --secrets "new-secret-name=keyvaultref:https://clauseforge-kv.vault.azure.net/secrets/new-secret-name,identityref:/subscriptions/{subscription-id}/resourceGroups/clauseforge-prod/providers/Microsoft.ManagedIdentity/userAssignedIdentities/{identity-name}"
```

### 3. Update Environment Variable
```bash
az containerapp update \
  -g clauseforge-prod \
  -n clauseforge-api \
  --set-env-vars "NEW_ENV_VAR=secretref:new-secret-name"
```

## Rollback Procedures

### Container App Rollback
```bash
# List revisions
az containerapp revision list \
  -g clauseforge-prod \
  -n clauseforge-api \
  --query "[].{Name:name,Active:properties.active,CreatedTime:properties.createdTime}" \
  -o table

# Activate previous revision
az containerapp revision activate \
  -g clauseforge-prod \
  -n clauseforge-api \
  --revision <previous-revision-name>
```

### Static Web App Rollback
Static Web Apps automatically maintain deployment history. Rollback through Azure portal:
1. Go to Azure Static Web Apps resource
2. Navigate to "Deployment history"
3. Select previous deployment and activate

## Monitoring and Health Checks

### Health Endpoints
- **Basic Health**: `https://clauseforge-api.azurecontainerapps.io/api/health`
- **Detailed Health**: `https://clauseforge-api.azurecontainerapps.io/api/health/detailed`

### Container App Logs
```bash
# View logs
az containerapp logs show \
  -g clauseforge-prod \
  -n clauseforge-api \
  --follow

# View specific revision logs
az containerapp revision show \
  -g clauseforge-prod \
  -n clauseforge-api \
  --revision <revision-name>
```

## Troubleshooting

### Common Issues

1. **Secret Reference Errors**
   - Ensure secrets exist in Key Vault
   - Verify Container App has managed identity with Key Vault access
   - Check secret reference format: `secretref:secret-name`

2. **Image Pull Errors**
   - Verify ACR access permissions
   - Check image exists: `az acr repository show-tags --name clauseforgeacr --repository clauseforge-api`

3. **Static Web App Build Failures**
   - Check Next.js configuration for static export
   - Verify environment variables are set correctly
   - Review build logs in GitHub Actions

### Debug Commands

```bash
# Check Container App status
az containerapp show -g clauseforge-prod -n clauseforge-api --query "properties.provisioningState"

# List Container App secrets
az containerapp secret list -g clauseforge-prod -n clauseforge-api

# Check Key Vault access
az keyvault secret list --vault-name clauseforge-kv

# Test Container App endpoint
curl -f https://clauseforge-api.azurecontainerapps.io/api/health
```

## Security Considerations

1. **Managed Identity**: Container App uses managed identity for Key Vault access
2. **Network Security**: Container App ingress is configured for HTTPS only
3. **Secret Rotation**: Secrets should be rotated regularly
4. **Access Control**: Use Azure RBAC for resource access control

## Performance Optimization

1. **Container Resources**: Adjust CPU/memory based on usage patterns
2. **Scaling Rules**: Configure auto-scaling based on HTTP requests or CPU usage
3. **CDN**: Consider Azure CDN for Static Web Apps for global performance
4. **Database**: Monitor and optimize PostgreSQL performance

## Backup and Disaster Recovery

1. **Database Backups**: Automated backups enabled on PostgreSQL Flexible Server
2. **Storage Backups**: Azure Blob Storage has geo-redundancy
3. **Code Repository**: GitHub serves as source of truth
4. **Infrastructure as Code**: All resources can be recreated from configuration

## Cost Optimization

1. **Container App**: Use consumption plan for variable workloads
2. **Storage**: Use appropriate storage tiers (Hot/Cool/Archive)
3. **Database**: Right-size compute and storage based on usage
4. **Monitoring**: Use Azure Cost Management for tracking and alerts