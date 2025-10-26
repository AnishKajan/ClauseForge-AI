#!/bin/bash

# ClauseForge Azure Quick Start Script
# This script provides a quick way to get started with the Azure migration

set -e

echo "🚀 ClauseForge Azure Migration Quick Start"
echo "=========================================="

# Check if running in the correct directory
if [ ! -f "README.md" ] || [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Error: Please run this script from the ClauseForge root directory"
    exit 1
fi

# Function to prompt for user input
prompt_for_input() {
    local prompt="$1"
    local var_name="$2"
    local default_value="$3"
    
    if [ -n "$default_value" ]; then
        read -p "$prompt [$default_value]: " input
        if [ -z "$input" ]; then
            input="$default_value"
        fi
    else
        read -p "$prompt: " input
        while [ -z "$input" ]; do
            read -p "$prompt (required): " input
        done
    fi
    
    export "$var_name"="$input"
}

# Collect configuration
echo ""
echo "📋 Configuration Setup"
echo "====================="

prompt_for_input "Azure Resource Group name" "RG" "clauseforge"
prompt_for_input "Azure Location" "LOC" "eastus2"
prompt_for_input "Container Registry name" "ACR_NAME" "clauseforgeacr"
prompt_for_input "Container Apps Environment name" "ACA_ENV" "clauseforge-env"
prompt_for_input "Container App name" "APP_NAME" "clauseforge-api"
prompt_for_input "PostgreSQL server name" "DB_NAME" "clauseforge-db"
prompt_for_input "PostgreSQL admin username" "DB_ADMIN" "cfadmin"
prompt_for_input "Storage Account name" "STG_NAME" "clauseforgestorage"

echo ""
echo "🔐 API Keys and Secrets"
echo "======================"

prompt_for_input "Anthropic Claude API Key" "CLAUDE_API_KEY"
prompt_for_input "Stripe Secret Key" "STRIPE_SECRET_KEY"

# Generate JWT secret if not provided
if [ -z "$JWT_SECRET" ]; then
    JWT_SECRET=$(openssl rand -base64 32)
    echo "Generated JWT Secret: $JWT_SECRET"
fi

# Generate strong database password
DB_PASS=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
echo "Generated Database Password: $DB_PASS"

# Export all variables
export RG ACR_NAME ACA_ENV APP_NAME DB_NAME DB_ADMIN DB_PASS STG_NAME
export CLAUDE_API_KEY STRIPE_SECRET_KEY JWT_SECRET

echo ""
echo "✅ Configuration Summary"
echo "======================="
echo "Resource Group: $RG"
echo "Location: $LOC"
echo "Container Registry: $ACR_NAME"
echo "Container App: $APP_NAME"
echo "Database: $DB_NAME"
echo "Storage: $STG_NAME"
echo ""

# Confirm before proceeding
read -p "Proceed with Azure resource creation? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "❌ Migration cancelled"
    exit 0
fi

# Step 1: Create Azure resources
echo ""
echo "🏗️  Step 1: Creating Azure Resources"
echo "===================================="

if [ -f "./scripts/setup-azure-resources.sh" ]; then
    ./scripts/setup-azure-resources.sh
else
    echo "❌ Error: setup-azure-resources.sh not found"
    exit 1
fi

# Step 2: Create service principal for GitHub Actions
echo ""
echo "👤 Step 2: Creating Service Principal"
echo "====================================="

read -p "Create service principal for GitHub Actions? (y/N): " create_sp
if [[ "$create_sp" =~ ^[Yy]$ ]]; then
    if [ -f "./scripts/create-service-principal.sh" ]; then
        ./scripts/create-service-principal.sh
    else
        echo "❌ Error: create-service-principal.sh not found"
    fi
fi

# Step 3: Build and deploy initial version
echo ""
echo "🐳 Step 3: Building and Deploying Application"
echo "============================================="

read -p "Build and deploy application now? (y/N): " deploy_now
if [[ "$deploy_now" =~ ^[Yy]$ ]]; then
    echo "Building backend image..."
    az acr build --registry "$ACR_NAME" --image clauseforge-api:latest ./backend
    
    echo "Updating Container App..."
    az containerapp update \
        -g "$RG" -n "$APP_NAME" \
        --image "$ACR_NAME.azurecr.io/clauseforge-api:latest" \
        --set-env-vars \
        CLAUDE_API_KEY=secretref:claude-api-key \
        STRIPE_SECRET_KEY=secretref:stripe-secret-key \
        DATABASE_URL=secretref:database-url \
        REDIS_URL=secretref:redis-url \
        AZURE_STORAGE_CONNECTION_STRING=secretref:storage-connection \
        JWT_SECRET=secretref:jwt-secret \
        AZURE_DOC_INTEL_ENDPOINT=secretref:doc-intel-endpoint \
        AZURE_DOC_INTEL_KEY=secretref:doc-intel-key \
        ENVIRONMENT=production \
        PORT=8000
fi

# Step 4: Get application URL and test
echo ""
echo "🔍 Step 4: Testing Deployment"
echo "============================="

APP_URL=$(az containerapp show -g "$RG" -n "$APP_NAME" --query properties.configuration.ingress.fqdn -o tsv)
echo "Application URL: https://$APP_URL"

echo "Waiting for application to start..."
sleep 30

if curl -f "https://$APP_URL/api/health" > /dev/null 2>&1; then
    echo "✅ Application is running successfully!"
else
    echo "⚠️  Application may still be starting. Check logs with:"
    echo "   az containerapp logs show -g $RG -n $APP_NAME --follow"
fi

# Step 5: Next steps
echo ""
echo "🎯 Next Steps"
echo "============"
echo ""
echo "1. 📄 Enable pgvector extension in PostgreSQL:"
echo "   psql \"postgresql://$DB_ADMIN:$DB_PASS@$DB_NAME.postgres.database.azure.com:5432/postgres\""
echo "   => CREATE EXTENSION IF NOT EXISTS vector;"
echo ""
echo "2. 🔐 Add GitHub Secrets for CI/CD:"
echo "   - AZURE_CREDENTIALS (from service principal output)"
echo "   - AZURE_RG=$RG"
echo "   - AZURE_ACR_NAME=$ACR_NAME"
echo "   - AZURE_APP_NAME=$APP_NAME"
echo "   - CLAUDE_API_KEY=$CLAUDE_API_KEY"
echo "   - STRIPE_SECRET_KEY=$STRIPE_SECRET_KEY"
echo "   - JWT_SECRET=$JWT_SECRET"
echo ""
echo "3. 🌐 Set up frontend deployment:"
echo "   - Create Azure Static Web App"
echo "   - Connect to GitHub repository"
echo "   - Set NEXT_PUBLIC_API_URL=https://$APP_URL"
echo ""
echo "4. 📊 Set up monitoring:"
echo "   - Configure Azure Monitor alerts"
echo "   - Set up cost monitoring"
echo "   - Review Container Apps scaling rules"
echo ""
echo "5. 🔄 Migrate data from AWS (if applicable):"
echo "   - Run ./scripts/migrate-to-azure.sh"
echo "   - Verify data integrity"
echo "   - Update DNS records"
echo ""

# Save configuration for future reference
cat > .azure-config << EOF
# Azure Configuration (generated by azure-quickstart.sh)
export RG="$RG"
export LOC="$LOC"
export ACR_NAME="$ACR_NAME"
export ACA_ENV="$ACA_ENV"
export APP_NAME="$APP_NAME"
export DB_NAME="$DB_NAME"
export DB_ADMIN="$DB_ADMIN"
export DB_PASS="$DB_PASS"
export STG_NAME="$STG_NAME"
export APP_URL="$APP_URL"
EOF

echo "📁 Configuration saved to .azure-config"
echo "   Source this file to reload variables: source .azure-config"
echo ""
echo "🎉 Azure Quick Start completed successfully!"
echo "   Application URL: https://$APP_URL"
echo "   Resource Group: $RG"
echo ""
echo "📚 For detailed migration steps, see:"
echo "   - AZURE_MIGRATION.md"
echo "   - MIGRATION_CHECKLIST.md"