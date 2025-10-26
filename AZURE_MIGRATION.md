# ClauseForge Azure Migration Guide

## Migration Overview

This guide covers migrating ClauseForge from AWS to Azure using Azure Container Apps (ACA), Azure Container Registry (ACR), and other Azure services.

### Service Mapping

| AWS Service | Azure Equivalent | Purpose |
|-------------|------------------|---------|
| S3 | Blob Storage | Document storage |
| SQS | Service Bus (optional) | Message queuing |
| Textract | AI Document Intelligence | Document text extraction |
| ECS Fargate | Container Apps | Container orchestration |
| ECR | Container Registry | Container images |
| RDS PostgreSQL | PostgreSQL Flexible Server | Database |
| ElastiCache Redis | Azure Cache for Redis | Caching |
| IAM | Microsoft Entra ID | Authentication |
| CloudWatch | Azure Monitor | Logging and monitoring |

## Prerequisites

1. **Azure CLI** (latest version)
2. **Container Apps extension**
3. **Azure subscription** (Pay-as-you-go)
4. **GitHub repository** with existing ClauseForge code

```bash
# Install/upgrade Azure CLI and extensions
az upgrade
az extension add --name containerapp --upgrade

# Login and set subscription
az login
az account set --subscription "Subscription-Pay-as-you-go"
```

## Environment Variables

Set these variables before running the migration scripts:

```bash
# ====== CHANGE THESE ======
export RG="clauseforge"
export LOC="eastus2"
export ACR_NAME="clauseforgeacr"
export ACA_ENV="clauseforge-env"
export APP_NAME="clauseforge-api"
export DB_NAME="clauseforge-db"
export DB_ADMIN="cfadmin"
export DB_PASS="REPLACE_WITH_STRONG_PASSWORD"
export STG_NAME="clauseforgestorage"

# Secrets (supply real values)
export CLAUDE_API_KEY="REPLACE_WITH_ANTHROPIC_KEY"
export STRIPE_SECRET_KEY="REPLACE_WITH_STRIPE_KEY"
export JWT_SECRET="REPLACE_WITH_RANDOM_LONG_SECRET"
```

## Migration Steps

### 1. Create Azure Resources

Run the Azure setup script:
```bash
./scripts/setup-azure-resources.sh
```

### 2. Update Application Code

The migration includes:
- Replace AWS SDK with Azure SDK
- Update storage service for Blob Storage
- Replace Textract with Document Intelligence
- Update environment variables

### 3. Build and Deploy

```bash
# Build and push to ACR
az acr build --registry $ACR_NAME --image clauseforge-api:latest ./backend

# Deploy to Container Apps
az containerapp update \
  -g $RG -n $APP_NAME \
  --image $ACR_NAME.azurecr.io/clauseforge-api:latest
```

### 4. Frontend Deployment

Deploy frontend to Azure Static Web Apps via GitHub Actions integration.

### 5. Update CI/CD Pipeline

The GitHub Actions workflow will be updated to:
- Use Azure Container Registry instead of ECR
- Deploy to Azure Container Apps instead of ECS
- Use Azure-specific health checks

## Cost Comparison

### AWS (Current)
- ECS Fargate: ~$50-100/month
- RDS PostgreSQL: ~$30-60/month
- S3 + other services: ~$20-40/month
- **Total: ~$100-200/month**

### Azure (Target)
- Container Apps: ~$30-80/month (scale-to-zero)
- PostgreSQL Flexible: ~$25-50/month
- Blob Storage + other: ~$15-30/month
- **Total: ~$70-160/month**

**Estimated savings: 20-30%** with better scale-to-zero capabilities.

## Rollback Plan

If migration issues occur:
1. Revert DNS to AWS ALB
2. Scale up AWS ECS services
3. Restore database from backup if needed
4. Update GitHub secrets back to AWS

## Testing Strategy

1. **Unit Tests**: Run existing test suite
2. **Integration Tests**: Test Azure service integrations
3. **Load Testing**: Verify performance matches AWS
4. **Security Testing**: Validate Azure security configurations

## Post-Migration Tasks

1. Update documentation
2. Monitor Azure costs and performance
3. Optimize Container Apps scaling rules
4. Set up Azure Monitor alerts
5. Train team on Azure tools

## Support

For migration issues:
1. Check Azure CLI logs: `az monitor activity-log list`
2. Review Container Apps logs: `az containerapp logs show`
3. Validate resource configurations
4. Contact Azure support if needed