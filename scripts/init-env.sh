#!/bin/bash

# Initialize environment configuration for LexiScan

set -e

echo "Initializing LexiScan environment configuration..."

# Copy .env.example to .env if it doesn't exist
if [[ ! -f ".env" ]]; then
    cp .env.example .env
    echo "✓ Created .env file from template"
    echo ""
    echo "⚠ IMPORTANT: Please edit .env file and configure the following:"
    echo "  - Database credentials"
    echo "  - AWS credentials and region"
    echo "  - API keys (Anthropic, OpenAI, Stripe)"
    echo "  - JWT secrets"
    echo ""
    echo "Required API keys to obtain:"
    echo "  1. Anthropic Claude API: https://console.anthropic.com"
    echo "  2. OpenAI API: https://platform.openai.com/api-keys"
    echo "  3. Stripe API: https://dashboard.stripe.com/apikeys"
    echo ""
    echo "Run './scripts/verify-prerequisites.sh' after configuration to verify setup."
else
    echo "✓ .env file already exists"
fi

# Generate JWT secrets if they're still default values
if grep -q "your-super-secret-jwt-signing-key-min-32-chars" .env; then
    JWT_SECRET=$(openssl rand -base64 32)
    sed -i.bak "s|your-super-secret-jwt-signing-key-min-32-chars|$JWT_SECRET|" .env
    echo "✓ Generated JWT_SECRET"
fi

if grep -q "your-nextauth-secret-key-min-32-chars" .env; then
    NEXTAUTH_SECRET=$(openssl rand -base64 32)
    sed -i.bak "s|your-nextauth-secret-key-min-32-chars|$NEXTAUTH_SECRET|" .env
    echo "✓ Generated NEXTAUTH_SECRET"
fi

# Clean up backup files
rm -f .env.bak

echo ""
echo "Environment initialization complete!"
echo "Next steps:"
echo "1. Edit .env file with your API keys and credentials"
echo "2. Run './scripts/verify-prerequisites.sh' to verify setup"
echo "3. Run './aws-setup/setup-aws-resources.sh' to create AWS resources"