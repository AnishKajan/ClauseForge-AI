#!/bin/bash

# LexiScan Deployment Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=""
AWS_REGION="us-east-1"
SKIP_TESTS=false
SKIP_BUILD=false
DRY_RUN=false

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
    echo "  -e, --environment ENVIRONMENT    Target environment (staging|production)"
    echo "  -r, --region REGION             AWS region (default: us-east-1)"
    echo "  --skip-tests                    Skip running tests"
    echo "  --skip-build                    Skip building Docker images"
    echo "  --dry-run                       Show what would be deployed without applying"
    echo "  -h, --help                      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e staging                   Deploy to staging"
    echo "  $0 -e production --skip-tests   Deploy to production without tests"
    echo "  $0 -e staging --dry-run         Show staging deployment plan"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
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

# Validate required parameters
if [[ -z "$ENVIRONMENT" ]]; then
    print_error "Environment is required. Use -e staging or -e production"
    show_usage
    exit 1
fi

if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    print_error "Environment must be either 'staging' or 'production'"
    exit 1
fi

# Check required tools
check_requirements() {
    print_status "Checking requirements..."
    
    local missing_tools=()
    
    if ! command -v aws &> /dev/null; then
        missing_tools+=("aws-cli")
    fi
    
    if ! command -v terraform &> /dev/null; then
        missing_tools+=("terraform")
    fi
    
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured or invalid"
        exit 1
    fi
    
    print_success "All requirements satisfied"
}

# Run tests
run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        print_warning "Skipping tests"
        return
    fi
    
    print_status "Running tests..."
    
    # Backend tests
    print_status "Running backend tests..."
    cd backend
    if [[ -f "requirements.txt" ]]; then
        python -m pytest --cov=. --cov-report=term-missing
    else
        print_warning "Backend requirements.txt not found, skipping backend tests"
    fi
    cd ..
    
    # Frontend tests
    print_status "Running frontend tests..."
    cd frontend
    if [[ -f "package.json" ]]; then
        npm test -- --coverage --watchAll=false
    else
        print_warning "Frontend package.json not found, skipping frontend tests"
    fi
    cd ..
    
    print_success "All tests passed"
}

# Build and push Docker images
build_and_push_images() {
    if [[ "$SKIP_BUILD" == "true" ]]; then
        print_warning "Skipping Docker image build"
        return
    fi
    
    print_status "Building and pushing Docker images..."
    
    # Get AWS account ID
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    
    # Login to ECR
    print_status "Logging in to Amazon ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
    
    # Create ECR repositories if they don't exist
    aws ecr describe-repositories --repository-names lexiscan-backend --region $AWS_REGION 2>/dev/null || \
        aws ecr create-repository --repository-name lexiscan-backend --region $AWS_REGION
    
    aws ecr describe-repositories --repository-names lexiscan-frontend --region $AWS_REGION 2>/dev/null || \
        aws ecr create-repository --repository-name lexiscan-frontend --region $AWS_REGION
    
    # Build and push backend image
    print_status "Building backend image..."
    BACKEND_IMAGE_TAG="${ECR_REGISTRY}/lexiscan-backend:${ENVIRONMENT}-$(git rev-parse --short HEAD)"
    docker build -t $BACKEND_IMAGE_TAG ./backend
    docker push $BACKEND_IMAGE_TAG
    
    # Build and push frontend image
    print_status "Building frontend image..."
    FRONTEND_IMAGE_TAG="${ECR_REGISTRY}/lexiscan-frontend:${ENVIRONMENT}-$(git rev-parse --short HEAD)"
    docker build -t $FRONTEND_IMAGE_TAG ./frontend
    docker push $FRONTEND_IMAGE_TAG
    
    print_success "Docker images built and pushed successfully"
    
    # Export image URIs for Terraform
    export TF_VAR_backend_image_uri=$BACKEND_IMAGE_TAG
    export TF_VAR_frontend_image_uri=$FRONTEND_IMAGE_TAG
}

# Deploy infrastructure
deploy_infrastructure() {
    print_status "Deploying infrastructure to $ENVIRONMENT..."
    
    cd infrastructure/terraform
    
    # Initialize Terraform
    print_status "Initializing Terraform..."
    terraform init -backend-config=backend-config/${ENVIRONMENT}.hcl
    
    # Plan deployment
    print_status "Planning Terraform deployment..."
    terraform plan -var-file=environments/${ENVIRONMENT}.tfvars \
        -var="environment=$ENVIRONMENT" \
        -var="aws_region=$AWS_REGION" \
        -out=tfplan
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_warning "Dry run mode - not applying changes"
        cd ../..
        return
    fi
    
    # Apply deployment
    print_status "Applying Terraform deployment..."
    terraform apply tfplan
    
    # Get outputs
    print_status "Getting deployment outputs..."
    ALB_DNS=$(terraform output -raw alb_dns_name)
    APP_URL=$(terraform output -raw application_url)
    
    cd ../..
    
    print_success "Infrastructure deployed successfully"
    print_success "Application URL: $APP_URL"
    print_success "Load Balancer DNS: $ALB_DNS"
}

# Run smoke tests
run_smoke_tests() {
    print_status "Running smoke tests..."
    
    cd infrastructure/terraform
    APP_URL=$(terraform output -raw application_url)
    cd ../..
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 60
    
    # Test health endpoints
    print_status "Testing health endpoints..."
    
    if curl -f "${APP_URL}/api/health" > /dev/null 2>&1; then
        print_success "API health check passed"
    else
        print_error "API health check failed"
        exit 1
    fi
    
    if curl -f "${APP_URL}/" > /dev/null 2>&1; then
        print_success "Frontend health check passed"
    else
        print_error "Frontend health check failed"
        exit 1
    fi
    
    print_success "All smoke tests passed"
}

# Main deployment flow
main() {
    print_status "Starting deployment to $ENVIRONMENT environment"
    print_status "AWS Region: $AWS_REGION"
    
    check_requirements
    run_tests
    build_and_push_images
    deploy_infrastructure
    
    if [[ "$DRY_RUN" != "true" ]]; then
        run_smoke_tests
        print_success "🚀 Deployment to $ENVIRONMENT completed successfully!"
    else
        print_success "🔍 Dry run completed - no changes applied"
    fi
}

# Run main function
main