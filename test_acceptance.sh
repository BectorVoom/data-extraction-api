#!/bin/bash

# End-to-End Acceptance Tests for Data Extraction API
# This script tests all the acceptance criteria defined in the requirements

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
BACKEND_PID=""

# Configuration
BACKEND_URL="http://localhost:8000"
BACKEND_DIR="rest_api_duckdb"
FRONTEND_DIR="frontend_svelte_tailwindcss"

log() {
    echo -e "${BLUE}$(date '+%H:%M:%S')${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

error() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Cleanup function
cleanup() {
    if [ ! -z "$BACKEND_PID" ]; then
        log "Stopping backend server (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null || true
        wait $BACKEND_PID 2>/dev/null || true
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Start backend server
start_backend() {
    log "Starting FastAPI backend server..."
    
    if [ ! -d "$BACKEND_DIR" ]; then
        error "Backend directory '$BACKEND_DIR' not found"
        exit 1
    fi
    
    # Start server in background
    cd $BACKEND_DIR
    uv run python -m app.main &
    BACKEND_PID=$!
    cd ..
    
    # Wait for server to start
    log "Waiting for backend server to start..."
    for i in {1..30}; do
        if curl -s "$BACKEND_URL/" > /dev/null 2>&1; then
            success "Backend server started successfully"
            return 0
        fi
        sleep 1
        if [ $((i % 5)) -eq 0 ]; then
            log "Still waiting... (attempt $i/30)"
        fi
    done
    
    error "Backend server failed to start within timeout"
    exit 1
}

# Test API endpoints
test_api_endpoints() {
    log "Testing API endpoints..."
    
    # Test 1: Root endpoint
    if curl -s "$BACKEND_URL/" | grep -q "Data Extraction API"; then
        success "Root endpoint working"
    else
        error "Root endpoint test failed"
    fi
    
    # Test 2: Health check
    if curl -s "$BACKEND_URL/api/health" | grep -q '"status":"healthy"'; then
        success "Health check endpoint working"
    else
        error "Health check endpoint test failed"
    fi
    
    # Test 3: Database info
    if curl -s "$BACKEND_URL/api/info" | grep -q '"database_info"'; then
        success "Database info endpoint working"
    else
        error "Database info endpoint test failed"
    fi
}

# Test query functionality
test_query_functionality() {
    log "Testing query functionality..."
    
    # Test 4: Valid query (should return 200 with data array)
    response=$(curl -s -w "%{http_code}" -H "Content-Type: application/json" \
        -d '{"id": "12345", "fromDate": "2024/01/01", "toDate": "2024/12/31"}' \
        "$BACKEND_URL/api/query")
    
    http_code="${response: -3}"
    body="${response%???}"
    
    if [ "$http_code" = "200" ] && echo "$body" | grep -q '"data":\[' && echo "$body" | grep -q '"count":'; then
        count=$(echo "$body" | grep -o '"count":[0-9]*' | cut -d':' -f2)
        success "Valid query returned HTTP 200 with $count results"
    else
        error "Valid query test failed (HTTP $http_code)"
    fi
    
    # Test 5: Query with no results
    response=$(curl -s -w "%{http_code}" -H "Content-Type: application/json" \
        -d '{"id": "nonexistent", "fromDate": "2024/01/01", "toDate": "2024/12/31"}' \
        "$BACKEND_URL/api/query")
    
    http_code="${response: -3}"
    body="${response%???}"
    
    if [ "$http_code" = "200" ] && echo "$body" | grep -q '"count":0'; then
        success "No results query handled correctly"
    else
        error "No results query test failed (HTTP $http_code)"
    fi
}

# Test validation (Acceptance criteria: malformed dates return 400/422)
test_validation() {
    log "Testing input validation..."
    
    # Test 6: Invalid date format (should return 422)
    response=$(curl -s -w "%{http_code}" -H "Content-Type: application/json" \
        -d '{"id": "12345", "fromDate": "2024-01-01", "toDate": "2024/12/31"}' \
        "$BACKEND_URL/api/query")
    
    http_code="${response: -3}"
    
    if [ "$http_code" = "422" ]; then
        success "Invalid date format rejected with HTTP 422"
    else
        error "Invalid date format test failed (HTTP $http_code, expected 422)"
    fi
    
    # Test 7: Invalid date range (should return 422)
    response=$(curl -s -w "%{http_code}" -H "Content-Type: application/json" \
        -d '{"id": "12345", "fromDate": "2024/12/31", "toDate": "2024/01/01"}' \
        "$BACKEND_URL/api/query")
    
    http_code="${response: -3}"
    
    if [ "$http_code" = "422" ]; then
        success "Invalid date range rejected with HTTP 422"
    else
        error "Invalid date range test failed (HTTP $http_code, expected 422)"
    fi
    
    # Test 8: Missing fields (should return 422)
    response=$(curl -s -w "%{http_code}" -H "Content-Type: application/json" \
        -d '{"id": "12345"}' \
        "$BACKEND_URL/api/query")
    
    http_code="${response: -3}"
    
    if [ "$http_code" = "422" ]; then
        success "Missing fields rejected with HTTP 422"
    else
        error "Missing fields test failed (HTTP $http_code, expected 422)"
    fi
}

# Test CORS configuration
test_cors() {
    log "Testing CORS configuration..."
    
    # Preflight request
    response=$(curl -s -w "%{http_code}" -X OPTIONS \
        -H "Origin: http://localhost:5173" \
        -H "Access-Control-Request-Method: POST" \
        -H "Access-Control-Request-Headers: Content-Type" \
        "$BACKEND_URL/api/query")
    
    http_code="${response: -3}"
    
    if [ "$http_code" = "200" ]; then
        success "CORS preflight request handled correctly"
    else
        error "CORS test failed (HTTP $http_code)"
    fi
}

# Test frontend build
test_frontend_build() {
    log "Testing frontend build..."
    
    if [ ! -d "$FRONTEND_DIR" ]; then
        warning "Frontend directory not found, skipping build test"
        return
    fi
    
    cd $FRONTEND_DIR
    if bun run build > /dev/null 2>&1; then
        success "Frontend builds successfully"
    else
        error "Frontend build failed"
    fi
    cd ..
}

# Run unit tests
test_backend_tests() {
    log "Running backend unit and integration tests..."
    
    cd $BACKEND_DIR
    if uv run pytest > /dev/null 2>&1; then
        success "All backend tests pass"
    else
        error "Backend tests failed"
    fi
    cd ..
}

# Main execution
main() {
    echo -e "${BOLD}${BLUE}🚀 Starting End-to-End Acceptance Tests${NC}"
    echo "========================================================"
    
    # Start backend
    start_backend
    
    # Run all acceptance tests
    echo
    echo -e "${BOLD}Running Acceptance Criteria Tests...${NC}"
    test_api_endpoints
    test_query_functionality
    test_validation
    test_cors
    
    echo
    echo -e "${BOLD}Running Additional Tests...${NC}"
    test_backend_tests
    test_frontend_build
    
    # Summary
    echo
    echo "========================================================"
    TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
    log "Test Summary:"
    echo "  Total tests: $TOTAL_TESTS"
    echo -e "  ${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "  ${RED}Failed: $TESTS_FAILED${NC}"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo
        echo -e "${BOLD}${GREEN}🎉 All acceptance tests passed!${NC}"
        echo -e "${BOLD}${GREEN}✅ System meets all acceptance criteria${NC}"
        exit 0
    else
        echo
        echo -e "${BOLD}${RED}❌ $TESTS_FAILED test(s) failed${NC}"
        exit 1
    fi
}

# Run main function
main "$@"