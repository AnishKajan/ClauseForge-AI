#!/bin/bash

# Test script to verify the project structure is set up correctly
set -e

echo "🧪 Testing LexiScan project structure..."

# Test backend structure
echo "✅ Checking backend structure..."
test -f backend/main.py || { echo "❌ backend/main.py missing"; exit 1; }
test -f backend/requirements.txt || { echo "❌ backend/requirements.txt missing"; exit 1; }
test -d backend/core || { echo "❌ backend/core directory missing"; exit 1; }
test -d backend/routers || { echo "❌ backend/routers directory missing"; exit 1; }
test -d backend/services || { echo "❌ backend/services directory missing"; exit 1; }
test -d backend/models || { echo "❌ backend/models directory missing"; exit 1; }

# Test frontend structure
echo "✅ Checking frontend structure..."
test -f frontend/package.json || { echo "❌ frontend/package.json missing"; exit 1; }
test -f frontend/next.config.js || { echo "❌ frontend/next.config.js missing"; exit 1; }
test -d frontend/src/app || { echo "❌ frontend/src/app directory missing"; exit 1; }
test -d frontend/src/components || { echo "❌ frontend/src/components directory missing"; exit 1; }
test -d frontend/src/lib || { echo "❌ frontend/src/lib directory missing"; exit 1; }

# Test Docker configuration
echo "✅ Checking Docker configuration..."
test -f docker-compose.yml || { echo "❌ docker-compose.yml missing"; exit 1; }
test -f backend/Dockerfile || { echo "❌ backend/Dockerfile missing"; exit 1; }
test -f frontend/Dockerfile || { echo "❌ frontend/Dockerfile missing"; exit 1; }

# Test environment configuration
echo "✅ Checking environment configuration..."
test -f .env || { echo "❌ .env file missing"; exit 1; }
test -f .env.example || { echo "❌ .env.example missing"; exit 1; }

# Test scripts
echo "✅ Checking scripts..."
test -f scripts/dev-setup.sh || { echo "❌ scripts/dev-setup.sh missing"; exit 1; }
test -f scripts/init-db.sql || { echo "❌ scripts/init-db.sql missing"; exit 1; }
test -f scripts/localstack-init.sh || { echo "❌ scripts/localstack-init.sh missing"; exit 1; }

# Test Makefile
echo "✅ Checking Makefile..."
test -f Makefile || { echo "❌ Makefile missing"; exit 1; }

echo "🎉 All project structure tests passed!"
echo ""
echo "📋 Project structure summary:"
echo "   ✅ Backend FastAPI application with proper structure"
echo "   ✅ Frontend Next.js application with App Router"
echo "   ✅ Docker Compose configuration for local development"
echo "   ✅ Environment variables and configuration"
echo "   ✅ Development scripts and utilities"
echo "   ✅ Database initialization scripts"
echo "   ✅ LocalStack AWS services setup"
echo ""
echo "🚀 Ready to start development!"
echo "   Run 'make setup' to initialize the development environment"