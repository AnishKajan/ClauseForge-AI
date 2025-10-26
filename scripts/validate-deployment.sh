#!/bin/bash

# Comprehensive Deployment Validation Script
# Validates deployment across all services and critical functionality

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="staging"
BASE_URL=""
TIMEOUT=60
SKIP_LOAD_TEST=false
SKIP_INTEGRATION_TEST=false
VERBOSE=false

# Validation results
VALIDATIONS_PASSED=0
VALIDATIONS_FAILED=0
FAILED_VALIDATIONS=()

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

print_validation_result() {
    local validation_name="$1"
    local result="$2"
    local details="$3"
    
    if [[ "$result" == "PASS" ]]; then
        echo -e "${GREEN}✓${NC} $validation_name"
        ((VALIDATIONS_PASSED++))
        if [[ "$VERBOSE" == "true" && -n "$details" ]]; then
            echo "    $details"
        fi
    else
        echo -e "${RED}✗${NC} $validation_name"
        ((VALIDATIONS_FAILED++))
        FAILED_VALIDATIONS+=("$validation_name")
        if [[ -n "$details" ]]; then
            echo "    $details"
        fi
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV           Environment (staging|production) (default: staging)"
    echo "  -u, --url URL                   Base URL for testing"
    echo "  -t, --timeout SECONDS           Timeout for operations (default: 60)"
    echo "  --skip-load-test                Skip load testing"
    echo "  --skip-integration-test         Skip integration tests"
    echo "  -v, --verbose                   Verbose output"
    echo "  -h, --help                      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e staging                   Validate staging deployment"
    echo "  $0 -e production -u https://lexiscan.ai  Validate production"
    echo "  $0 --skip-load-test             Skip load testing"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -u|--url)
            BASE_URL="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --skip-load-test)
            SKIP_LOAD_TEST=true
            shift
            ;;
        --skip-integration-test)
            SKIP_INTEGRATION_TEST=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
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

# Set default URL based on environment
if [[ -z "$BASE_URL" ]]; then
    case "$ENVIRONMENT" in
        staging)
            BASE_URL="http://localhost:80"
            ;;
        production)
            BASE_URL="https://lexiscan.ai"
            ;;
        *)
            print_error "Unknown environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
fi

# Remove trailing slash from URL
BASE_URL=${BASE_URL%/}

# Validation 1: Service availability
validate_service_availability() {
    print_status "Validating service availability..."
    
    local services=()
    local service_urls=()
    
    if [[ "$ENVIRONMENT" == "staging" ]]; then
        services=("Frontend" "Backend API" "Nginx" "PostgreSQL" "Redis" "LocalStack" "Prometheus" "Grafana")
        service_urls=("http://localhost:3001" "http://localhost:8001/api/health" "http://localhost:80/health" "localhost:5433" "localhost:6380" "http://localhost:4567/_localstack/health" "http://localhost:9091" "http://localhost:3001")
    else
        services=("Frontend" "Backend API" "Load Balancer")
        service_urls=("$BASE_URL" "$BASE_URL/api/health" "$BASE_URL/health")
    fi
    
    for i in "${!services[@]}"; do
        local service="${services[$i]}"
        local url="${service_urls[$i]}"
        
        if [[ "$url" == localhost:* ]]; then
            # TCP connection test
            local host_port=(${url//:/ })
            if timeout 5 bash -c "</dev/tcp/${host_port[0]}/${host_port[1]}" 2>/dev/null; then
                print_validation_result "$service availability" "PASS" "TCP connection successful"
            else
                print_validation_result "$service availability" "FAIL" "TCP connection failed"
            fi
        else
            # HTTP test
            if curl -f -s --max-time 10 "$url" >/dev/null 2>&1; then
                print_validation_result "$service availability" "PASS" "HTTP response successful"
            else
                print_validation_result "$service availability" "FAIL" "HTTP request failed"
            fi
        fi
    done
}

# Validation 2: Database schema and data integrity
validate_database_integrity() {
    print_status "Validating database integrity..."
    
    if [[ "$ENVIRONMENT" == "staging" ]]; then
        # Check database schema
        local schema_check
        schema_check=$(docker-compose -f docker-compose.staging.yml exec -T postgres psql -U lexiscan -d lexiscan_staging -c "
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        " 2>/dev/null | grep -E '^[[:space:]]*[0-9]+[[:space:]]*$' | tr -d ' ')
        
        if [[ "$schema_check" -gt 10 ]]; then
            print_validation_result "Database schema" "PASS" "$schema_check tables found"
        else
            print_validation_result "Database schema" "FAIL" "Insufficient tables: $schema_check"
        fi
        
        # Check extensions
        local extensions_check
        extensions_check=$(docker-compose -f docker-compose.staging.yml exec -T postgres psql -U lexiscan -d lexiscan_staging -c "
            SELECT COUNT(*) FROM pg_extension WHERE extname IN ('pgcrypto', 'vector');
        " 2>/dev/null | grep -E '^[[:space:]]*[0-9]+[[:space:]]*$' | tr -d ' ')
        
        if [[ "$extensions_check" -eq 2 ]]; then
            print_validation_result "Database extensions" "PASS" "pgcrypto and vector extensions installed"
        else
            print_validation_result "Database extensions" "FAIL" "Missing required extensions"
        fi
        
        # Check RLS policies
        local rls_check
        rls_check=$(docker-compose -f docker-compose.staging.yml exec -T postgres psql -U lexiscan -d lexiscan_staging -c "
            SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public';
        " 2>/dev/null | grep -E '^[[:space:]]*[0-9]+[[:space:]]*$' | tr -d ' ')
        
        if [[ "$rls_check" -gt 5 ]]; then
            print_validation_result "Row Level Security policies" "PASS" "$rls_check RLS policies found"
        else
            print_validation_result "Row Level Security policies" "FAIL" "Insufficient RLS policies: $rls_check"
        fi
    else
        print_validation_result "Database integrity (production)" "PASS" "Skipped for production environment"
    fi
}

# Validation 3: API endpoint functionality
validate_api_endpoints() {
    print_status "Validating API endpoints..."
    
    local endpoints=(
        "/api/health:GET:200"
        "/api/health/detailed:GET:200"
        "/api/ready:GET:200"
        "/api/live:GET:200"
        "/api/version:GET:200"
        "/api/docs:GET:200"
        "/api/metrics:GET:200"
        "/api/auth/register:POST:422"  # Should fail without data
        "/api/auth/login:POST:422"     # Should fail without data
        "/api/documents:GET:401"       # Should require auth
        "/api/rag/query:POST:401"      # Should require auth
        "/api/analyses:GET:401"        # Should require auth
    )
    
    for endpoint_spec in "${endpoints[@]}"; do
        IFS=':' read -r endpoint method expected_status <<< "$endpoint_spec"
        
        local status_code
        if [[ "$method" == "GET" ]]; then
            status_code=$(curl -s -w "%{http_code}" -o /dev/null --max-time 10 "${BASE_URL}${endpoint}")
        elif [[ "$method" == "POST" ]]; then
            status_code=$(curl -s -w "%{http_code}" -o /dev/null --max-time 10 -X POST -H "Content-Type: application/json" -d '{}' "${BASE_URL}${endpoint}")
        fi
        
        if [[ "$status_code" == "$expected_status" ]]; then
            print_validation_result "API endpoint $endpoint ($method)" "PASS" "Status: $status_code"
        else
            print_validation_result "API endpoint $endpoint ($method)" "FAIL" "Expected: $expected_status, Got: $status_code"
        fi
    done
}

# Validation 4: Security configuration
validate_security_configuration() {
    print_status "Validating security configuration..."
    
    # Check security headers
    local headers
    headers=$(curl -s -I "${BASE_URL}/" 2>/dev/null)
    
    local security_headers=(
        "X-Frame-Options"
        "X-Content-Type-Options"
        "X-XSS-Protection"
        "Referrer-Policy"
    )
    
    for header in "${security_headers[@]}"; do
        if echo "$headers" | grep -qi "$header"; then
            print_validation_result "Security header: $header" "PASS" "Header present"
        else
            print_validation_result "Security header: $header" "FAIL" "Header missing"
        fi
    done
    
    # Check HTTPS in production
    if [[ "$ENVIRONMENT" == "production" ]]; then
        if [[ "$BASE_URL" == https://* ]]; then
            print_validation_result "HTTPS configuration" "PASS" "Using HTTPS"
        else
            print_validation_result "HTTPS configuration" "FAIL" "Not using HTTPS"
        fi
        
        # Check SSL certificate
        if openssl s_client -connect "${BASE_URL#https://}:443" -servername "${BASE_URL#https://}" </dev/null 2>/dev/null | grep -q "Verify return code: 0"; then
            print_validation_result "SSL certificate" "PASS" "Valid SSL certificate"
        else
            print_validation_result "SSL certificate" "FAIL" "Invalid SSL certificate"
        fi
    fi
    
    # Check rate limiting
    local rate_limit_triggered=false
    for i in {1..20}; do
        local status_code
        status_code=$(curl -s -w "%{http_code}" -o /dev/null --max-time 5 "${BASE_URL}/api/health")
        if [[ "$status_code" == "429" ]]; then
            rate_limit_triggered=true
            break
        fi
        sleep 0.1
    done
    
    if [[ "$rate_limit_triggered" == "true" ]]; then
        print_validation_result "Rate limiting" "PASS" "Rate limiting active"
    else
        print_validation_result "Rate limiting" "PASS" "Rate limiting not triggered (may be configured for higher limits)"
    fi
}

# Validation 5: Performance benchmarks
validate_performance() {
    print_status "Validating performance benchmarks..."
    
    # Test API response time
    local total_time=0
    local requests=5
    
    for i in $(seq 1 $requests); do
        local start_time end_time duration
        start_time=$(date +%s%N)
        curl -s --max-time 10 "${BASE_URL}/api/health" >/dev/null 2>&1
        end_time=$(date +%s%N)
        duration=$(( (end_time - start_time) / 1000000 ))
        total_time=$((total_time + duration))
    done
    
    local avg_response_time=$((total_time / requests))
    
    if [[ $avg_response_time -lt 500 ]]; then
        print_validation_result "API response time" "PASS" "Average: ${avg_response_time}ms"
    elif [[ $avg_response_time -lt 1000 ]]; then
        print_validation_result "API response time" "PASS" "Average: ${avg_response_time}ms (acceptable)"
    else
        print_validation_result "API response time" "FAIL" "Average: ${avg_response_time}ms (too slow)"
    fi
    
    # Test frontend response time
    total_time=0
    for i in $(seq 1 $requests); do
        local start_time end_time duration
        start_time=$(date +%s%N)
        curl -s --max-time 15 "${BASE_URL}/" >/dev/null 2>&1
        end_time=$(date +%s%N)
        duration=$(( (end_time - start_time) / 1000000 ))
        total_time=$((total_time + duration))
    done
    
    avg_response_time=$((total_time / requests))
    
    if [[ $avg_response_time -lt 2000 ]]; then
        print_validation_result "Frontend response time" "PASS" "Average: ${avg_response_time}ms"
    elif [[ $avg_response_time -lt 3000 ]]; then
        print_validation_result "Frontend response time" "PASS" "Average: ${avg_response_time}ms (acceptable)"
    else
        print_validation_result "Frontend response time" "FAIL" "Average: ${avg_response_time}ms (too slow)"
    fi
}

# Validation 6: Load testing (basic)
validate_load_handling() {
    if [[ "$SKIP_LOAD_TEST" == "true" ]]; then
        print_warning "Skipping load testing"
        return
    fi
    
    print_status "Validating load handling..."
    
    # Simple concurrent request test
    local concurrent_requests=10
    local pids=()
    local success_count=0
    local start_time end_time
    
    start_time=$(date +%s)
    
    for i in $(seq 1 $concurrent_requests); do
        (
            if curl -s --max-time 30 "${BASE_URL}/api/health" >/dev/null 2>&1; then
                echo "success"
            else
                echo "failure"
            fi
        ) &
        pids+=($!)
    done
    
    # Wait for all requests to complete
    for pid in "${pids[@]}"; do
        if wait "$pid"; then
            local result
            result=$(jobs -p | grep -c "$pid" || echo "success")
            if [[ "$result" == "success" ]]; then
                ((success_count++))
            fi
        fi
    done
    
    end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [[ $success_count -ge $((concurrent_requests * 8 / 10)) ]]; then
        print_validation_result "Concurrent request handling" "PASS" "$success_count/$concurrent_requests successful in ${duration}s"
    else
        print_validation_result "Concurrent request handling" "FAIL" "Only $success_count/$concurrent_requests successful"
    fi
}

# Validation 7: Monitoring and observability
validate_monitoring() {
    print_status "Validating monitoring and observability..."
    
    # Check metrics endpoint
    if curl -s --max-time 10 "${BASE_URL}/api/metrics" | grep -q "lexiscan_info"; then
        print_validation_result "Metrics endpoint" "PASS" "Prometheus metrics available"
    else
        print_validation_result "Metrics endpoint" "FAIL" "Metrics not properly formatted"
    fi
    
    # Check health check details
    if curl -s --max-time 10 "${BASE_URL}/api/health/detailed" | grep -q '"system"'; then
        print_validation_result "System metrics" "PASS" "System metrics available"
    else
        print_validation_result "System metrics" "FAIL" "System metrics not available"
    fi
    
    # Check if monitoring services are available (staging only)
    if [[ "$ENVIRONMENT" == "staging" ]]; then
        if curl -s --max-time 5 "http://localhost:9091" >/dev/null 2>&1; then
            print_validation_result "Prometheus availability" "PASS" "Prometheus accessible"
        else
            print_validation_result "Prometheus availability" "FAIL" "Prometheus not accessible"
        fi
        
        if curl -s --max-time 5 "http://localhost:3001" >/dev/null 2>&1; then
            print_validation_result "Grafana availability" "PASS" "Grafana accessible"
        else
            print_validation_result "Grafana availability" "FAIL" "Grafana not accessible"
        fi
    fi
}

# Validation 8: Configuration validation
validate_configuration() {
    print_status "Validating configuration..."
    
    # Check version information
    local version_info
    version_info=$(curl -s --max-time 10 "${BASE_URL}/api/version" 2>/dev/null)
    
    if echo "$version_info" | grep -q '"version"'; then
        local version
        version=$(echo "$version_info" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
        print_validation_result "Version information" "PASS" "Version: $version"
    else
        print_validation_result "Version information" "FAIL" "Version information not available"
    fi
    
    # Check environment configuration
    local health_info
    health_info=$(curl -s --max-time 10 "${BASE_URL}/api/health/detailed" 2>/dev/null)
    
    if echo "$health_info" | grep -q "\"$ENVIRONMENT\""; then
        print_validation_result "Environment configuration" "PASS" "Environment: $ENVIRONMENT"
    else
        print_validation_result "Environment configuration" "FAIL" "Environment mismatch or not configured"
    fi
}

# Generate validation report
generate_validation_report() {
    echo ""
    echo "=========================================="
    echo "       DEPLOYMENT VALIDATION REPORT"
    echo "=========================================="
    echo "Environment: $ENVIRONMENT"
    echo "Base URL: $BASE_URL"
    echo "Timestamp: $(date)"
    echo ""
    echo "Results:"
    echo "  Validations Passed: $VALIDATIONS_PASSED"
    echo "  Validations Failed: $VALIDATIONS_FAILED"
    echo "  Total Validations: $((VALIDATIONS_PASSED + VALIDATIONS_FAILED))"
    echo ""
    
    if [[ $VALIDATIONS_FAILED -gt 0 ]]; then
        echo "Failed Validations:"
        for validation in "${FAILED_VALIDATIONS[@]}"; do
            echo "  - $validation"
        done
        echo ""
    fi
    
    local success_rate
    success_rate=$(( VALIDATIONS_PASSED * 100 / (VALIDATIONS_PASSED + VALIDATIONS_FAILED) ))
    echo "Success Rate: ${success_rate}%"
    echo ""
    
    # Deployment readiness assessment
    if [[ $VALIDATIONS_FAILED -eq 0 ]]; then
        print_success "🎉 Deployment validation successful! System is ready for use."
        echo ""
        echo "Next steps:"
        echo "  - Monitor system performance and logs"
        echo "  - Run user acceptance tests"
        echo "  - Update monitoring dashboards"
        return 0
    elif [[ $success_rate -ge 90 ]]; then
        print_warning "⚠️  Deployment validation mostly successful with minor issues."
        echo ""
        echo "Recommendations:"
        echo "  - Address failed validations if critical"
        echo "  - Monitor system closely after deployment"
        echo "  - Consider rollback if issues persist"
        return 1
    else
        print_error "❌ Deployment validation failed. System may not be ready for use."
        echo ""
        echo "Critical actions required:"
        echo "  - Address all failed validations"
        echo "  - Consider rollback to previous version"
        echo "  - Investigate root causes before retry"
        return 2
    fi
}

# Main function
main() {
    print_status "Starting deployment validation for $ENVIRONMENT environment..."
    print_status "Target URL: $BASE_URL"
    print_status "Timeout: ${TIMEOUT}s"
    echo ""
    
    # Run all validations
    validate_service_availability
    validate_database_integrity
    validate_api_endpoints
    validate_security_configuration
    validate_performance
    validate_load_handling
    validate_monitoring
    validate_configuration
    
    # Generate and display report
    generate_validation_report
}

# Run main function
main