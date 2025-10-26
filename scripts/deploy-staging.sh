#!/bin/bash

# LexiScan Staging Deployment Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
SKIP_BUILD=false
SKIP_TESTS=false
CLEAN_VOLUMES=false
DETACHED=true

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --skip-build                    Skip building Docker images"
    echo "  --skip-tests                    Skip running tests"
    echo "  --clean-volumes                 Remove existing volumes before deployment"
    echo "  --foreground                    Run in foreground (don't detach)"
    echo "  -h, --help                      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                              Deploy staging environment"
    echo "  $0 --skip-build                 Deploy without rebuilding images"
    echo "  $0 --clean-volumes              Deploy with fresh volumes"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --clean-volumes)
            CLEAN_VOLUMES=true
            shift
            ;;
        --foreground)
            DETACHED=false
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    local missing_tools=()
    
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        missing_tools+=("docker-compose")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    print_success "All prerequisites satisfied"
}

# Run tests
run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        print_warning "Skipping tests"
        return
    fi
    
    print_status "Running tests..."
    
    # Backend tests
    if [[ -f "backend/requirements.txt" ]]; then
        print_status "Running backend tests..."
        cd backend
        python -m pytest --cov=. --cov-report=term-missing || {
            print_error "Backend tests failed"
            exit 1
        }
        cd ..
    fi
    
    # Frontend tests
    if [[ -f "frontend/package.json" ]]; then
        print_status "Running frontend tests..."
        cd frontend
        npm test -- --coverage --watchAll=false || {
            print_error "Frontend tests failed"
            exit 1
        }
        cd ..
    fi
    
    print_success "All tests passed"
}

# Clean up existing deployment
cleanup_existing() {
    print_status "Cleaning up existing staging deployment..."
    
    # Stop and remove containers
    docker-compose -f docker-compose.staging.yml down --remove-orphans || true
    
    # Remove volumes if requested
    if [[ "$CLEAN_VOLUMES" == "true" ]]; then
        print_warning "Removing existing volumes..."
        docker-compose -f docker-compose.staging.yml down -v || true
        
        # Remove named volumes
        docker volume rm lexiscan-staging_postgres_staging_data 2>/dev/null || true
        docker volume rm lexiscan-staging_redis_staging_data 2>/dev/null || true
        docker volume rm lexiscan-staging_localstack_staging_data 2>/dev/null || true
        docker volume rm lexiscan-staging_prometheus_staging_data 2>/dev/null || true
        docker volume rm lexiscan-staging_grafana_staging_data 2>/dev/null || true
    fi
    
    # Clean up unused images and networks
    docker system prune -f || true
}

# Build images
build_images() {
    if [[ "$SKIP_BUILD" == "true" ]]; then
        print_warning "Skipping image build"
        return
    fi
    
    print_status "Building Docker images for staging..."
    
    # Build images
    docker-compose -f docker-compose.staging.yml build --no-cache
    
    print_success "Docker images built successfully"
}

# Initialize environment
init_environment() {
    print_status "Initializing staging environment..."
    
    # Create .env.staging.local if it doesn't exist
    if [[ ! -f ".env.staging.local" ]]; then
        print_status "Creating .env.staging.local from template..."
        cp .env.staging .env.staging.local
        print_warning "Please edit .env.staging.local with your actual configuration values"
    fi
    
    # Create necessary directories
    mkdir -p nginx/ssl
    mkdir -p backend/logs
    mkdir -p monitoring/grafana/dashboards
    mkdir -p monitoring/grafana/datasources
    
    # Create Grafana datasource configuration
    cat > monitoring/grafana/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF
    
    print_success "Environment initialized"
}

# Deploy services
deploy_services() {
    print_status "Deploying staging services..."
    
    # Start services
    if [[ "$DETACHED" == "true" ]]; then
        docker-compose -f docker-compose.staging.yml --env-file .env.staging.local up -d
    else
        docker-compose -f docker-compose.staging.yml --env-file .env.staging.local up
    fi
    
    if [[ "$DETACHED" == "true" ]]; then
        print_success "Staging services started in detached mode"
    fi
}

# Wait for services to be ready
wait_for_services() {
    if [[ "$DETACHED" != "true" ]]; then
        return
    fi
    
    print_status "Waiting for services to be ready..."
    
    # Wait for database
    print_status "Waiting for PostgreSQL..."
    timeout=60
    while ! docker-compose -f docker-compose.staging.yml exec -T postgres pg_isready -U lexiscan -d lexiscan_staging &>/dev/null; do
        sleep 2
        timeout=$((timeout - 2))
        if [[ $timeout -le 0 ]]; then
            print_error "PostgreSQL failed to start within 60 seconds"
            exit 1
        fi
    done
    
    # Wait for Redis
    print_status "Waiting for Redis..."
    timeout=30
    while ! docker-compose -f docker-compose.staging.yml exec -T redis redis-cli ping &>/dev/null; do
        sleep 2
        timeout=$((timeout - 2))
        if [[ $timeout -le 0 ]]; then
            print_error "Redis failed to start within 30 seconds"
            exit 1
        fi
    done
    
    # Wait for LocalStack
    print_status "Waiting for LocalStack..."
    timeout=60
    while ! curl -f http://localhost:4567/_localstack/health &>/dev/null; do
        sleep 2
        timeout=$((timeout - 2))
        if [[ $timeout -le 0 ]]; then
            print_error "LocalStack failed to start within 60 seconds"
            exit 1
        fi
    done
    
    # Wait for backend
    print_status "Waiting for backend API..."
    timeout=120
    while ! curl -f http://localhost:8001/api/health &>/dev/null; do
        sleep 2
        timeout=$((timeout - 2))
        if [[ $timeout -le 0 ]]; then
            print_error "Backend API failed to start within 120 seconds"
            exit 1
        fi
    done
    
    # Wait for frontend
    print_status "Waiting for frontend..."
    timeout=60
    while ! curl -f http://localhost:3001/ &>/dev/null; do
        sleep 2
        timeout=$((timeout - 2))
        if [[ $timeout -le 0 ]]; then
            print_error "Frontend failed to start within 60 seconds"
            exit 1
        fi
    done
    
    print_success "All services are ready"
}

# Run smoke tests
run_smoke_tests() {
    if [[ "$DETACHED" != "true" ]]; then
        return
    fi
    
    print_status "Running smoke tests..."
    
    # Test health endpoints
    if curl -f http://localhost:8001/api/health &>/dev/null; then
        print_success "✓ Backend health check passed"
    else
        print_error "✗ Backend health check failed"
        exit 1
    fi
    
    if curl -f http://localhost:8001/api/health/detailed &>/dev/null; then
        print_success "✓ Backend detailed health check passed"
    else
        print_warning "⚠ Backend detailed health check failed (some dependencies may be unavailable)"
    fi
    
    if curl -f http://localhost:3001/ &>/dev/null; then
        print_success "✓ Frontend health check passed"
    else
        print_error "✗ Frontend health check failed"
        exit 1
    fi
    
    if curl -f http://localhost:80/health &>/dev/null; then
        print_success "✓ Nginx health check passed"
    else
        print_error "✗ Nginx health check failed"
        exit 1
    fi
    
    print_success "All smoke tests passed"
}

# Show deployment info
show_deployment_info() {
    if [[ "$DETACHED" != "true" ]]; then
        return
    fi
    
    print_success "🚀 Staging deployment completed successfully!"
    echo ""
    echo "Access URLs:"
    echo "  Frontend:    http://localhost:3001"
    echo "  Backend API: http://localhost:8001"
    echo "  Nginx:       http://localhost:80"
    echo "  Grafana:     http://localhost:3001 (admin/staging_admin)"
    echo "  Prometheus:  http://localhost:9091"
    echo ""
    echo "Useful commands:"
    echo "  View logs:           docker-compose -f docker-compose.staging.yml logs -f"
    echo "  Stop services:       docker-compose -f docker-compose.staging.yml down"
    echo "  Restart service:     docker-compose -f docker-compose.staging.yml restart <service>"
    echo "  Shell into backend:  docker-compose -f docker-compose.staging.yml exec backend bash"
    echo "  Database shell:      docker-compose -f docker-compose.staging.yml exec postgres psql -U lexiscan -d lexiscan_staging"
    echo ""
}

# Main deployment function
main() {
    print_status "Starting LexiScan staging deployment..."
    
    check_prerequisites
    run_tests
    cleanup_existing
    init_environment
    build_images
    deploy_services
    wait_for_services
    run_smoke_tests
    show_deployment_info
}

# Handle script interruption
trap 'print_error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main