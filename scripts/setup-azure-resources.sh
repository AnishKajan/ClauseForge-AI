#!/bin/bash

# ClauseForge Azure Resources Setup Script
# Migrates from AWS to Azure Container Apps + supporting services

set -e

# Configuration - Update these values
RG=${RG:-"clauseforge"}
LOC=${LOC:-"eastus2"}
ACR_NAME=${ACR_NAME:-"clauseforgeacr"}
ACA_ENV=${ACA_ENV:-"clauseforge-env"}
APP_NAME=${APP_NAME:-"clauseforge-api"}
DB_NAME=${DB_NAME:-"clauseforge-db"}
DB_ADMIN=${DB_ADMIN:-"cfadmin"}
DB_PASS=${DB_PASS:-"REPLACE_WITH_STRONG_PASSWORD"}
STG_NAME=${STG_NAME:-"clauseforgestorage"}

# Secrets - Set these as environment variables
CLAUDE_API_KEY=${CLAUDE_API_KEY:-"REPLACE_WITH_ANTHROPIC_KEY"}
STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY:-"REPLACE_WITH_STRIPE_KEY"}
JWT_SECRET=${JWT_SECRET:-"REPLACE_WITH_RANDOM_LONG_SECRET"}

echo "🚀 Setting up Azure resources for ClauseForge"
echo "Resource Group: $RG"
echo "Location: $LOC"
echo "Container Registry: $ACR_NAME"
echo "Container Apps Environment: $ACA_ENV"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Error: Azure CLI is not installed. Please install it first."
    exit 1
fi

# Check if containerapp extension is installed
if ! az extension list --query "[?name=='containerapp']" -o tsv | grep -q containerapp; then
    echo "📦 Installing Container Apps extension..."
    az extension add --name containerapp --upgrade
fi

# Verify Azure login
echo "🔐 Verifying Azure credentials..."
az account show > /dev/null || {
    echo "❌ Error: Not logged into Azure. Run 'az login' first."
    exit 1
}

echo "✅ Azure CLI configured successfully"

# 1. Create Resource Group
echo "📁 Creating Resource Group: $RG"
az group create -n $RG -l $LOC

# 2. Create Log Analytics Workspace (for Container Apps logs)
echo "📊 Creating Log Analytics Workspace..."
az monitor log-analytics workspace create -g $RG -n clauseforge-law -l $LOC

LAW_ID=$(az monitor log-analytics workspace show -g $RG -n clauseforge-law --query customerId -o tsv)
LAW_KEY=$(az monitor log-analytics workspace get-shared-keys -g $RG -n clauseforge-law --query primarySharedKey -o tsv)

echo "✅ Log Analytics Workspace created"

# 3. Create Container Apps Environment
echo "🏗️ Creating Container Apps Environment: $ACA_ENV"
az containerapp env create \
  -g $RG -n $ACA_ENV -l $LOC \
  --logs-workspace-id $LAW_ID \
  --logs-workspace-key $LAW_KEY

echo "✅ Container Apps Environment created"

# 4. Create PostgreSQL Flexible Server with pgvector
echo "🗄️ Creating PostgreSQL Flexible Server: $DB_NAME"
az postgres flexible-server create \
  -g $RG -n $DB_NAME -l $LOC \
  --tier Burstable --sku-name Standard_B1ms \
  --storage-size 32 --version 16 \
  --auth-type Password --admin-user $DB_ADMIN --admin-password $DB_PASS --yes

# Build DATABASE_URL for FastAPI
DATABASE_URL="postgresql+psycopg://$DB_ADMIN:$DB_PASS@$DB_NAME.postgres.database.azure.com:5432/clauseforge"
echo "✅ PostgreSQL server created"

echo "⚠️  Remember to enable pgvector extension after first connection:"
echo "   psql \"postgresql://$DB_ADMIN:$DB_PASS@$DB_NAME.postgres.database.azure.com:5432/postgres\""
echo "   => CREATE EXTENSION IF NOT EXISTS vector;"

# 5. Create Azure Cache for Redis
echo "🔴 Creating Azure Cache for Redis..."
az redis create \
  -g $RG -n clauseforge-redis -l $LOC \
  --sku Basic --vm-size c0

REDIS_KEY=$(az redis list-keys -g $RG -n clauseforge-redis --query primaryKey -o tsv)
REDIS_URL="redis://:$REDIS_KEY@clauseforge-redis.redis.cache.windows.net:6380/0?ssl=true"

echo "✅ Redis cache created"

# 6. Create Blob Storage (S3 → Blob)
echo "💾 Creating Storage Account: $STG_NAME"
az storage account create -g $RG -n $STG_NAME -l $LOC --sku Standard_LRS

ST_CONN=$(az storage account show-connection-string -g $RG -n $STG_NAME --query connectionString -o tsv)

# Create containers (equivalent to S3 buckets)
az storage container create --name contracts --connection-string "$ST_CONN"
az storage container create --name exports --connection-string "$ST_CONN"
az storage container create --name logs --connection-string "$ST_CONN"

echo "✅ Storage account and containers created"

# 7. Create Azure Container Registry
echo "🐳 Creating Azure Container Registry: $ACR_NAME"
az acr create -g $RG -n $ACR_NAME --sku Standard -l $LOC

echo "✅ Container Registry created"

# 8. Create Document Intelligence resource (Textract → Form Recognizer)
echo "📄 Creating Document Intelligence resource..."
az cognitiveservices account create \
  -g $RG -n clauseforge-doc-intel -l $LOC \
  --kind FormRecognizer --sku S0

DOC_INTEL_ENDPOINT=$(az cognitiveservices account show -g $RG -n clauseforge-doc-intel --query properties.endpoint -o tsv)
DOC_INTEL_KEY=$(az cognitiveservices account keys list -g $RG -n clauseforge-doc-intel --query key1 -o tsv)

echo "✅ Document Intelligence resource created"

# 9. Create Container App with temporary image (will update later)
echo "🚀 Creating Container App: $APP_NAME"
az containerapp create \
  -g $RG -n $APP_NAME --environment $ACA_ENV \
  --ingress external --target-port 8000 \
  --min-replicas 0 --max-replicas 2 \
  --image mcr.microsoft.com/azuredocs/containerapps-helloworld:latest

echo "✅ Container App created with temporary image"

# 10. Set Container App secrets
echo "🔐 Setting Container App secrets..."
az containerapp secret set -g $RG -n $APP_NAME \
  --secrets \
  claude-api-key="$CLAUDE_API_KEY" \
  stripe-secret-key="$STRIPE_SECRET_KEY" \
  database-url="$DATABASE_URL" \
  redis-url="$REDIS_URL" \
  storage-connection="$ST_CONN" \
  jwt-secret="$JWT_SECRET" \
  doc-intel-endpoint="$DOC_INTEL_ENDPOINT" \
  doc-intel-key="$DOC_INTEL_KEY"

echo "✅ Secrets configured"

# 11. Create Key Vault for additional secret management (optional)
echo "🔑 Creating Key Vault..."
VAULT_NAME="clauseforge-kv-$(date +%s | tail -c 6)"
az keyvault create -g $RG -n $VAULT_NAME -l $LOC

# Store secrets in Key Vault
az keyvault secret set --vault-name $VAULT_NAME --name "claude-api-key" --value "$CLAUDE_API_KEY"
az keyvault secret set --vault-name $VAULT_NAME --name "stripe-secret-key" --value "$STRIPE_SECRET_KEY"
az keyvault secret set --vault-name $VAULT_NAME --name "jwt-secret" --value "$JWT_SECRET"

echo "✅ Key Vault created and secrets stored"

# 12. Output configuration summary
echo ""
echo "🎉 Azure Resources Created Successfully!"
echo "=================================================="
echo ""
echo "📋 Resource Summary:"
echo "  Resource Group: $RG"
echo "  Location: $LOC"
echo "  Container Registry: $ACR_NAME.azurecr.io"
echo "  Container App: $APP_NAME"
echo "  Database: $DB_NAME.postgres.database.azure.com"
echo "  Storage Account: $STG_NAME"
echo "  Key Vault: $VAULT_NAME"
echo ""
echo "🔗 Connection Strings:"
echo "  DATABASE_URL: $DATABASE_URL"
echo "  REDIS_URL: $REDIS_URL"
echo "  STORAGE_CONNECTION: [stored in secrets]"
echo ""
echo "📄 Document Intelligence:"
echo "  Endpoint: $DOC_INTEL_ENDPOINT"
echo "  Key: [stored in secrets]"
echo ""
echo "🚀 Next Steps:"
echo "1. Enable pgvector extension in PostgreSQL:"
echo "   psql \"$DATABASE_URL\" -c \"CREATE EXTENSION IF NOT EXISTS vector;\""
echo ""
echo "2. Build and push your application image:"
echo "   az acr build --registry $ACR_NAME --image clauseforge-api:latest ./backend"
echo ""
echo "3. Update Container App with your image:"
echo "   az containerapp update -g $RG -n $APP_NAME \\"
echo "     --image $ACR_NAME.azurecr.io/clauseforge-api:latest \\"
echo "     --set-env-vars \\"
echo "     CLAUDE_API_KEY=secretref:claude-api-key \\"
echo "     STRIPE_SECRET_KEY=secretref:stripe-secret-key \\"
echo "     DATABASE_URL=secretref:database-url \\"
echo "     REDIS_URL=secretref:redis-url \\"
echo "     AZURE_STORAGE_CONNECTION_STRING=secretref:storage-connection \\"
echo "     JWT_SECRET=secretref:jwt-secret \\"
echo "     AZURE_DOC_INTEL_ENDPOINT=secretref:doc-intel-endpoint \\"
echo "     AZURE_DOC_INTEL_KEY=secretref:doc-intel-key \\"
echo "     PORT=8000"
echo ""
echo "4. Get your Container App URL:"
echo "   az containerapp show -g $RG -n $APP_NAME --query properties.configuration.ingress.fqdn -o tsv"
echo ""
echo "5. Set up GitHub Actions with these secrets:"
echo "   AZURE_CREDENTIALS (service principal JSON)"
echo "   AZURE_RG=$RG"
echo "   AZURE_ACR_NAME=$ACR_NAME"
echo "   AZURE_APP_NAME=$APP_NAME"
echo ""
echo "✅ Setup completed successfully!"