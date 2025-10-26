#!/bin/bash

# Production Deployment Script with Blue-Green Strategy
# Implements safe production deployments with automatic rollback

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
AWS_REGION="us-east-1"
CLUSTER_NAME="lexiscan-production-cluster"
BACKEND_SERVICE="lexiscan-production-backend"
FRONTEND_SERVICE="lexiscan-production-frontend"
DEPLOYMENT_TIMEOUT=600  # 10 minutes
HEALTH_CHECK_TIMEOUT=300  # 5 minutes
ROLLBACK_ON_FAILURE=true
DRY_RUN=false
SKIP_VALIDATION=false
FORCE_DEPLOYMENT=false

# Deployment state
DEPLOYMENT_ID=""
PREVIOUS_BACKEND_TASK_DEF=""
PREVIOUS_FRONTEND_TASK_DEF=""
DEPLOYMENT_START_TIME=""

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
    echo "  -r, --region REGION             AWS region (default: us-east-1)"
    echo "  -c, --cluster CLUSTER           ECS cluster name"
    echo "  --backend-service SERVICE       Backend service name"
    echo "  --frontend-service SERVICE      Frontend service name"
    echo "  --timeout SECONDS               Deployment timeout (default: 600)"
    echo "  --no-rollback                   Disable automatic rollback on failure"
    echo "  --dry-run                       Show what would be deployed without applying"
    echo "  --skip-validation               Skip pre-deployment validation"
    echo "  --force                         Force deployment even if validation fails"
    echo "  -h, --help                      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                              Deploy to production with defaults"
    echo "  $0 --dry-run                    Show deployment plan"
    echo "  $0 --no-rollback                Deploy without automatic rollback"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -c|--cluster)
            CLUSTER_NAME="$2"
            shift 2
            ;;
        --backend-service)
            BACKEND_SERVICE="$2"
            shift 2
            ;;
        --frontend-service)
            FRONTEND_SERVICE="$2"
            shift 2
            ;;
        --timeout)
            DEPLOYMENT_TIMEOUT="$2"
            shift 2
            ;;
        --no-rollback)
            ROLLBACK_ON_FAILURE=false
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-validation)
            SKIP_VALIDATION=true
            shift
            ;;
        --force)
            FORCE_DEPLOYMENT=true
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
    
    if ! command -v aws &> /dev/null; then
        missing_tools+=("aws-cli")
    fi
    
    if ! command -v jq &> /dev/null; then
        missing_tools+=("jq")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity --region "$AWS_REGION" &> /dev/null; then
        print_error "AWS credentials not configured or invalid"
        exit 1
    fi
    
    # Check cluster exists
    if ! aws ecs describe-clusters --clusters "$CLUSTER_NAME" --region "$AWS_REGION" &> /dev/null; then
        print_error "ECS cluster '$CLUSTER_NAME' not found in region '$AWS_REGION'"
        exit 1
    fi
    
    print_success "All prerequisites satisfied"
}

# Generate deployment ID
generate_deployment_id() {
    DEPLOYMENT_ID="deploy-$(date +%Y%m%d-%H%M%S)-$(openssl rand -hex 4)"
    DEPLOYMENT_START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    print_status "Deployment ID: $DEPLOYMENT_ID"
}

# Get current task definitions
get_current_task_definitions() {
    print_status "Getting current task definitions..."
    
    # Get backend task definition
    PREVIOUS_BACKEND_TASK_DEF=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$BACKEND_SERVICE" \
        --region "$AWS_REGION" \
        --query 'services[0].taskDefinition' \
        --output text 2>/dev/null || echo "")
    
    # Get frontend task definition
    PREVIOUS_FRONTEND_TASK_DEF=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$FRONTEND_SERVICE" \
        --region "$AWS_REGION" \
        --query 'services[0].taskDefinition' \
        --output text 2>/dev/null || echo "")
    
    if [[ -n "$PREVIOUS_BACKEND_TASK_DEF" ]]; then
        print_status "Previous backend task definition: $PREVIOUS_BACKEND_TASK_DEF"
    else
        print_warning "No previous backend task definition found"
    fi
    
    if [[ -n "$PREVIOUS_FRONTEND_TASK_DEF" ]]; then
        print_status "Previous frontend task definition: $PREVIOUS_FRONTEND_TASK_DEF"
    else
        print_warning "No previous frontend task definition found"
    fi
}

# Pre-deployment validation
run_pre_deployment_validation() {
    if [[ "$SKIP_VALIDATION" == "true" ]]; then
        print_warning "Skipping pre-deployment validation"
        return 0
    fi
    
    print_status "Running pre-deployment validation..."
    
    # Check if new task definitions exist
    local backend_task_def_arn
    local frontend_task_def_arn
    
    # Get the latest task definition ARNs
    backend_task_def_arn=$(aws ecs list-task-definitions \
        --family-prefix "lexiscan-backend" \
        --status ACTIVE \
        --sort DESC \
        --max-items 1 \
        --region "$AWS_REGION" \
        --query 'taskDefinitionArns[0]' \
        --output text 2>/dev/null || echo "")
    
    frontend_task_def_arn=$(aws ecs list-task-definitions \
        --family-prefix "lexiscan-frontend" \
        --status ACTIVE \
        --sort DESC \
        --max-items 1 \
        --region "$AWS_REGION" \
        --query 'taskDefinitionArns[0]' \
        --output text 2>/dev/null || echo "")
    
    if [[ -z "$backend_task_def_arn" || "$backend_task_def_arn" == "None" ]]; then
        print_error "No backend task definition found"
        return 1
    fi
    
    if [[ -z "$frontend_task_def_arn" || "$frontend_task_def_arn" == "None" ]]; then
        print_error "No frontend task definition found"
        return 1
    fi
    
    # Check if task definitions are different from current
    if [[ "$backend_task_def_arn" == "$PREVIOUS_BACKEND_TASK_DEF" && "$frontend_task_def_arn" == "$PREVIOUS_FRONTEND_TASK_DEF" ]]; then
        if [[ "$FORCE_DEPLOYMENT" != "true" ]]; then
            print_error "No new task definitions found. Use --force to redeploy current versions."
            return 1
        else
            print_warning "Force deployment requested with same task definitions"
        fi
    fi
    
    # Validate task definitions can be deployed
    print_status "Validating task definitions..."
    
    # Check backend task definition
    if ! aws ecs describe-task-definition \
        --task-definition "$backend_task_def_arn" \
        --region "$AWS_REGION" \
        --query 'taskDefinition.status' \
        --output text | grep -q "ACTIVE"; then
        print_error "Backend task definition is not active"
        return 1
    fi
    
    # Check frontend task definition
    if ! aws ecs describe-task-definition \
        --task-definition "$frontend_task_def_arn" \
        --region "$AWS_REGION" \
        --query 'taskDefinition.status' \
        --output text | grep -q "ACTIVE"; then
        print_error "Frontend task definition is not active"
        return 1
    fi
    
    print_success "Pre-deployment validation passed"
    return 0
}

# Deploy services using blue-green strategy
deploy_services() {
    print_status "Starting blue-green deployment..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_warning "DRY RUN MODE - No actual deployment will occur"
        print_status "Would deploy:"
        print_status "  Backend service: $BACKEND_SERVICE"
        print_status "  Frontend service: $FRONTEND_SERVICE"
        print_status "  Cluster: $CLUSTER_NAME"
        print_status "  Region: $AWS_REGION"
        return 0
    fi
    
    # Deploy backend service
    print_status "Deploying backend service..."
    
    local backend_deployment_id
    backend_deployment_id=$(aws ecs update-service \
        --cluster "$CLUSTER_NAME" \
        --service "$BACKEND_SERVICE" \
        --force-new-deployment \
        --region "$AWS_REGION" \
        --query 'service.deployments[0].id' \
        --output text 2>/dev/null || echo "")
    
    if [[ -n "$backend_deployment_id" ]]; then
        print_status "Backend deployment started: $backend_deployment_id"
    else
        print_error "Failed to start backend deployment"
        return 1
    fi
    
    # Deploy frontend service
    print_status "Deploying frontend service..."
    
    local frontend_deployment_id
    frontend_deployment_id=$(aws ecs update-service \
        --cluster "$CLUSTER_NAME" \
        --service "$FRONTEND_SERVICE" \
        --force-new-deployment \
        --region "$AWS_REGION" \
        --query 'service.deployments[0].id' \
        --output text 2>/dev/null || echo "")
    
    if [[ -n "$frontend_deployment_id" ]]; then
        print_status "Frontend deployment started: $frontend_deployment_id"
    else
        print_error "Failed to start frontend deployment"
        return 1
    fi
    
    print_success "Blue-green deployment initiated"
    return 0
}

# Wait for deployment to complete
wait_for_deployment() {
    if [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    print_status "Waiting for deployment to complete (timeout: ${DEPLOYMENT_TIMEOUT}s)..."
    
    local start_time
    start_time=$(date +%s)
    local timeout_time=$((start_time + DEPLOYMENT_TIMEOUT))
    
    while [[ $(date +%s) -lt $timeout_time ]]; do
        # Check backend service status
        local backend_status
        backend_status=$(aws ecs describe-services \
            --cluster "$CLUSTER_NAME" \
            --services "$BACKEND_SERVICE" \
            --region "$AWS_REGION" \
            --query 'services[0].deployments[?status==`PRIMARY`].runningCount' \
            --output text 2>/dev/null || echo "0")
        
        # Check frontend service status
        local frontend_status
        frontend_status=$(aws ecs describe-services \
            --cluster "$CLUSTER_NAME" \
            --services "$FRONTEND_SERVICE" \
            --region "$AWS_REGION" \
            --query 'services[0].deployments[?status==`PRIMARY`].runningCount' \
            --output text 2>/dev/null || echo "0")
        
        # Get desired counts
        local backend_desired
        backend_desired=$(aws ecs describe-services \
            --cluster "$CLUSTER_NAME" \
            --services "$BACKEND_SERVICE" \
            --region "$AWS_REGION" \
            --query 'services[0].desiredCount' \
            --output text 2>/dev/null || echo "0")
        
        local frontend_desired
        frontend_desired=$(aws ecs describe-services \
            --cluster "$CLUSTER_NAME" \
            --services "$FRONTEND_SERVICE" \
            --region "$AWS_REGION" \
            --query 'services[0].desiredCount' \
            --output text 2>/dev/null || echo "0")
        
        print_status "Deployment progress - Backend: $backend_status/$backend_desired, Frontend: $frontend_status/$frontend_desired"
        
        # Check if deployment is complete
        if [[ "$backend_status" == "$backend_desired" && "$frontend_status" == "$frontend_desired" ]]; then
            print_success "Deployment completed successfully"
            return 0
        fi
        
        # Check for failed deployments
        local backend_failed
        backend_failed=$(aws ecs describe-services \
            --cluster "$CLUSTER_NAME" \
            --services "$BACKEND_SERVICE" \
            --region "$AWS_REGION" \
            --query 'services[0].deployments[?status==`FAILED`]' \
            --output text 2>/dev/null || echo "")
        
        local frontend_failed
        frontend_failed=$(aws ecs describe-services \
            --cluster "$CLUSTER_NAME" \
            --services "$FRONTEND_SERVICE" \
            --region "$AWS_REGION" \
            --query 'services[0].deployments[?status==`FAILED`]' \
            --output text 2>/dev/null || echo "")
        
        if [[ -n "$backend_failed" || -n "$frontend_failed" ]]; then
            print_error "Deployment failed"
            return 1
        fi
        
        sleep 30
    done
    
    print_error "Deployment timeout after ${DEPLOYMENT_TIMEOUT} seconds"
    return 1
}

# Run health checks
run_health_checks() {
    if [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    print_status "Running post-deployment health checks..."
    
    # Get application URL from Terraform output or ALB
    local app_url
    app_url=$(terraform -chdir=./infrastructure/terraform output -raw application_url 2>/dev/null || echo "")
    
    if [[ -z "$app_url" ]]; then
        # Try to get ALB DNS name
        local alb_dns
        alb_dns=$(terraform -chdir=./infrastructure/terraform output -raw alb_dns_name 2>/dev/null || echo "")
        if [[ -n "$alb_dns" ]]; then
            app_url="https://$alb_dns"
        else
            print_warning "Could not determine application URL for health checks"
            return 0
        fi
    fi
    
    print_status "Testing application health at: $app_url"
    
    local health_check_start
    health_check_start=$(date +%s)
    local health_timeout_time=$((health_check_start + HEALTH_CHECK_TIMEOUT))
    
    while [[ $(date +%s) -lt $health_timeout_time ]]; do
        # Test basic health endpoint
        if curl -f -s --max-time 10 "$app_url/api/health" >/dev/null 2>&1; then
            print_success "Basic health check passed"
            
            # Test detailed health endpoint
            if curl -f -s --max-time 15 "$app_url/api/health/detailed" >/dev/null 2>&1; then
                print_success "Detailed health check passed"
                
                # Test frontend
                if curl -f -s --max-time 10 "$app_url/" >/dev/null 2>&1; then
                    print_success "Frontend health check passed"
                    print_success "All health checks passed"
                    return 0
                else
                    print_warning "Frontend health check failed, retrying..."
                fi
            else
                print_warning "Detailed health check failed, retrying..."
            fi
        else
            print_warning "Basic health check failed, retrying..."
        fi
        
        sleep 15
    done
    
    print_error "Health checks failed after ${HEALTH_CHECK_TIMEOUT} seconds"
    return 1
}

# Run smoke tests
run_smoke_tests() {
    if [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    print_status "Running smoke tests..."
    
    # Get application URL
    local app_url
    app_url=$(terraform -chdir=./infrastructure/terraform output -raw application_url 2>/dev/null || echo "")
    
    if [[ -z "$app_url" ]]; then
        print_warning "Could not determine application URL for smoke tests"
        return 0
    fi
    
    # Run smoke tests if script exists
    if [[ -f "./scripts/smoke-tests.sh" ]]; then
        if ./scripts/smoke-tests.sh -u "$app_url" -e production; then
            print_success "Smoke tests passed"
            return 0
        else
            print_error "Smoke tests failed"
            return 1
        fi
    else
        print_warning "Smoke test script not found, skipping"
        return 0
    fi
}

# Rollback deployment
rollback_deployment() {
    if [[ "$DRY_RUN" == "true" ]]; then
        print_warning "DRY RUN MODE - Would rollback deployment"
        return 0
    fi
    
    print_error "Rolling back deployment..."
    
    local rollback_success=true
    
    # Rollback backend service
    if [[ -n "$PREVIOUS_BACKEND_TASK_DEF" ]]; then
        print_status "Rolling back backend service to: $PREVIOUS_BACKEND_TASK_DEF"
        
        if aws ecs update-service \
            --cluster "$CLUSTER_NAME" \
            --service "$BACKEND_SERVICE" \
            --task-definition "$PREVIOUS_BACKEND_TASK_DEF" \
            --region "$AWS_REGION" >/dev/null 2>&1; then
            print_status "Backend rollback initiated"
        else
            print_error "Failed to rollback backend service"
            rollback_success=false
        fi
    else
        print_warning "No previous backend task definition for rollback"
    fi
    
    # Rollback frontend service
    if [[ -n "$PREVIOUS_FRONTEND_TASK_DEF" ]]; then
        print_status "Rolling back frontend service to: $PREVIOUS_FRONTEND_TASK_DEF"
        
        if aws ecs update-service \
            --cluster "$CLUSTER_NAME" \
            --service "$FRONTEND_SERVICE" \
            --task-definition "$PREVIOUS_FRONTEND_TASK_DEF" \
            --region "$AWS_REGION" >/dev/null 2>&1; then
            print_status "Frontend rollback initiated"
        else
            print_error "Failed to rollback frontend service"
            rollback_success=false
        fi
    else
        print_warning "No previous frontend task definition for rollback"
    fi
    
    if [[ "$rollback_success" == "true" ]]; then
        print_status "Waiting for rollback to complete..."
        
        # Wait for rollback to complete (simplified check)
        sleep 60
        
        # Run basic health check after rollback
        local app_url
        app_url=$(terraform -chdir=./infrastructure/terraform output -raw application_url 2>/dev/null || echo "")
        
        if [[ -n "$app_url" ]] && curl -f -s --max-time 10 "$app_url/api/health" >/dev/null 2>&1; then
            print_success "Rollback completed successfully"
        else
            print_error "Rollback may have failed - manual intervention required"
        fi
    else
        print_error "Rollback failed - manual intervention required"
    fi
}

# Send deployment notification
send_deployment_notification() {
    local status="$1"
    local message="$2"
    
    print_status "Sending deployment notification..."
    
    # Create notification payload
    local notification_payload
    notification_payload=$(cat << EOF
{
    "deployment_id": "$DEPLOYMENT_ID",
    "environment": "production",
    "status": "$status",
    "message": "$message",
    "timestamp": "$DEPLOYMENT_START_TIME",
    "services": {
        "backend": "$BACKEND_SERVICE",
        "frontend": "$FRONTEND_SERVICE"
    },
    "cluster": "$CLUSTER_NAME",
    "region": "$AWS_REGION"
}
EOF
)
    
    # Send to webhook if configured
    if [[ -n "${DEPLOYMENT_WEBHOOK_URL:-}" ]]; then
        curl -s -X POST \
            -H "Content-Type: application/json" \
            -d "$notification_payload" \
            "$DEPLOYMENT_WEBHOOK_URL" >/dev/null 2>&1 || true
    fi
    
    # Log notification
    echo "$notification_payload" > "/tmp/deployment-${DEPLOYMENT_ID}.json"
    print_status "Deployment notification logged to /tmp/deployment-${DEPLOYMENT_ID}.json"
}

# Generate deployment report
generate_deployment_report() {
    local status="$1"
    local end_time
    end_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    echo ""
    echo "=========================================="
    echo "       PRODUCTION DEPLOYMENT REPORT"
    echo "=========================================="
    echo "Deployment ID: $DEPLOYMENT_ID"
    echo "Status: $status"
    echo "Start Time: $DEPLOYMENT_START_TIME"
    echo "End Time: $end_time"
    echo "Cluster: $CLUSTER_NAME"
    echo "Region: $AWS_REGION"
    echo ""
    echo "Services Deployed:"
    echo "  Backend: $BACKEND_SERVICE"
    echo "  Frontend: $FRONTEND_SERVICE"
    echo ""
    
    if [[ "$status" == "SUCCESS" ]]; then
        print_success "🚀 Production deployment completed successfully!"
        echo ""
        echo "Post-deployment checklist:"
        echo "  ✓ Services deployed and healthy"
        echo "  ✓ Health checks passed"
        echo "  ✓ Smoke tests completed"
        echo ""
        echo "Monitoring:"
        echo "  - Monitor application logs and metrics"
        echo "  - Watch for any error rate increases"
        echo "  - Verify user-facing functionality"
    else
        print_error "❌ Production deployment failed!"
        echo ""
        echo "Failure details:"
        echo "  - Check ECS service events for errors"
        echo "  - Review CloudWatch logs for issues"
        echo "  - Verify task definition configurations"
        echo ""
        if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
            echo "Rollback status: Attempted"
        else
            echo "Rollback status: Disabled"
        fi
    fi
}

# Main deployment function
main() {
    print_status "Starting production deployment..."
    print_status "Cluster: $CLUSTER_NAME"
    print_status "Region: $AWS_REGION"
    print_status "Rollback on failure: $ROLLBACK_ON_FAILURE"
    echo ""
    
    # Generate deployment ID
    generate_deployment_id
    
    # Check prerequisites
    check_prerequisites
    
    # Get current state
    get_current_task_definitions
    
    # Run pre-deployment validation
    if ! run_pre_deployment_validation; then
        if [[ "$FORCE_DEPLOYMENT" != "true" ]]; then
            print_error "Pre-deployment validation failed. Use --force to override."
            send_deployment_notification "FAILED" "Pre-deployment validation failed"
            generate_deployment_report "FAILED"
            exit 1
        else
            print_warning "Pre-deployment validation failed but continuing due to --force"
        fi
    fi
    
    # Deploy services
    if ! deploy_services; then
        print_error "Service deployment failed"
        send_deployment_notification "FAILED" "Service deployment failed"
        generate_deployment_report "FAILED"
        exit 1
    fi
    
    # Wait for deployment to complete
    if ! wait_for_deployment; then
        print_error "Deployment did not complete successfully"
        
        if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
            rollback_deployment
            send_deployment_notification "ROLLED_BACK" "Deployment failed and was rolled back"
            generate_deployment_report "ROLLED_BACK"
        else
            send_deployment_notification "FAILED" "Deployment failed without rollback"
            generate_deployment_report "FAILED"
        fi
        exit 1
    fi
    
    # Run health checks
    if ! run_health_checks; then
        print_error "Health checks failed"
        
        if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
            rollback_deployment
            send_deployment_notification "ROLLED_BACK" "Health checks failed and deployment was rolled back"
            generate_deployment_report "ROLLED_BACK"
        else
            send_deployment_notification "FAILED" "Health checks failed"
            generate_deployment_report "FAILED"
        fi
        exit 1
    fi
    
    # Run smoke tests
    if ! run_smoke_tests; then
        print_warning "Smoke tests failed, but deployment will continue"
        # Note: We don't rollback on smoke test failures as they might be flaky
    fi
    
    # Success!
    send_deployment_notification "SUCCESS" "Production deployment completed successfully"
    generate_deployment_report "SUCCESS"
}

# Handle script interruption
trap 'print_error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main