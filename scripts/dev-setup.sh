#!/bin/bash

# Development environment setup script
set -e

echo "🚀 Setting up LexiScan development environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. Please update it with your actual API keys."
fi

# Build and start services
echo "🏗️  Building and starting services..."
docker-compose up -d --build

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🔍 Checking service health..."
docker-compose ps

# Install frontend dependencies if running locally
if [ -d "frontend" ] && [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Install backend dependencies if running locally
if [ -d "backend" ] && [ ! -d "backend/__pycache__" ]; then
    echo "🐍 Installing backend dependencies..."
    cd backend
    pip install -r requirements.txt
    cd ..
fi

echo "✅ Development environment setup complete!"
echo ""
echo "🌐 Services are available at:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo "   PostgreSQL: localhost:5432"
echo "   Redis: localhost:6379"
echo "   LocalStack: http://localhost:4566"
echo ""
echo "📚 Next steps:"
echo "   1. Update .env file with your API keys"
echo "   2. Visit http://localhost:3000 to see the application"
echo "   3. Check http://localhost:8000/docs for API documentation"
echo ""
echo "🛠️  Useful commands:"
echo "   docker-compose logs -f [service]  # View logs"
echo "   docker-compose restart [service] # Restart service"
echo "   docker-compose down              # Stop all services"