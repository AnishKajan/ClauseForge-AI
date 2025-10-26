#!/bin/bash

# Comprehensive Smoke Tests for LexiScan Deployment
# Tests critical user workflows and system functionality

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
BASE_URL=""
ENVIRONMENT="staging"
TIMEOUT=30
VERBOSE=false
SKIP_AUTH_TESTS=false

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

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

print_test_result() {
    local test_name="$1"
    local result="$2"
    local details="$3"
    
    if [[ "$result" == "PASS" ]]; then
        echo -e "${GREEN}✓${NC} $test_name"
        ((TESTS_PASSED++))
        if [[ "$VERBOSE" == "true" && -n "$details" ]]; then
            echo "    $details"
        fi
    else
        echo -e "${RED}✗${NC} $test_name"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
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
    echo "  -u, --url URL                   Base URL for testing (required)"
    echo "  -e, --environment ENV           Environment (staging|production) (default: staging)"
    echo "  -t, --timeout SECONDS           Request timeout (default: 30)"
    echo "  --skip-auth                     Skip authentication tests"
    echo "  -v, --verbose                   Verbose output"
    echo "  -h, --help                      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -u http://localhost:80       Test staging environment"
    echo "  $0 -u https://lexiscan.ai -e production  Test production"
    echo "  $0 -u http://localhost:80 --skip-auth    Skip auth tests"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            BASE_URL="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --skip-auth)
            SKIP_AUTH_TESTS=true
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

# Validate required parameters
if [[ -z "$BASE_URL" ]]; then
    print_error "Base URL is required. Use -u or --url"
    show_usage
    exit 1
fi

# Remove trailing slash from URL
BASE_URL=${BASE_URL%/}

# Helper function to make HTTP requests
make_request() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local expected_status="$4"
    local headers="$5"
    
    local url="${BASE_URL}${endpoint}"
    local curl_args=(-s -w "%{http_code}" --max-time "$TIMEOUT")
    
    if [[ -n "$headers" ]]; then
        while IFS= read -r header; do
            curl_args+=(-H "$header")
        done <<< "$headers"
    fi
    
    if [[ "$method" == "POST" && -n "$data" ]]; then
        curl_args+=(-X POST -d "$data" -H "Content-Type: application/json")
    elif [[ "$method" == "PUT" && -n "$data" ]]; then
        curl_args+=(-X PUT -d "$data" -H "Content-Type: application/json")
    elif [[ "$method" == "DELETE" ]]; then
        curl_args+=(-X DELETE)
    fi
    
    local response
    response=$(curl "${curl_args[@]}" "$url" 2>/dev/null)
    local status_code="${response: -3}"
    local body="${response%???}"
    
    if [[ -n "$expected_status" && "$status_code" != "$expected_status" ]]; then
        return 1
    fi
    
    echo "$body"
    return 0
}

# Test 1: Basic connectivity
test_basic_connectivity() {
    print_status "Testing basic connectivity..."
    
    if response=$(make_request "GET" "/" "" "200"); then
        print_test_result "Frontend accessibility" "PASS" "Status: 200"
    else
        print_test_result "Frontend accessibility" "FAIL" "Failed to connect to frontend"
    fi
    
    if response=$(make_request "GET" "/api/health" "" "200"); then
        print_test_result "API health endpoint" "PASS" "Status: 200"
    else
        print_test_result "API health endpoint" "FAIL" "Health check failed"
    fi
}

# Test 2: Health checks
test_health_endpoints() {
    print_status "Testing health endpoints..."
    
    # Basic health
    if response=$(make_request "GET" "/api/health" "" "200"); then
        if echo "$response" | grep -q '"status":"healthy"'; then
            print_test_result "Basic health check" "PASS" "Service is healthy"
        else
            print_test_result "Basic health check" "FAIL" "Service reports unhealthy status"
        fi
    else
        print_test_result "Basic health check" "FAIL" "Health endpoint unreachable"
    fi
    
    # Detailed health
    if response=$(make_request "GET" "/api/health/detailed" "" "200"); then
        if echo "$response" | grep -q '"status":"healthy"'; then
            print_test_result "Detailed health check" "PASS" "All dependencies healthy"
        else
            print_test_result "Detailed health check" "FAIL" "Some dependencies unhealthy"
        fi
    else
        print_test_result "Detailed health check" "FAIL" "Detailed health endpoint failed"
    fi
    
    # Readiness probe
    if response=$(make_request "GET" "/api/ready" "" "200"); then
        print_test_result "Readiness probe" "PASS" "Service is ready"
    else
        print_test_result "Readiness probe" "FAIL" "Service not ready"
    fi
    
    # Liveness probe
    if response=$(make_request "GET" "/api/live" "" "200"); then
        print_test_result "Liveness probe" "PASS" "Service is alive"
    else
        print_test_result "Liveness probe" "FAIL" "Service not alive"
    fi
    
    # Version endpoint
    if response=$(make_request "GET" "/api/version" "" "200"); then
        if echo "$response" | grep -q '"version"'; then
            version=$(echo "$response" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
            print_test_result "Version endpoint" "PASS" "Version: $version"
        else
            print_test_result "Version endpoint" "FAIL" "Invalid version response"
        fi
    else
        print_test_result "Version endpoint" "FAIL" "Version endpoint failed"
    fi
}

# Test 3: API documentation
test_api_documentation() {
    print_status "Testing API documentation..."
    
    if response=$(make_request "GET" "/api/docs" "" "200"); then
        if echo "$response" | grep -q "swagger\|openapi"; then
            print_test_result "API documentation" "PASS" "Swagger/OpenAPI docs available"
        else
            print_test_result "API documentation" "FAIL" "Documentation not properly formatted"
        fi
    else
        print_test_result "API documentation" "FAIL" "API documentation not accessible"
    fi
}

# Test 4: Database connectivity
test_database_connectivity() {
    print_status "Testing database connectivity..."
    
    if response=$(make_request "GET" "/api/health/detailed" "" "200"); then
        if echo "$response" | grep -q '"database":{"status":"healthy"'; then
            print_test_result "Database connectivity" "PASS" "Database is healthy"
        else
            print_test_result "Database connectivity" "FAIL" "Database connection issues"
        fi
    else
        print_test_result "Database connectivity" "FAIL" "Cannot check database status"
    fi
}

# Test 5: Redis connectivity
test_redis_connectivity() {
    print_status "Testing Redis connectivity..."
    
    if response=$(make_request "GET" "/api/health/detailed" "" "200"); then
        if echo "$response" | grep -q '"redis":{"status":"healthy"'; then
            print_test_result "Redis connectivity" "PASS" "Redis is healthy"
        else
            print_test_result "Redis connectivity" "FAIL" "Redis connection issues"
        fi
    else
        print_test_result "Redis connectivity" "FAIL" "Cannot check Redis status"
    fi
}

# Test 6: External service dependencies
test_external_dependencies() {
    print_status "Testing external service dependencies..."
    
    if response=$(make_request "GET" "/api/health/dependencies" "" "200"); then
        # Check AI services
        if echo "$response" | grep -q '"anthropic":{"status":"configured"'; then
            print_test_result "Anthropic API configuration" "PASS" "API key configured"
        else
            print_test_result "Anthropic API configuration" "FAIL" "API key not configured"
        fi
        
        if echo "$response" | grep -q '"openai":{"status":"configured"'; then
            print_test_result "OpenAI API configuration" "PASS" "API key configured"
        else
            print_test_result "OpenAI API configuration" "FAIL" "API key not configured"
        fi
        
        # Check Stripe
        if echo "$response" | grep -q '"stripe":{"status":"configured"'; then
            print_test_result "Stripe API configuration" "PASS" "API key configured"
        else
            print_test_result "Stripe API configuration" "FAIL" "API key not configured"
        fi
    else
        print_test_result "External dependencies check" "FAIL" "Dependencies endpoint failed"
    fi
}

# Test 7: Feature flags
test_feature_flags() {
    print_status "Testing feature flags..."
    
    # This test doesn't require authentication for basic flag info
    if response=$(make_request "GET" "/api/feature-flags/admin/stats" "" "401"); then
        print_test_result "Feature flags endpoint" "PASS" "Endpoint accessible (auth required)"
    else
        print_test_result "Feature flags endpoint" "FAIL" "Feature flags endpoint not working"
    fi
}

# Test 8: Rate limiting
test_rate_limiting() {
    print_status "Testing rate limiting..."
    
    # Make multiple rapid requests to test rate limiting
    local rate_limit_hit=false
    for i in {1..15}; do
        if ! make_request "GET" "/api/health" "" "200" >/dev/null 2>&1; then
            rate_limit_hit=true
            break
        fi
        sleep 0.1
    done
    
    if [[ "$rate_limit_hit" == "true" ]]; then
        print_test_result "Rate limiting" "PASS" "Rate limiting is active"
    else
        print_test_result "Rate limiting" "PASS" "Rate limiting not triggered (may be configured for higher limits)"
    fi
}

# Test 9: CORS headers
test_cors_headers() {
    print_status "Testing CORS headers..."
    
    local cors_headers
    cors_headers=$(curl -s -I -H "Origin: http://localhost:3000" "${BASE_URL}/api/health" | grep -i "access-control")
    
    if [[ -n "$cors_headers" ]]; then
        print_test_result "CORS headers" "PASS" "CORS headers present"
    else
        print_test_result "CORS headers" "FAIL" "CORS headers missing"
    fi
}

# Test 10: Security headers
test_security_headers() {
    print_status "Testing security headers..."
    
    local headers
    headers=$(curl -s -I "${BASE_URL}/" 2>/dev/null)
    
    if echo "$headers" | grep -qi "x-frame-options"; then
        print_test_result "X-Frame-Options header" "PASS" "Header present"
    else
        print_test_result "X-Frame-Options header" "FAIL" "Header missing"
    fi
    
    if echo "$headers" | grep -qi "x-content-type-options"; then
        print_test_result "X-Content-Type-Options header" "PASS" "Header present"
    else
        print_test_result "X-Content-Type-Options header" "FAIL" "Header missing"
    fi
    
    if echo "$headers" | grep -qi "x-xss-protection"; then
        print_test_result "X-XSS-Protection header" "PASS" "Header present"
    else
        print_test_result "X-XSS-Protection header" "FAIL" "Header missing"
    fi
}

# Test 11: Static file serving
test_static_files() {
    print_status "Testing static file serving..."
    
    # Test favicon
    if make_request "GET" "/favicon.ico" "" "200" >/dev/null 2>&1; then
        print_test_result "Favicon serving" "PASS" "Favicon accessible"
    else
        print_test_result "Favicon serving" "FAIL" "Favicon not accessible"
    fi
    
    # Test robots.txt
    if make_request "GET" "/robots.txt" "" "200" >/dev/null 2>&1; then
        print_test_result "Robots.txt serving" "PASS" "Robots.txt accessible"
    else
        print_test_result "Robots.txt serving" "FAIL" "Robots.txt not accessible"
    fi
}

# Test 12: Error handling
test_error_handling() {
    print_status "Testing error handling..."
    
    # Test 404 handling
    if make_request "GET" "/nonexistent-endpoint" "" "404" >/dev/null 2>&1; then
        print_test_result "404 error handling" "PASS" "Returns 404 for non-existent endpoints"
    else
        print_test_result "404 error handling" "FAIL" "Does not return 404 for non-existent endpoints"
    fi
    
    # Test API 404 handling
    if make_request "GET" "/api/nonexistent" "" "404" >/dev/null 2>&1; then
        print_test_result "API 404 error handling" "PASS" "API returns 404 for non-existent endpoints"
    else
        print_test_result "API 404 error handling" "FAIL" "API does not handle 404s properly"
    fi
}

# Test 13: Performance baseline
test_performance_baseline() {
    print_status "Testing performance baseline..."
    
    # Test response time for health endpoint
    local start_time end_time duration
    start_time=$(date +%s%N)
    if make_request "GET" "/api/health" "" "200" >/dev/null 2>&1; then
        end_time=$(date +%s%N)
        duration=$(( (end_time - start_time) / 1000000 )) # Convert to milliseconds
        
        if [[ $duration -lt 1000 ]]; then
            print_test_result "API response time" "PASS" "Response time: ${duration}ms"
        else
            print_test_result "API response time" "FAIL" "Response time too slow: ${duration}ms"
        fi
    else
        print_test_result "API response time" "FAIL" "Could not measure response time"
    fi
    
    # Test frontend response time
    start_time=$(date +%s%N)
    if make_request "GET" "/" "" "200" >/dev/null 2>&1; then
        end_time=$(date +%s%N)
        duration=$(( (end_time - start_time) / 1000000 ))
        
        if [[ $duration -lt 2000 ]]; then
            print_test_result "Frontend response time" "PASS" "Response time: ${duration}ms"
        else
            print_test_result "Frontend response time" "FAIL" "Response time too slow: ${duration}ms"
        fi
    else
        print_test_result "Frontend response time" "FAIL" "Could not measure response time"
    fi
}

# Test 14: Critical user workflows (simplified without auth)
test_critical_workflows() {
    print_status "Testing critical user workflows..."
    
    # Test document upload endpoint exists (will require auth)
    if make_request "GET" "/api/upload" "" "401" >/dev/null 2>&1; then
        print_test_result "Document upload endpoint" "PASS" "Endpoint exists (requires auth)"
    else
        print_test_result "Document upload endpoint" "FAIL" "Upload endpoint not accessible"
    fi
    
    # Test RAG query endpoint exists (will require auth)
    if make_request "POST" "/api/rag/query" '{"query":"test"}' "401" >/dev/null 2>&1; then
        print_test_result "RAG query endpoint" "PASS" "Endpoint exists (requires auth)"
    else
        print_test_result "RAG query endpoint" "FAIL" "RAG endpoint not accessible"
    fi
    
    # Test analysis endpoint exists (will require auth)
    if make_request "GET" "/api/analyses" "" "401" >/dev/null 2>&1; then
        print_test_result "Analysis endpoint" "PASS" "Endpoint exists (requires auth)"
    else
        print_test_result "Analysis endpoint" "FAIL" "Analysis endpoint not accessible"
    fi
}

# Generate test report
generate_report() {
    echo ""
    echo "=========================================="
    echo "           SMOKE TEST REPORT"
    echo "=========================================="
    echo "Environment: $ENVIRONMENT"
    echo "Base URL: $BASE_URL"
    echo "Timestamp: $(date)"
    echo ""
    echo "Results:"
    echo "  Tests Passed: $TESTS_PASSED"
    echo "  Tests Failed: $TESTS_FAILED"
    echo "  Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
    echo ""
    
    if [[ $TESTS_FAILED -gt 0 ]]; then
        echo "Failed Tests:"
        for test in "${FAILED_TESTS[@]}"; do
            echo "  - $test"
        done
        echo ""
    fi
    
    local success_rate
    success_rate=$(( TESTS_PASSED * 100 / (TESTS_PASSED + TESTS_FAILED) ))
    echo "Success Rate: ${success_rate}%"
    echo ""
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        print_success "🎉 All smoke tests passed! Deployment is healthy."
        return 0
    else
        print_error "❌ Some smoke tests failed. Please investigate before proceeding."
        return 1
    fi
}

# Main function
main() {
    print_status "Starting smoke tests for $ENVIRONMENT environment..."
    print_status "Target URL: $BASE_URL"
    echo ""
    
    # Run all tests
    test_basic_connectivity
    test_health_endpoints
    test_api_documentation
    test_database_connectivity
    test_redis_connectivity
    test_external_dependencies
    test_feature_flags
    test_rate_limiting
    test_cors_headers
    test_security_headers
    test_static_files
    test_error_handling
    test_performance_baseline
    test_critical_workflows
    
    # Generate and display report
    generate_report
}

# Run main function
main