#!/bin/bash

# Create Azure Service Principal for GitHub Actions
# This script creates a service principal with the necessary permissions for CI/CD

set -e

# Configuration
RG=${RG:-"clauseforge"}
SP_NAME=${SP_NAME:-"clauseforge-github-actions"}

echo "🔐 Creating Azure Service Principal for GitHub Actions"
echo "Resource Group: $RG"
echo "Service Principal Name: $SP_NAME"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Error: Azure CLI is not installed. Please install it first."
    exit 1
fi

# Verify Azure login
echo "🔐 Verifying Azure credentials..."
az account show > /dev/null || {
    echo "❌ Error: Not logged into Azure. Run 'az login' first."
    exit 1
}

# Get subscription ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "📋 Subscription ID: $SUBSCRIPTION_ID"

# Create service principal with contributor role on the resource group
echo "👤 Creating service principal..."
SP_OUTPUT=$(az ad sp create-for-rbac \
    --name "$SP_NAME" \
    --role contributor \
    --scopes "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG" \
    --sdk-auth)

echo "✅ Service principal created successfully!"

# Display the JSON output for GitHub secrets
echo ""
echo "🔑 GitHub Secret Configuration"
echo "================================"
echo ""
echo "Add the following JSON as a GitHub secret named 'AZURE_CREDENTIALS':"
echo ""
echo "$SP_OUTPUT"
echo ""

# Extract individual values for reference
CLIENT_ID=$(echo "$SP_OUTPUT" | jq -r '.clientId')
CLIENT_SECRET=$(echo "$SP_OUTPUT" | jq -r '.clientSecret')
TENANT_ID=$(echo "$SP_OUTPUT" | jq -r '.tenantId')

echo "📋 Individual Values (for reference):"
echo "  CLIENT_ID: $CLIENT_ID"
echo "  CLIENT_SECRET: [hidden]"
echo "  TENANT_ID: $TENANT_ID"
echo "  SUBSCRIPTION_ID: $SUBSCRIPTION_ID"
echo ""

# Additional GitHub secrets needed
echo "🔧 Additional GitHub Secrets Required:"
echo "======================================"
echo ""
echo "Set these additional secrets in your GitHub repository:"
echo ""
echo "AZURE_RG=$RG"
echo "AZURE_ACR_NAME=clauseforgeacr"
echo "AZURE_APP_NAME=clauseforge-api"
echo "CLAUDE_API_KEY=your-anthropic-api-key"
echo "STRIPE_SECRET_KEY=your-stripe-secret-key"
echo "JWT_SECRET=$(openssl rand -base64 32)"
echo ""

# Instructions for GitHub
echo "📚 Setup Instructions:"
echo "====================="
echo ""
echo "1. Go to your GitHub repository"
echo "2. Navigate to Settings > Secrets and variables > Actions"
echo "3. Add the following repository secrets:"
echo "   - AZURE_CREDENTIALS: [paste the JSON output above]"
echo "   - AZURE_RG: $RG"
echo "   - AZURE_ACR_NAME: clauseforgeacr"
echo "   - AZURE_APP_NAME: clauseforge-api"
echo "   - CLAUDE_API_KEY: [your Anthropic API key]"
echo "   - STRIPE_SECRET_KEY: [your Stripe secret key]"
echo "   - JWT_SECRET: [generate with: openssl rand -base64 32]"
echo ""
echo "4. For Static Web Apps, also add:"
echo "   - AZURE_STATIC_WEB_APPS_API_TOKEN: [get from Azure portal]"
echo "   - PROD_API_URL: https://your-container-app-url"
echo "   - STAGING_API_URL: https://your-staging-container-app-url"
echo "   - APP_URL: https://your-static-web-app-url"
echo ""

# Test the service principal
echo "🧪 Testing service principal permissions..."
az login --service-principal \
    --username "$CLIENT_ID" \
    --password "$CLIENT_SECRET" \
    --tenant "$TENANT_ID" > /dev/null

az group show --name "$RG" > /dev/null && echo "✅ Service principal can access resource group"

# Login back as user
az login > /dev/null 2>&1 || echo "⚠️  Please login again with 'az login'"

echo ""
echo "🎉 Service principal setup completed successfully!"
echo "You can now use GitHub Actions to deploy to Azure."