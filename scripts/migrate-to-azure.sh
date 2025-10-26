#!/bin/bash

# ClauseForge AWS to Azure Migration Script
# This script helps migrate data and configurations from AWS to Azure

set -e

# Configuration
RG=${RG:-"clauseforge"}
MIGRATION_LOG="migration-$(date +%Y%m%d-%H%M%S).log"

echo "🚀 Starting ClauseForge migration from AWS to Azure"
echo "Migration log: $MIGRATION_LOG"

# Create log file
exec > >(tee -a "$MIGRATION_LOG")
exec 2>&1

echo "📅 Migration started at: $(date)"

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check Azure CLI
if ! command -v az &> /dev/null; then
    echo "❌ Error: Azure CLI is not installed"
    exit 1
fi

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ Error: AWS CLI is not installed (needed for data migration)"
    exit 1
fi

# Check if logged into Azure
az account show > /dev/null || {
    echo "❌ Error: Not logged into Azure. Run 'az login' first."
    exit 1
}

# Check if AWS credentials are configured
aws sts get-caller-identity > /dev/null || {
    echo "❌ Error: AWS credentials not configured. Run 'aws configure' first."
    exit 1
}

echo "✅ Prerequisites check passed"

# Step 1: Create Azure resources
echo ""
echo "📦 Step 1: Creating Azure resources..."
if [ -f "./scripts/setup-azure-resources.sh" ]; then
    ./scripts/setup-azure-resources.sh
else
    echo "❌ Error: setup-azure-resources.sh not found"
    exit 1
fi

# Step 2: Migrate S3 data to Blob Storage
echo ""
echo "📁 Step 2: Migrating S3 data to Azure Blob Storage..."

# Get S3 bucket name from environment or default
S3_BUCKET=${S3_BUCKET_NAME:-"lexiscan-documents"}
STORAGE_ACCOUNT=${STG_NAME:-"clauseforgestorage"}

echo "Source S3 bucket: $S3_BUCKET"
echo "Target storage account: $STORAGE_ACCOUNT"

# Check if S3 bucket exists and has objects
if aws s3 ls "s3://$S3_BUCKET" > /dev/null 2>&1; then
    OBJECT_COUNT=$(aws s3 ls "s3://$S3_BUCKET" --recursive | wc -l)
    echo "Found $OBJECT_COUNT objects in S3 bucket"
    
    if [ "$OBJECT_COUNT" -gt 0 ]; then
        echo "🔄 Starting data migration..."
        
        # Use AzCopy for efficient migration
        if command -v azcopy &> /dev/null; then
            echo "Using AzCopy for migration..."
            
            # Get storage account key
            STORAGE_KEY=$(az storage account keys list -g "$RG" -n "$STORAGE_ACCOUNT" --query '[0].value' -o tsv)
            
            # Sync S3 to Blob Storage
            azcopy sync "https://s3.amazonaws.com/$S3_BUCKET" \
                "https://$STORAGE_ACCOUNT.blob.core.windows.net/contracts?sv=2020-08-04&ss=b&srt=sco&sp=rwdlacx&se=2024-12-31T23:59:59Z&st=2024-01-01T00:00:00Z&spr=https&sig=PLACEHOLDER" \
                --recursive=true
        else
            echo "⚠️  AzCopy not found. Using AWS CLI + Azure CLI for migration..."
            
            # Create temporary directory for migration
            TEMP_DIR="/tmp/clauseforge-migration"
            mkdir -p "$TEMP_DIR"
            
            # Download from S3 and upload to Azure (for small datasets)
            aws s3 sync "s3://$S3_BUCKET" "$TEMP_DIR" --quiet
            
            # Upload to Azure Blob Storage
            az storage blob upload-batch \
                --account-name "$STORAGE_ACCOUNT" \
                --destination "contracts" \
                --source "$TEMP_DIR" \
                --auth-mode key
            
            # Cleanup
            rm -rf "$TEMP_DIR"
        fi
        
        echo "✅ Data migration completed"
    else
        echo "ℹ️  No objects found in S3 bucket, skipping data migration"
    fi
else
    echo "⚠️  S3 bucket not found or not accessible, skipping data migration"
fi

# Step 3: Update application configuration
echo ""
echo "⚙️  Step 3: Updating application configuration..."

# Create new environment file for Azure
cat > .env.azure << EOF
# Azure Configuration
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=$STORAGE_ACCOUNT;AccountKey=REPLACE_WITH_ACTUAL_KEY;EndpointSuffix=core.windows.net"
AZURE_STORAGE_CONTAINER_NAME="contracts"
AZURE_DOC_INTEL_ENDPOINT="https://clauseforge-doc-intel.cognitiveservices.azure.com/"
AZURE_DOC_INTEL_KEY="REPLACE_WITH_ACTUAL_KEY"

# Database (Azure PostgreSQL)
DATABASE_URL="postgresql+psycopg://cfadmin:REPLACE_WITH_PASSWORD@clauseforge-db.postgres.database.azure.com:5432/clauseforge"

# Redis (Azure Cache for Redis)
REDIS_URL="redis://:REPLACE_WITH_KEY@clauseforge-redis.redis.cache.windows.net:6380/0?ssl=true"

# Application settings
ENVIRONMENT=production
DEBUG=false
PORT=8000

# API Keys (same as before)
CLAUDE_API_KEY=REPLACE_WITH_ANTHROPIC_KEY
STRIPE_SECRET_KEY=REPLACE_WITH_STRIPE_KEY
JWT_SECRET=REPLACE_WITH_JWT_SECRET
EOF

echo "✅ Created .env.azure configuration file"

# Step 4: Build and deploy application
echo ""
echo "🐳 Step 4: Building and deploying application..."

# Build and push to ACR
ACR_NAME=${ACR_NAME:-"clauseforgeacr"}
echo "Building backend image..."
az acr build --registry "$ACR_NAME" --image clauseforge-api:latest ./backend

echo "Building frontend image..."
az acr build --registry "$ACR_NAME" --image clauseforge-frontend:latest ./frontend

# Update Container App
APP_NAME=${APP_NAME:-"clauseforge-api"}
echo "Updating Container App..."
az containerapp update \
    -g "$RG" -n "$APP_NAME" \
    --image "$ACR_NAME.azurecr.io/clauseforge-api:latest"

echo "✅ Application deployed to Azure"

# Step 5: Verify migration
echo ""
echo "🔍 Step 5: Verifying migration..."

# Get Container App URL
APP_URL=$(az containerapp show -g "$RG" -n "$APP_NAME" --query properties.configuration.ingress.fqdn -o tsv)
echo "Application URL: https://$APP_URL"

# Test health endpoints
echo "Testing health endpoints..."
if curl -f "https://$APP_URL/api/health" > /dev/null 2>&1; then
    echo "✅ Basic health check passed"
else
    echo "❌ Basic health check failed"
fi

if curl -f "https://$APP_URL/api/health/detailed" > /dev/null 2>&1; then
    echo "✅ Detailed health check passed"
else
    echo "❌ Detailed health check failed"
fi

# Step 6: Migration summary
echo ""
echo "📊 Migration Summary"
echo "==================="
echo "Migration completed at: $(date)"
echo "Resource Group: $RG"
echo "Container Registry: $ACR_NAME.azurecr.io"
echo "Container App: $APP_NAME"
echo "Application URL: https://$APP_URL"
echo "Storage Account: $STORAGE_ACCOUNT"
echo ""

# Next steps
echo "🎯 Next Steps:"
echo "=============="
echo "1. Update DNS records to point to: https://$APP_URL"
echo "2. Update GitHub secrets with Azure credentials"
echo "3. Test all application functionality"
echo "4. Update monitoring and alerting"
echo "5. Decommission AWS resources after verification"
echo ""

# Cost estimation
echo "💰 Estimated Monthly Costs:"
echo "=========================="
echo "Container Apps: ~$30-80/month (scale-to-zero)"
echo "PostgreSQL Flexible: ~$25-50/month"
echo "Blob Storage: ~$5-15/month"
echo "Redis Cache: ~$15-30/month"
echo "Document Intelligence: ~$10-25/month (usage-based)"
echo "Total: ~$85-200/month"
echo ""

echo "🎉 Migration completed successfully!"
echo "Check the migration log for details: $MIGRATION_LOG"