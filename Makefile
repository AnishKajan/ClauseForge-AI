.PHONY: help setup up down logs clean test lint format

# Default target
help:
	@echo "LexiScan Development Commands"
	@echo "============================="
	@echo "setup     - Initial development environment setup"
	@echo "up        - Start all services"
	@echo "down      - Stop all services"
	@echo "logs      - View logs from all services"
	@echo "clean     - Clean up containers and volumes"
	@echo "test      - Run tests"
	@echo "lint      - Run linting"
	@echo "format    - Format code"
	@echo "db-reset  - Reset database"
	@echo "shell-be  - Open shell in backend container"
	@echo "shell-fe  - Open shell in frontend container"

# Initial setup
setup:
	@echo "🚀 Setting up LexiScan development environment..."
	@./scripts/dev-setup.sh

# Start services
up:
	@echo "🏗️  Starting services..."
	@docker-compose up -d
	@echo "✅ Services started!"

# Stop services
down:
	@echo "🛑 Stopping services..."
	@docker-compose down
	@echo "✅ Services stopped!"

# View logs
logs:
	@docker-compose logs -f

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	@docker-compose down -v --remove-orphans
	@docker system prune -f
	@echo "✅ Cleanup complete!"

# Run tests
test:
	@echo "🧪 Running tests..."
	@docker-compose exec backend pytest
	@docker-compose exec frontend npm test

# Run linting
lint:
	@echo "🔍 Running linting..."
	@docker-compose exec backend flake8 .
	@docker-compose exec backend mypy .
	@docker-compose exec frontend npm run lint

# Format code
format:
	@echo "✨ Formatting code..."
	@docker-compose exec backend black .
	@docker-compose exec backend isort .
	@docker-compose exec frontend npm run format

# Reset database
db-reset:
	@echo "🗄️  Resetting database..."
	@docker-compose exec postgres psql -U lexiscan -d lexiscan -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	@docker-compose restart backend
	@echo "✅ Database reset complete!"

# Backend shell
shell-be:
	@docker-compose exec backend bash

# Frontend shell
shell-fe:
	@docker-compose exec frontend sh

# Health check
health:
	@echo "🏥 Checking service health..."
	@curl -f http://localhost:8000/api/health || echo "Backend unhealthy"
	@curl -f http://localhost:3000 || echo "Frontend unhealthy"