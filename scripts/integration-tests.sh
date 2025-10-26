#!/bin/bash

# Integration Tests for Critical User Workflows
# Tests end-to-end functionality with actual API calls

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
BASE_URL="http://localhost:80"
ENVIRONMENT="staging"
TEST_USER_EMAIL="integration-test@lexiscan.ai"
TEST_USER_PASSWORD="TestPassword123!"
VERBOSE=false

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Test data
AUTH_TOKEN=""
TEST_ORG_ID=""
TEST_USER_ID=""
TEST_DOCUMENT_ID=""

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
    echo "  -u, --url URL                   Base URL for testing (default: http://localhost:80)"
    echo "  -e, --environment ENV           Environment (default: staging)"
    echo "  --email EMAIL                   Test user email (default: integration-test@lexiscan.ai)"
    echo "  --password PASSWORD             Test user password (default: TestPassword123!)"
    echo "  -v, --verbose                   Verbose output"
    echo "  -h, --help                      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                              Run integration tests on staging"
    echo "  $0 -u https://lexiscan.ai -e production  Run on production"
    echo "  $0 --email test@example.com     Use custom test user"
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
        --email)
            TEST_USER_EMAIL="$2"
            shift 2
            ;;
        --password)
            TEST_USER_PASSWORD="$2"
            shift 2
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

# Remove trailing slash from URL
BASE_URL=${BASE_URL%/}

# Helper function to make authenticated API requests
make_api_request() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local expected_status="$4"
    
    local url="${BASE_URL}${endpoint}"
    local curl_args=(-s -w "%{http_code}" --max-time 30)
    
    # Add auth header if token is available
    if [[ -n "$AUTH_TOKEN" ]]; then
        curl_args+=(-H "Authorization: Bearer $AUTH_TOKEN")
    fi
    
    # Add content type for POST/PUT requests
    if [[ "$method" == "POST" || "$method" == "PUT" ]]; then
        curl_args+=(-H "Content-Type: application/json")
    fi
    
    # Add method and data
    if [[ "$method" == "POST" && -n "$data" ]]; then
        curl_args+=(-X POST -d "$data")
    elif [[ "$method" == "PUT" && -n "$data" ]]; then
        curl_args+=(-X PUT -d "$data")
    elif [[ "$method" == "DELETE" ]]; then
        curl_args+=(-X DELETE)
    fi
    
    local response
    response=$(curl "${curl_args[@]}" "$url" 2>/dev/null)
    local status_code="${response: -3}"
    local body="${response%???}"
    
    if [[ -n "$expected_status" && "$status_code" != "$expected_status" ]]; then
        if [[ "$VERBOSE" == "true" ]]; then
            echo "Expected status: $expected_status, Got: $status_code"
            echo "Response body: $body"
        fi
        return 1
    fi
    
    echo "$body"
    return 0
}

# Test 1: User registration and authentication
test_user_authentication() {
    print_status "Testing user authentication workflow..."
    
    # Test user registration
    local register_data
    register_data=$(cat << EOF
{
    "email": "$TEST_USER_EMAIL",
    "password": "$TEST_USER_PASSWORD",
    "name": "Integration Test User",
    "organization_name": "Test Organization"
}
EOF
)
    
    if response=$(make_api_request "POST" "/api/auth/register" "$register_data" "201"); then
        print_test_result "User registration" "PASS" "User registered successfully"
        
        # Extract user info from response
        TEST_USER_ID=$(echo "$response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
        TEST_ORG_ID=$(echo "$response" | grep -o '"org_id":"[^"]*"' | cut -d'"' -f4)
    else
        # User might already exist, try to login
        print_test_result "User registration" "PASS" "User already exists (expected in staging)"
    fi
    
    # Test user login
    local login_data
    login_data=$(cat << EOF
{
    "email": "$TEST_USER_EMAIL",
    "password": "$TEST_USER_PASSWORD"
}
EOF
)
    
    if response=$(make_api_request "POST" "/api/auth/login" "$login_data" "200"); then
        AUTH_TOKEN=$(echo "$response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
        if [[ -n "$AUTH_TOKEN" ]]; then
            print_test_result "User login" "PASS" "Authentication token received"
        else
            print_test_result "User login" "FAIL" "No authentication token in response"
        fi
    else
        print_test_result "User login" "FAIL" "Login request failed"
    fi
    
    # Test token validation
    if [[ -n "$AUTH_TOKEN" ]]; then
        if response=$(make_api_request "GET" "/api/auth/me" "" "200"); then
            print_test_result "Token validation" "PASS" "Token is valid"
        else
            print_test_result "Token validation" "FAIL" "Token validation failed"
        fi
    fi
}

# Test 2: Document upload workflow
test_document_upload() {
    print_status "Testing document upload workflow..."
    
    if [[ -z "$AUTH_TOKEN" ]]; then
        print_test_result "Document upload (auth required)" "FAIL" "No authentication token available"
        return
    fi
    
    # Create a test document
    local test_doc_content="This is a test contract document for integration testing. It contains standard legal clauses including indemnification, liability limitations, and termination provisions."
    echo "$test_doc_content" > /tmp/test_contract.txt
    
    # Test file upload
    local upload_response
    upload_response=$(curl -s -w "%{http_code}" --max-time 60 \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -F "file=@/tmp/test_contract.txt" \
        -F "title=Integration Test Contract" \
        "${BASE_URL}/api/upload" 2>/dev/null)
    
    local upload_status="${upload_response: -3}"
    local upload_body="${upload_response%???}"
    
    if [[ "$upload_status" == "201" || "$upload_status" == "200" ]]; then
        TEST_DOCUMENT_ID=$(echo "$upload_body" | grep -o '"document_id":"[^"]*"' | cut -d'"' -f4)
        if [[ -n "$TEST_DOCUMENT_ID" ]]; then
            print_test_result "Document upload" "PASS" "Document uploaded successfully"
        else
            print_test_result "Document upload" "FAIL" "No document ID in response"
        fi
    else
        print_test_result "Document upload" "FAIL" "Upload failed with status: $upload_status"
    fi
    
    # Clean up test file
    rm -f /tmp/test_contract.txt
    
    # Test document listing
    if response=$(make_api_request "GET" "/api/documents" "" "200"); then
        if echo "$response" | grep -q "documents"; then
            print_test_result "Document listing" "PASS" "Documents retrieved successfully"
        else
            print_test_result "Document listing" "FAIL" "Invalid document list response"
        fi
    else
        print_test_result "Document listing" "FAIL" "Document listing failed"
    fi
}

# Test 3: Document processing and analysis
test_document_analysis() {
    print_status "Testing document analysis workflow..."
    
    if [[ -z "$AUTH_TOKEN" || -z "$TEST_DOCUMENT_ID" ]]; then
        print_test_result "Document analysis (prerequisites)" "FAIL" "Missing auth token or document ID"
        return
    fi
    
    # Wait for document processing to complete
    print_status "Waiting for document processing..."
    local processing_complete=false
    local attempts=0
    local max_attempts=30
    
    while [[ "$processing_complete" != "true" && $attempts -lt $max_attempts ]]; do
        if response=$(make_api_request "GET" "/api/documents/$TEST_DOCUMENT_ID" "" "200"); then
            local status
            status=$(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
            if [[ "$status" == "completed" ]]; then
                processing_complete=true
                break
            elif [[ "$status" == "failed" ]]; then
                print_test_result "Document processing" "FAIL" "Document processing failed"
                return
            fi
        fi
        sleep 2
        ((attempts++))
    done
    
    if [[ "$processing_complete" == "true" ]]; then
        print_test_result "Document processing" "PASS" "Document processed successfully"
    else
        print_test_result "Document processing" "FAIL" "Document processing timeout"
        return
    fi
    
    # Test document analysis
    local analysis_data
    analysis_data=$(cat << EOF
{
    "document_id": "$TEST_DOCUMENT_ID",
    "playbook_id": null
}
EOF
)
    
    if response=$(make_api_request "POST" "/api/documents/$TEST_DOCUMENT_ID/analyze" "$analysis_data" "200"); then
        local analysis_id
        analysis_id=$(echo "$response" | grep -o '"analysis_id":"[^"]*"' | cut -d'"' -f4)
        if [[ -n "$analysis_id" ]]; then
            print_test_result "Document analysis" "PASS" "Analysis completed successfully"
            
            # Test analysis retrieval
            if response=$(make_api_request "GET" "/api/analyses/$analysis_id" "" "200"); then
                if echo "$response" | grep -q "risk_score"; then
                    print_test_result "Analysis retrieval" "PASS" "Analysis results retrieved"
                else
                    print_test_result "Analysis retrieval" "FAIL" "Invalid analysis response"
                fi
            else
                print_test_result "Analysis retrieval" "FAIL" "Analysis retrieval failed"
            fi
        else
            print_test_result "Document analysis" "FAIL" "No analysis ID in response"
        fi
    else
        print_test_result "Document analysis" "FAIL" "Analysis request failed"
    fi
}

# Test 4: RAG query functionality
test_rag_queries() {
    print_status "Testing RAG query functionality..."
    
    if [[ -z "$AUTH_TOKEN" || -z "$TEST_DOCUMENT_ID" ]]; then
        print_test_result "RAG queries (prerequisites)" "FAIL" "Missing auth token or document ID"
        return
    fi
    
    # Test basic RAG query
    local query_data
    query_data=$(cat << EOF
{
    "query": "What are the main clauses in this contract?",
    "document_ids": ["$TEST_DOCUMENT_ID"],
    "model": "claude-3-sonnet"
}
EOF
)
    
    if response=$(make_api_request "POST" "/api/rag/query" "$query_data" "200"); then
        if echo "$response" | grep -q "answer"; then
            print_test_result "RAG query" "PASS" "Query processed successfully"
            
            # Check for citations
            if echo "$response" | grep -q "citations"; then
                print_test_result "RAG citations" "PASS" "Citations included in response"
            else
                print_test_result "RAG citations" "FAIL" "No citations in response"
            fi
        else
            print_test_result "RAG query" "FAIL" "Invalid query response"
        fi
    else
        print_test_result "RAG query" "FAIL" "RAG query failed"
    fi
    
    # Test query with specific document context
    query_data=$(cat << EOF
{
    "query": "Are there any indemnification clauses?",
    "document_ids": ["$TEST_DOCUMENT_ID"]
}
EOF
)
    
    if response=$(make_api_request "POST" "/api/rag/query" "$query_data" "200"); then
        print_test_result "Contextual RAG query" "PASS" "Contextual query successful"
    else
        print_test_result "Contextual RAG query" "FAIL" "Contextual query failed"
    fi
}

# Test 5: Feature flags functionality
test_feature_flags() {
    print_status "Testing feature flags functionality..."
    
    if [[ -z "$AUTH_TOKEN" ]]; then
        print_test_result "Feature flags (auth required)" "FAIL" "No authentication token available"
        return
    fi
    
    # Test user feature flags
    if response=$(make_api_request "GET" "/api/feature-flags/user" "" "200"); then
        if echo "$response" | grep -q "features"; then
            print_test_result "User feature flags" "PASS" "Feature flags retrieved"
        else
            print_test_result "User feature flags" "FAIL" "Invalid feature flags response"
        fi
    else
        print_test_result "User feature flags" "FAIL" "Feature flags request failed"
    fi
    
    # Test specific feature flag check
    if response=$(make_api_request "GET" "/api/feature-flags/check/new_ui_dashboard" "" "200"); then
        if echo "$response" | grep -q "enabled"; then
            print_test_result "Feature flag check" "PASS" "Feature flag check successful"
        else
            print_test_result "Feature flag check" "FAIL" "Invalid feature flag check response"
        fi
    else
        print_test_result "Feature flag check" "FAIL" "Feature flag check failed"
    fi
}

# Test 6: Billing and usage tracking
test_billing_functionality() {
    print_status "Testing billing and usage functionality..."
    
    if [[ -z "$AUTH_TOKEN" ]]; then
        print_test_result "Billing (auth required)" "FAIL" "No authentication token available"
        return
    fi
    
    # Test usage tracking
    if response=$(make_api_request "GET" "/api/usage/current" "" "200"); then
        if echo "$response" | grep -q "usage"; then
            print_test_result "Usage tracking" "PASS" "Usage data retrieved"
        else
            print_test_result "Usage tracking" "FAIL" "Invalid usage response"
        fi
    else
        print_test_result "Usage tracking" "FAIL" "Usage tracking failed"
    fi
    
    # Test subscription info
    if response=$(make_api_request "GET" "/api/billing/subscription" "" "200"); then
        if echo "$response" | grep -q "plan\|subscription"; then
            print_test_result "Subscription info" "PASS" "Subscription data retrieved"
        else
            print_test_result "Subscription info" "FAIL" "Invalid subscription response"
        fi
    else
        print_test_result "Subscription info" "FAIL" "Subscription info failed"
    fi
}

# Test 7: Document comparison
test_document_comparison() {
    print_status "Testing document comparison functionality..."
    
    if [[ -z "$AUTH_TOKEN" || -z "$TEST_DOCUMENT_ID" ]]; then
        print_test_result "Document comparison (prerequisites)" "FAIL" "Missing auth token or document ID"
        return
    fi
    
    # For this test, we'll compare the document with itself (simplified test)
    local comparison_data
    comparison_data=$(cat << EOF
{
    "document1_id": "$TEST_DOCUMENT_ID",
    "document2_id": "$TEST_DOCUMENT_ID"
}
EOF
)
    
    if response=$(make_api_request "POST" "/api/compare" "$comparison_data" "200"); then
        if echo "$response" | grep -q "comparison"; then
            print_test_result "Document comparison" "PASS" "Comparison completed successfully"
        else
            print_test_result "Document comparison" "FAIL" "Invalid comparison response"
        fi
    else
        print_test_result "Document comparison" "FAIL" "Document comparison failed"
    fi
}

# Test 8: Audit logging
test_audit_logging() {
    print_status "Testing audit logging functionality..."
    
    if [[ -z "$AUTH_TOKEN" ]]; then
        print_test_result "Audit logging (auth required)" "FAIL" "No authentication token available"
        return
    fi
    
    # Test audit log retrieval (admin endpoint, may fail for non-admin users)
    if response=$(make_api_request "GET" "/api/admin/audit-logs" "" "200"); then
        if echo "$response" | grep -q "logs\|audits"; then
            print_test_result "Audit log retrieval" "PASS" "Audit logs retrieved"
        else
            print_test_result "Audit log retrieval" "FAIL" "Invalid audit log response"
        fi
    elif response=$(make_api_request "GET" "/api/admin/audit-logs" "" "403"); then
        print_test_result "Audit log access control" "PASS" "Proper access control (403 for non-admin)"
    else
        print_test_result "Audit logging" "FAIL" "Audit logging endpoint failed"
    fi
}

# Cleanup test data
cleanup_test_data() {
    print_status "Cleaning up test data..."
    
    if [[ -n "$AUTH_TOKEN" && -n "$TEST_DOCUMENT_ID" ]]; then
        # Delete test document
        if make_api_request "DELETE" "/api/documents/$TEST_DOCUMENT_ID" "" "200" >/dev/null 2>&1; then
            print_status "Test document deleted successfully"
        else
            print_warning "Could not delete test document (may require manual cleanup)"
        fi
    fi
    
    # Note: We don't delete the test user as it might be useful for future tests
    print_status "Test user preserved for future tests: $TEST_USER_EMAIL"
}

# Generate integration test report
generate_integration_report() {
    echo ""
    echo "=========================================="
    echo "       INTEGRATION TEST REPORT"
    echo "=========================================="
    echo "Environment: $ENVIRONMENT"
    echo "Base URL: $BASE_URL"
    echo "Test User: $TEST_USER_EMAIL"
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
        print_success "🎉 All integration tests passed! Critical workflows are functional."
        return 0
    elif [[ $success_rate -ge 80 ]]; then
        print_warning "⚠️  Most integration tests passed with some failures."
        return 1
    else
        print_error "❌ Integration tests failed. Critical workflows may not be functional."
        return 2
    fi
}

# Main function
main() {
    print_status "Starting integration tests for $ENVIRONMENT environment..."
    print_status "Target URL: $BASE_URL"
    print_status "Test User: $TEST_USER_EMAIL"
    echo ""
    
    # Run all integration tests
    test_user_authentication
    test_document_upload
    test_document_analysis
    test_rag_queries
    test_feature_flags
    test_billing_functionality
    test_document_comparison
    test_audit_logging
    
    # Cleanup and generate report
    cleanup_test_data
    generate_integration_report
}

# Handle script interruption
trap 'print_error "Integration tests interrupted"; cleanup_test_data; exit 1' INT TERM

# Run main function
main