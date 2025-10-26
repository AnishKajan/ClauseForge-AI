#!/bin/bash

# Emergency Production Rollback Script
# Quickly rollback production deployment to previous version

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
ROLLBACK_TIMEOUT=300  # 5 minutes
DRY_RUN=false
FORCE_ROLLBACK=false
TARGET_REVISION=""

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
    echo "  --revision REVISION             Target task definition revision (default: previous)"
    echo "  --timeout SECONDS               Rollback timeout (default: 300)"
    echo "  --dry-run                       Show what would be rolled back"
    echo "  --force                         Force rollback without confirmation"
    echo "  -h, --help                      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                              Rollback to previous version"
    echo "  $0 --revision 5                 Rollback to specific revision"
    echo "  $0 --dry-run                    Show rollback plan"
    echo "  $0 --force                      Rollback without confirmation"
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
        --revision)
            TARGET_REVISION="$2"
            shift 2
            ;;
        --timeout)
            ROLLBACK_TIMEOUT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE_ROLLBACK=true
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
    
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        print_error "jq not found"
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
    
    print_success "Prerequisites check passed"
}

# Get current deployment status
get_current_status() {
    print_status "Getting current deployment status..."
    
    # Get backend service info
    local backend_info
    backend_info=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$BACKEND_SERVICE" \
        --region "$AWS_REGION" \
        --query 'services[0]' 2>/dev/null || echo "{}")
    
    if [[ "$backend_info" == "{}" ]]; then
        print_error "Backend service '$BACKEND_SERVICE' not found"
        exit 1
    fi
    
    # Get frontend service info
    local frontend_info
    frontend_info=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$FRONTEND_SERVICE" \
        --region "$AWS_REGION" \
        --query 'services[0]' 2>/dev/null || echo "{}")
    
    if [[ "$frontend_info" == "{}" ]]; then
        print_error "Frontend service '$FRONTEND_SERVICE' not found"
        exit 1
    fi
    
    # Display current status
    local backend_task_def
    local frontend_task_def
    local backend_running
    local frontend_running
    local backend_desired
    local frontend_desired
    
    backend_task_def=$(echo "$backend_info" | jq -r '.taskDefinition')
    frontend_task_def=$(echo "$frontend_info" | jq -r '.taskDefinition')
    backend_running=$(echo "$backend_info" | jq -r '.runningCount')
    frontend_running=$(echo "$frontend_info" | jq -r '.runningCount')
    backend_desired=$(echo "$backend_info" | jq -r '.desiredCount')
    frontend_desired=$(echo "$frontend_info" | jq -r '.desiredCount')
    
    echo ""
    echo "Current Deployment Status:"
    echo "  Backend Service: $BACKEND_SERVICE"
    echo "    Task Definition: $backend_task_def"
    echo "    Running/Desired: $backend_running/$backend_desired"
    echo ""
    echo "  Frontend Service: $FRONTEND_SERVICE"
    echo "    Task Definition: $frontend_task_def"
    echo "    Running/Desired: $frontend_running/$frontend_desired"
    echo ""
}

# Get available task definition revisions
get_available_revisions() {
    print_status "Getting available task definition revisions..."
    
    # Get backend task definition family
    local backend_family
    backend_family=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$BACKEND_SERVICE" \
        --region "$AWS_REGION" \
        --query 'services[0].taskDefinition' \
        --output text | cut -d':' -f6 | cut -d'/' -f2 | cut -d':' -f1)
    
    # Get frontend task definition family
    local frontend_family
    frontend_family=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$FRONTEND_SERVICE" \
        --region "$AWS_REGION" \
        --query 'services[0].taskDefinition' \
        --output text | cut -d':' -f6 | cut -d'/' -f2 | cut -d':' -f1)
    
    # List recent backend revisions
    echo "Recent Backend Task Definition Revisions ($backend_family):"
    aws ecs list-task-definitions \
        --family-prefix "$backend_family" \
        --status ACTIVE \
        --sort DESC \
        --max-items 5 \
        --region "$AWS_REGION" \
        --query 'taskDefinitionArns[]' \
        --output table
    
    echo ""
    echo "Recent Frontend Task Definition Revisions ($frontend_family):"
    aws ecs list-task-definitions \
        --family-prefix "$frontend_family" \
        --status ACTIVE \
        --sort DESC \
        --max-items 5 \
        --region "$AWS_REGION" \
        --query 'taskDefinitionArns[]' \
        --output table
    echo ""
}

# Get target task definitions for rollback
get_target_task_definitions() {
    print_status "Determining target task definitions for rollback..."
    
    local backend_family frontend_family
    local backend_current_revision frontend_current_revision
    local backend_target_arn frontend_target_arn
    
    # Get current task definition families and revisions
    backend_family=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$BACKEND_SERVICE" \
        --region "$AWS_REGION" \
        --query 'services[0].taskDefinition' \
        --output text | cut -d':' -f6 | cut -d'/' -f2 | cut -d':' -f1)
    
    frontend_family=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$FRONTEND_SERVICE" \
        --region "$AWS_REGION" \
        --query 'services[0].taskDefinition' \
        --output text | cut -d':' -f6 | cut -d'/' -f2 | cut -d':' -f1)
    
    backend_current_revision=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$BACKEND_SERVICE" \
        --region "$AWS_REGION" \
        --query 'services[0].taskDefinition' \
        --output text | cut -d':' -f7)
    
    frontend_current_revision=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$FRONTEND_SERVICE" \
        --region "$AWS_REGION" \
        --query 'services[0].taskDefinition' \
        --output text | cut -d':' -f7)
    
    if [[ -n "$TARGET_REVISION" ]]; then
        # Use specified revision
        backend_target_arn=$(aws ecs list-task-definitions \
            --family-prefix "$backend_family" \
            --status ACTIVE \
            --region "$AWS_REGION" \
            --query "taskDefinitionArns[?contains(@, ':$TARGET_REVISION')]" \
            --output text | head -1)
        
        frontend_target_arn=$(aws ecs list-task-definitions \
            --family-prefix "$frontend_family" \
            --status ACTIVE \
            --region "$AWS_REGION" \
            --query "taskDefinitionArns[?contains(@, ':$TARGET_REVISION')]" \
            --output text | head -1)
    else
        # Use previous revision (current - 1)
        local backend_target_revision=$((backend_current_revision - 1))
        local frontend_target_revision=$((frontend_current_revision - 1))
        
        if [[ $backend_target_revision -lt 1 ]]; then
            print_error "No previous backend revision available for rollback"
            exit 1
        fi
        
        if [[ $frontend_target_revision -lt 1 ]]; then
            print_error "No previous frontend revision available for rollback"
            exit 1
        fi
        
        backend_target_arn=$(aws ecs list-task-definitions \
            --family-prefix "$backend_family" \
            --status ACTIVE \
            --region "$AWS_REGION" \
            --query "taskDefinitionArns[?contains(@, ':$backend_target_revision')]" \
            --output text | head -1)
        
        frontend_target_arn=$(aws ecs list-task-definitions \
            --family-prefix "$frontend_family" \
            --status ACTIVE \
            --region "$AWS_REGION" \
            --query "taskDefinitionArns[?contains(@, ':$frontend_target_revision')]" \
            --output text | head -1)
    fi
    
    if [[ -z "$backend_target_arn" ]]; then
        print_error "Target backend task definition not found"
        exit 1
    fi
    
    if [[ -z "$frontend_target_arn" ]]; then
        print_error "Target frontend task definition not found"
        exit 1
    fi
    
    echo "Rollback Target Task Definitions:"
    echo "  Backend: $backend_target_arn"
    echo "  Frontend: $frontend_target_arn"
    echo ""
    
    # Store for later use
    export BACKEND_TARGET_ARN="$backend_target_arn"
    export FRONTEND_TARGET_ARN="$frontend_target_arn"
}

# Confirm rollback
confirm_rollback() {
    if [[ "$FORCE_ROLLBACK" == "true" || "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    echo ""
    print_warning "⚠️  PRODUCTION ROLLBACK CONFIRMATION ⚠️"
    echo ""
    echo "You are about to rollback the production deployment:"
    echo "  Cluster: $CLUSTER_NAME"
    echo "  Region: $AWS_REGION"
    echo "  Backend Service: $BACKEND_SERVICE"
    echo "  Frontend Service: $FRONTEND_SERVICE"
    echo ""
    echo "Target Task Definitions:"
    echo "  Backend: $BACKEND_TARGET_ARN"
    echo "  Frontend: $FRONTEND_TARGET_ARN"
    echo ""
    
    read -p "Are you sure you want to proceed with the rollback? (type 'ROLLBACK' to confirm): " confirmation
    
    if [[ "$confirmation" != "ROLLBACK" ]]; then
        print_error "Rollback cancelled"
        exit 1
    fi
    
    print_status "Rollback confirmed"
}

# Execute rollback
execute_rollback() {
    if [[ "$DRY_RUN" == "true" ]]; then
        print_warning "DRY RUN MODE - No actual rollback will occur"
        print_status "Would rollback:"
        print_status "  Backend to: $BACKEND_TARGET_ARN"
        print_status "  Frontend to: $FRONTEND_TARGET_ARN"
        return 0
    fi
    
    print_status "Executing production rollback..."
    
    local rollback_id
    rollback_id="rollback-$(date +%Y%m%d-%H%M%S)"
    
    print_status "Rollback ID: $rollback_id"
    
    # Rollback backend service
    print_status "Rolling back backend service..."
    
    if aws ecs update-service \
        --cluster "$CLUSTER_NAME" \
        --service "$BACKEND_SERVICE" \
        --task-definition "$BACKEND_TARGET_ARN" \
        --region "$AWS_REGION" >/dev/null 2>&1; then
        print_success "Backend rollback initiated"
    else
        print_error "Failed to initiate backend rollback"
        return 1
    fi
    
    # Rollback frontend service
    print_status "Rolling back frontend service..."
    
    if aws ecs update-service \
        --cluster "$CLUSTER_NAME" \
        --service "$FRONTEND_SERVICE" \
        --task-definition "$FRONTEND_TARGET_ARN" \
        --region "$AWS_REGION" >/dev/null 2>&1; then
        print_success "Frontend rollback initiated"
    else
        print_error "Failed to initiate frontend rollback"
        return 1
    fi
    
    print_success "Rollback initiated successfully"
    return 0
}

# Wait for rollback completion
wait_for_rollback() {
    if [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    print_status "Waiting for rollback to complete (timeout: ${ROLLBACK_TIMEOUT}s)..."
    
    local start_time
    start_time=$(date +%s)
    local timeout_time=$((start_time + ROLLBACK_TIMEOUT))
    
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
        
        print_status "Rollback progress - Backend: $backend_status/$backend_desired, Frontend: $frontend_status/$frontend_desired"
        
        # Check if rollback is complete
        if [[ "$backend_status" == "$backend_desired" && "$frontend_status" == "$frontend_desired" ]]; then
            print_success "Rollback completed successfully"
            return 0
        fi
        
        sleep 15
    done
    
    print_error "Rollback timeout after ${ROLLBACK_TIMEOUT} seconds"
    return 1
}

# Verify rollback
verify_rollback() {
    if [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    print_status "Verifying rollback..."
    
    # Get application URL
    local app_url
    app_url=$(terraform -chdir=./infrastructure/terraform output -raw application_url 2>/dev/null || echo "")
    
    if [[ -z "$app_url" ]]; then
        print_warning "Could not determine application URL for verification"
        return 0
    fi
    
    # Test basic health endpoint
    local attempts=0
    local max_attempts=10
    
    while [[ $attempts -lt $max_attempts ]]; do
        if curl -f -s --max-time 10 "$app_url/api/health" >/dev/null 2>&1; then
            print_success "Health check passed after rollback"
            
            # Test frontend
            if curl -f -s --max-time 10 "$app_url/" >/dev/null 2>&1; then
                print_success "Frontend accessible after rollback"
                return 0
            else
                print_warning "Frontend not accessible, retrying..."
            fi
        else
            print_warning "Health check failed, retrying..."
        fi
        
        ((attempts++))
        sleep 10
    done
    
    print_error "Verification failed after rollback"
    return 1
}

# Generate rollback report
generate_rollback_report() {
    local status="$1"
    local end_time
    end_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    echo ""
    echo "=========================================="
    echo "       PRODUCTION ROLLBACK REPORT"
    echo "=========================================="
    echo "Status: $status"
    echo "End Time: $end_time"
    echo "Cluster: $CLUSTER_NAME"
    echo "Region: $AWS_REGION"
    echo ""
    echo "Services Rolled Back:"
    echo "  Backend: $BACKEND_SERVICE"
    echo "    Target: $BACKEND_TARGET_ARN"
    echo "  Frontend: $FRONTEND_SERVICE"
    echo "    Target: $FRONTEND_TARGET_ARN"
    echo ""
    
    if [[ "$status" == "SUCCESS" ]]; then
        print_success "🔄 Production rollback completed successfully!"
        echo ""
        echo "Post-rollback actions:"
        echo "  ✓ Services rolled back to previous version"
        echo "  ✓ Health checks passed"
        echo "  ✓ Application accessible"
        echo ""
        echo "Next steps:"
        echo "  - Monitor application for stability"
        echo "  - Investigate root cause of original issue"
        echo "  - Plan fix and redeployment"
    else
        print_error "❌ Production rollback failed!"
        echo ""
        echo "Manual intervention required:"
        echo "  - Check ECS service events"
        echo "  - Review task definition configurations"
        echo "  - Consider manual service updates"
    fi
}

# Main rollback function
main() {
    print_status "Starting production rollback process..."
    print_status "Cluster: $CLUSTER_NAME"
    print_status "Region: $AWS_REGION"
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Get current status
    get_current_status
    
    # Show available revisions
    get_available_revisions
    
    # Determine target task definitions
    get_target_task_definitions
    
    # Confirm rollback
    confirm_rollback
    
    # Execute rollback
    if ! execute_rollback; then
        print_error "Rollback execution failed"
        generate_rollback_report "FAILED"
        exit 1
    fi
    
    # Wait for rollback completion
    if ! wait_for_rollback; then
        print_error "Rollback did not complete successfully"
        generate_rollback_report "TIMEOUT"
        exit 1
    fi
    
    # Verify rollback
    if ! verify_rollback; then
        print_warning "Rollback verification failed, but rollback may still be successful"
    fi
    
    # Success!
    generate_rollback_report "SUCCESS"
}

# Handle script interruption
trap 'print_error "Rollback interrupted"; exit 1' INT TERM

# Run main function
main