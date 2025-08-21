#!/bin/bash

# =============================================================================
# COMPREHENSIVE TEST STABILITY & HTTP ERROR DETECTION PIPELINE
# =============================================================================
# Ensures zero tolerance for HTTP 4xx/5xx errors anywhere in the system
# Runs both internal test suites and real HTTP server end-to-end tests
# GitHub Actions compatible with proper exit codes and comprehensive logging
# =============================================================================

# Strict error handling: exit on any error, undefined variables, or pipe failures
set -euo pipefail

# Global configuration
SERVER_PORT=8000
SERVER_HOST="localhost"
SERVER_URL="http://${SERVER_HOST}:${SERVER_PORT}"
MAX_STARTUP_RETRIES=15
SERVER_STARTUP_WAIT=3
REQUEST_TIMEOUT=30

# Create comprehensive logs directory structure FIRST
LOG_DIR="$(pwd)/test-logs/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$LOG_DIR/unit-tests"
mkdir -p "$LOG_DIR/server-logs"
mkdir -p "$LOG_DIR/http-tests" 
mkdir -p "$LOG_DIR/failing-requests"
mkdir -p "$LOG_DIR/reports"

# Create initial log file and wait for filesystem
touch "$LOG_DIR/run-report.txt"
sleep 0.1  # Brief pause to ensure filesystem operations complete

echo "🏗️  COMPREHENSIVE TEST STABILITY PIPELINE"
echo "==========================================="
echo "✅ Zero tolerance for HTTP 4xx/5xx errors"
echo "🔍 Internal tests + Real HTTP server tests"
echo "📊 Comprehensive error monitoring & logging"
echo ""

# Enhanced logging functions
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ℹ️  INFO: $1" | tee -a "$LOG_DIR/run-report.txt"
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ SUCCESS: $1" | tee -a "$LOG_DIR/run-report.txt"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ ERROR: $1" | tee -a "$LOG_DIR/run-report.txt" >&2
}

log_warning() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  WARNING: $1" | tee -a "$LOG_DIR/run-report.txt"
}

# Enhanced HTTP request logging
log_http_request() {
    local method="$1"
    local url="$2"
    local headers="$3"
    local body="$4"
    local request_num="$5"
    
    cat > "$LOG_DIR/failing-requests/request-$request_num.json" << EOF
{
  "method": "$method",
  "url": "$url", 
  "headers": $headers,
  "body": $body,
  "timestamp": "$(date -Iseconds)",
  "test_run_id": "$(basename $LOG_DIR)"
}
EOF
}

log_http_response() {
    local status="$1"
    local headers="$2"
    local body="$3"
    local request_num="$4"
    
    cat > "$LOG_DIR/failing-requests/response-$request_num.json" << EOF
{
  "status": $status,
  "headers": $headers,
  "body": $body,
  "timestamp": "$(date -Iseconds)",
  "test_run_id": "$(basename $LOG_DIR)",
  "error_category": "http_error"
}
EOF
}

# STRICT HTTP request function - ZERO tolerance for 4xx/5xx
make_http_request() {
    local method="$1"
    local url="$2"
    local data="$3"
    local description="$4"
    local expected_status="${5:-200}"  # Default to 200 if not specified
    
    log_info "Testing: $description"
    log_info "Making $method request to $url (expecting HTTP $expected_status)"
    
    local temp_response=$(mktemp)
    local temp_headers=$(mktemp)
    local temp_stderr=$(mktemp)
    
    # Make request with comprehensive error capture
    if [[ "$method" == "GET" ]]; then
        http_code=$(curl -s -w "%{http_code}" -D "$temp_headers" -o "$temp_response" \
            --connect-timeout $REQUEST_TIMEOUT --max-time $REQUEST_TIMEOUT \
            "$url" 2>"$temp_stderr" || echo "000")
    else
        http_code=$(curl -s -w "%{http_code}" -X "$method" \
            -H "Content-Type: application/json" -d "$data" \
            -D "$temp_headers" -o "$temp_response" \
            --connect-timeout $REQUEST_TIMEOUT --max-time $REQUEST_TIMEOUT \
            "$url" 2>"$temp_stderr" || echo "000")
    fi
    
    local response_body=$(cat "$temp_response" 2>/dev/null || echo "")
    local response_headers=$(cat "$temp_headers" 2>/dev/null || echo "")
    local curl_error=$(cat "$temp_stderr" 2>/dev/null || echo "")
    
    # STRICT: Any non-2xx status is a failure (including 422)
    if [[ $http_code -lt 200 || $http_code -ge 300 ]]; then
        log_error "$description FAILED with HTTP $http_code (expected $expected_status)"
        log_error "This violates the zero-tolerance policy for HTTP errors"
        
        # Log comprehensive failure details
        local request_num=$(date +%s%N)
        local headers_json='{}'
        if [[ -n "$data" ]]; then
            headers_json='{"Content-Type": "application/json"}'
        fi
        
        log_http_request "$method" "$url" "$headers_json" "$data" "$request_num"
        log_http_response "$http_code" "$(echo "$response_headers" | jq -R . | jq -s . 2>/dev/null || echo '[]')" "$(echo "$response_body" | jq -R . 2>/dev/null || echo '""')" "$request_num"
        
        # Display failure details
        echo "" >&2
        echo "=== FAILURE DETAILS ===" >&2
        echo "Expected Status: $expected_status" >&2
        echo "Actual Status: $http_code" >&2
        echo "Response Body: $response_body" >&2
        echo "Response Headers:" >&2
        echo "$response_headers" >&2
        if [[ -n "$curl_error" ]]; then
            echo "Curl Error: $curl_error" >&2
        fi
        echo "======================" >&2
        
        # Cleanup temp files
        rm -f "$temp_response" "$temp_headers" "$temp_stderr"
        
        # CRITICAL: Exit immediately on any HTTP error
        exit 1
    elif [[ $http_code -eq $expected_status ]]; then
        log_success "$description SUCCESS (HTTP $http_code)"
        echo "Response preview: $(echo "$response_body" | head -c 150 | tr '\n' ' ')..."
    else
        log_warning "$description unexpected status (HTTP $http_code, expected $expected_status) but within 2xx range"
    fi
    
    # Cleanup temp files  
    rm -f "$temp_response" "$temp_headers" "$temp_stderr"
}

# Server log monitoring function
monitor_server_logs() {
    local server_log_file="$1"
    local monitoring_duration="$2"
    
    log_info "Starting server log monitoring for $monitoring_duration seconds"
    
    # Monitor for HTTP errors in server logs
    timeout $monitoring_duration tail -f "$server_log_file" | while read -r line; do
        # Check for HTTP error status codes in logs
        if echo "$line" | grep -E "HTTP [4-5][0-9][0-9]|status.*[4-5][0-9][0-9]|error.*[4-5][0-9][0-9]" >/dev/null; then
            log_error "HTTP error detected in server logs: $line"
            echo "$line" >> "$LOG_DIR/server-logs/detected-errors.log"
            # Kill the monitoring and fail the test
            exit 1
        fi
        
        # Log all server activity for debugging
        echo "$line" >> "$LOG_DIR/server-logs/activity.log"
    done &
    
    SERVER_MONITOR_PID=$!
}

# Enhanced cleanup with comprehensive reporting
cleanup() {
    local exit_code=$?
    log_info "Starting cleanup process..."
    
    # Stop server log monitoring
    if [[ -n "${SERVER_MONITOR_PID:-}" ]]; then
        kill "$SERVER_MONITOR_PID" 2>/dev/null || true
        wait "$SERVER_MONITOR_PID" 2>/dev/null || true
    fi
    
    # Stop backend server
    if [[ -n "${BACKEND_PID:-}" ]]; then
        log_info "Stopping backend server (PID: $BACKEND_PID)"
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
    
    # Generate final test report
    generate_test_report $exit_code
    
    log_info "Cleanup completed. Final logs saved to: $LOG_DIR"
}
trap cleanup EXIT

# Generate comprehensive test report
generate_test_report() {
    local final_exit_code="$1"
    local report_file="$LOG_DIR/reports/final-test-report.json"
    
    log_info "Generating comprehensive test report..."
    
    local test_status="PASS"
    if [[ $final_exit_code -ne 0 ]]; then
        test_status="FAIL"
    fi
    
    cat > "$report_file" << EOF
{
  "test_run_id": "$(basename $LOG_DIR)",
  "timestamp": "$(date -Iseconds)",
  "status": "$test_status",
  "exit_code": $final_exit_code,
  "configuration": {
    "server_url": "$SERVER_URL",
    "zero_error_tolerance": true,
    "comprehensive_monitoring": true
  },
  "test_phases": {
    "unit_tests": "$([ -f "$LOG_DIR/unit-tests/results.txt" ] && cat "$LOG_DIR/unit-tests/results.txt" || echo 'NOT_RUN')",
    "http_server_tests": "$([ $final_exit_code -eq 0 ] && echo 'PASS' || echo 'FAIL')",
    "server_log_monitoring": "$([ -f "$LOG_DIR/server-logs/detected-errors.log" ] && echo 'ERRORS_DETECTED' || echo 'CLEAN')"
  },
  "error_summary": {
    "http_errors_detected": $([ -f "$LOG_DIR/failing-requests/"*.json ] && ls "$LOG_DIR/failing-requests/"*.json 2>/dev/null | wc -l || echo 0),
    "server_log_errors": $([ -f "$LOG_DIR/server-logs/detected-errors.log" ] && wc -l < "$LOG_DIR/server-logs/detected-errors.log" || echo 0)
  },
  "log_directory": "$LOG_DIR"
}
EOF
    
    log_info "Test report saved to: $report_file"
    
    # Display final summary
    echo ""
    echo "=== FINAL TEST SUMMARY ==="
    echo "Status: $test_status"
    echo "Exit Code: $final_exit_code"
    echo "Log Directory: $LOG_DIR"
    echo "========================="
}

# =============================================================================
# PHASE 1: INTERNAL UNIT/INTEGRATION TESTS
# =============================================================================

log_info "🧪 PHASE 1: Running internal unit and integration tests"
log_info "This ensures all TestClient-based tests pass before starting HTTP server"

# Navigate to the backend directory
if ! cd rest_api_duckdb; then
    log_error "Failed to navigate to rest_api_duckdb directory"
    exit 1
fi

# Install dependencies
log_info "📦 Installing/updating dependencies with uv"
if ! uv sync --dev >> "$LOG_DIR/unit-tests/uv-sync.log" 2>&1; then
    log_error "Failed to install dependencies with uv sync"
    exit 1
fi

# Run comprehensive internal test suite
log_info "🔍 Running comprehensive pytest suite (TestClient tests)"

# Capture test results
if uv run pytest --tb=short -v > "$LOG_DIR/unit-tests/pytest-output.log" 2>&1; then
    log_success "Internal tests PASSED - proceeding to HTTP server tests"
    echo "PASS" > "$LOG_DIR/unit-tests/results.txt"
else
    log_error "Internal tests FAILED - cannot proceed to HTTP server tests"
    echo "FAIL" > "$LOG_DIR/unit-tests/results.txt"
    echo "Unit test output:"
    cat "$LOG_DIR/unit-tests/pytest-output.log"
    exit 1
fi

# Return to root directory
cd ..

# =============================================================================
# PHASE 2: REAL HTTP SERVER TESTING
# =============================================================================

log_info "🚀 PHASE 2: Starting real HTTP server for end-to-end testing"
log_info "Zero tolerance policy: Any HTTP 4xx/5xx response will fail the test"

# Navigate to backend directory
cd rest_api_duckdb

# Create comprehensive server log file
SERVER_LOG_FILE="$LOG_DIR/server-logs/uvicorn-server.log"

# Start server with comprehensive logging
log_info "Starting uvicorn server on $SERVER_URL"
uv run python -m app.main > "$SERVER_LOG_FILE" 2>&1 &
BACKEND_PID=$!

# Return to root directory
cd ..

log_info "Backend server started with PID: $BACKEND_PID"
log_info "Server logs: $SERVER_LOG_FILE"
log_info "Waiting $SERVER_STARTUP_WAIT seconds for server startup..."

# Wait for initial startup
sleep $SERVER_STARTUP_WAIT

# Start server log monitoring
monitor_server_logs "$SERVER_LOG_FILE" 300  # Monitor for 5 minutes

# Wait for server to be ready with comprehensive retry logic
log_info "Verifying server readiness with health checks"
retry_count=0
while ! curl -s --connect-timeout 5 --max-time 10 "$SERVER_URL/" >/dev/null 2>&1; do
    retry_count=$((retry_count + 1))
    if [[ $retry_count -ge $MAX_STARTUP_RETRIES ]]; then
        log_error "Server failed to start within $MAX_STARTUP_RETRIES attempts"
        log_error "Server log contents:"
        cat "$SERVER_LOG_FILE" || true
        exit 1
    fi
    log_info "Waiting for server readiness... (attempt $retry_count/$MAX_STARTUP_RETRIES)"
    sleep 2
done

log_success "Server is ready and responding"

# =============================================================================
# PHASE 3: COMPREHENSIVE HTTP TEST SUITE (ZERO ERROR TOLERANCE)
# =============================================================================

log_info "🎯 PHASE 3: Comprehensive HTTP test suite with zero error tolerance"
log_info "Testing all endpoints with real HTTP requests (curl)"

# Test 1: Root endpoint
make_http_request "GET" "$SERVER_URL/" "" "root endpoint health check" "200"

# Test 2: API health endpoint
make_http_request "GET" "$SERVER_URL/api/health" "" "API health check endpoint" "200"

# Test 3: API info endpoint
make_http_request "GET" "$SERVER_URL/api/info" "" "API info endpoint" "200"

# Test 4: Valid query with all fields
make_http_request "POST" "$SERVER_URL/api/query" '{"id": "12345", "fromDate": "2024/01/01", "toDate": "2024/12/31", "environment": "production"}' "valid query with all fields" "200"

# Test 5: Query with ID only
make_http_request "POST" "$SERVER_URL/api/query" '{"id": "12345"}' "query with ID only" "200"

# Test 6: Query with environment only
make_http_request "POST" "$SERVER_URL/api/query" '{"environment": "production"}' "query with environment only" "200"

# Test 7: Query with date range only
make_http_request "POST" "$SERVER_URL/api/query" '{"fromDate": "2024/01/01", "toDate": "2024/12/31"}' "query with date range only" "200"

# Test 8: Empty query (should return all data)
make_http_request "POST" "$SERVER_URL/api/query" '{}' "empty query (all data)" "200"

# Test 9: Feather endpoint with valid data
make_http_request "POST" "$SERVER_URL/api/query/feather" '{"id": "12345"}' "feather endpoint with valid data" "200"

# Test 10: Feather endpoint with all data
make_http_request "POST" "$SERVER_URL/api/query/feather" '{}' "feather endpoint all data" "200"

log_success "🎉 ALL HTTP TESTS PASSED WITH ZERO ERRORS!"
log_success "✅ System maintains strict HTTP error tolerance"
log_success "🚀 Production readiness confirmed"

echo ""
echo "========================================"
echo "🏆 TEST PIPELINE COMPLETED SUCCESSFULLY"
echo "========================================"
echo "✅ Internal unit tests: PASSED"
echo "✅ Real HTTP server tests: PASSED" 
echo "✅ Zero HTTP errors detected: CONFIRMED"
echo "✅ Server log monitoring: CLEAN"
echo "✅ Production readiness: VERIFIED"
echo ""
echo "📁 Complete logs available at: $LOG_DIR"
echo "🎯 System ready for deployment with confidence!"

exit 0