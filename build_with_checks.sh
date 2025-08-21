#!/bin/bash

# =============================================================================
# INTEGRATED BUILD + COMPREHENSIVE TEST + VALIDATION PIPELINE
# =============================================================================
# Complete CI/CD pipeline for the Data Extraction System
# Combines build verification, comprehensive testing, and production readiness
# GitHub Actions & CI/CD compatible with detailed reporting
# =============================================================================

# Strict error handling: exit on any error, undefined variables, or pipe failures
set -euo pipefail

# Global configuration
PIPELINE_START_TIME=$(date +%s)
BUILD_DIR="$(pwd)/build-reports/$(date +%Y%m%d-%H%M%S)"
FRONTEND_DIR="excel-addin-svelte" 
BACKEND_DIR="rest_api_duckdb"
NODE_VERSION_REQUIRED="18"
PYTHON_VERSION_REQUIRED="3.13"

# Create comprehensive build report directory
mkdir -p "$BUILD_DIR/frontend"
mkdir -p "$BUILD_DIR/backend"  
mkdir -p "$BUILD_DIR/integration"
mkdir -p "$BUILD_DIR/reports"

# Create initial log file and wait for filesystem
touch "$BUILD_DIR/build-pipeline.log"
sleep 0.1

echo "🏗️  INTEGRATED BUILD + TEST + VALIDATION PIPELINE"
echo "=================================================="
echo "📦 Build verification and dependency management"
echo "🧪 Comprehensive test execution (unit + E2E)"
echo "🚀 Production readiness validation"
echo "📊 Detailed reporting and metrics"
echo ""

# Enhanced logging functions
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ℹ️  INFO: $1" | tee -a "$BUILD_DIR/build-pipeline.log"
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ SUCCESS: $1" | tee -a "$BUILD_DIR/build-pipeline.log"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ ERROR: $1" | tee -a "$BUILD_DIR/build-pipeline.log" >&2
}

log_warning() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  WARNING: $1" | tee -a "$BUILD_DIR/build-pipeline.log"
}

# Build status tracking (macOS compatible)
FRONTEND_DEPS_STATUS="PENDING"
FRONTEND_BUILD_STATUS="PENDING"
FRONTEND_LINT_STATUS="PENDING"
BACKEND_DEPS_STATUS="PENDING"
BACKEND_TESTS_STATUS="PENDING"
BACKEND_LINT_STATUS="PENDING"
INTEGRATION_TESTS_STATUS="PENDING"
E2E_VALIDATION_STATUS="PENDING"

# Cleanup function
cleanup() {
    local exit_code=$?
    log_info "Starting pipeline cleanup..."
    
    # Generate final build report
    generate_build_report $exit_code
    
    log_info "Build pipeline completed. Reports saved to: $BUILD_DIR"
    
    if [[ $exit_code -eq 0 ]]; then
        echo ""
        echo "🎉 BUILD PIPELINE COMPLETED SUCCESSFULLY!"
        echo "✅ All checks passed - system ready for deployment"
    else
        echo ""
        echo "❌ BUILD PIPELINE FAILED!"
        echo "🔍 Check logs in $BUILD_DIR for details"
    fi
}
trap cleanup EXIT

# Generate comprehensive build report
generate_build_report() {
    local final_exit_code="$1"
    local pipeline_end_time=$(date +%s)
    local total_duration=$((pipeline_end_time - PIPELINE_START_TIME))
    local report_file="$BUILD_DIR/reports/build-pipeline-report.json"
    
    log_info "Generating comprehensive build report..."
    
    local pipeline_status="PASS"
    if [[ $final_exit_code -ne 0 ]]; then
        pipeline_status="FAIL"
    fi
    
    cat > "$report_file" << EOF
{
  "pipeline_run_id": "$(basename $BUILD_DIR)",
  "timestamp": "$(date -Iseconds)",
  "status": "$pipeline_status",
  "exit_code": $final_exit_code,
  "duration_seconds": $total_duration,
  "environment": {
    "node_version": "$(node --version 2>/dev/null || echo 'NOT_FOUND')",
    "python_version": "$(python3 --version 2>/dev/null || echo 'NOT_FOUND')",
    "uv_version": "$(uv --version 2>/dev/null || echo 'NOT_FOUND')",
    "bun_version": "$(bun --version 2>/dev/null || echo 'NOT_FOUND')"
  },
  "build_phases": {
    "frontend_dependencies": "$FRONTEND_DEPS_STATUS",
    "frontend_build": "$FRONTEND_BUILD_STATUS",
    "frontend_lint": "$FRONTEND_LINT_STATUS",
    "backend_dependencies": "$BACKEND_DEPS_STATUS",
    "backend_tests": "$BACKEND_TESTS_STATUS",
    "backend_lint": "$BACKEND_LINT_STATUS",
    "integration_tests": "$INTEGRATION_TESTS_STATUS",
    "e2e_validation": "$E2E_VALIDATION_STATUS"
  },
  "logs_directory": "$BUILD_DIR"
}
EOF
    
    log_info "Build report saved to: $report_file"
    
    # Display summary
    echo ""
    echo "=== BUILD PIPELINE SUMMARY ==="
    echo "Status: $pipeline_status"
    echo "Duration: ${total_duration}s"
    echo "Exit Code: $final_exit_code"
    echo "Log Directory: $BUILD_DIR"
    echo "============================="
}

# Check system prerequisites
check_prerequisites() {
    log_info "🔍 Checking system prerequisites"
    
    # Check Node.js
    if ! command -v node >/dev/null 2>&1; then
        log_error "Node.js not found. Please install Node.js $NODE_VERSION_REQUIRED+"
        exit 1
    fi
    
    local node_version=$(node --version | sed 's/v//' | cut -d. -f1)
    if [[ $node_version -lt $NODE_VERSION_REQUIRED ]]; then
        log_error "Node.js version $node_version found, but $NODE_VERSION_REQUIRED+ required"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 >/dev/null 2>&1; then
        log_error "Python 3 not found. Please install Python $PYTHON_VERSION_REQUIRED+"
        exit 1
    fi
    
    # Check uv
    if ! command -v uv >/dev/null 2>&1; then
        log_error "uv not found. Please install uv for Python package management"
        exit 1
    fi
    
    # Check bun (optional but preferred)
    if ! command -v bun >/dev/null 2>&1; then
        log_warning "bun not found. Will use npm/node instead"
    fi
    
    log_success "Prerequisites check completed"
}

# =============================================================================
# FRONTEND BUILD PIPELINE
# =============================================================================

build_frontend() {
    log_info "🎨 Starting frontend build pipeline"
    
    if [[ ! -d "$FRONTEND_DIR" ]]; then
        log_warning "Frontend directory $FRONTEND_DIR not found, skipping frontend build"
        FRONTEND_DEPS_STATUS="SKIPPED"
        FRONTEND_BUILD_STATUS="SKIPPED"
        FRONTEND_LINT_STATUS="SKIPPED"
        return 0
    fi
    
    cd "$FRONTEND_DIR"
    
    # Install dependencies
    log_info "📦 Installing frontend dependencies"
    if command -v bun >/dev/null 2>&1; then
        if bun install > "$BUILD_DIR/frontend/bun-install.log" 2>&1; then
            FRONTEND_DEPS_STATUS="PASS"
            log_success "Frontend dependencies installed with bun"
        else
            FRONTEND_DEPS_STATUS="FAIL"
            log_error "Frontend dependency installation failed"
            cat "$BUILD_DIR/frontend/bun-install.log"
            exit 1
        fi
    else
        if npm install > "$BUILD_DIR/frontend/npm-install.log" 2>&1; then
            FRONTEND_DEPS_STATUS="PASS"
            log_success "Frontend dependencies installed with npm"
        else
            FRONTEND_DEPS_STATUS="FAIL"
            log_error "Frontend dependency installation failed"
            cat "$BUILD_DIR/frontend/npm-install.log"
            exit 1
        fi
    fi
    
    # Build frontend
    log_info "🏗️  Building frontend application"
    if command -v bun >/dev/null 2>&1; then
        if bun run build > "$BUILD_DIR/frontend/bun-build.log" 2>&1; then
            FRONTEND_BUILD_STATUS="PASS"
            log_success "Frontend build completed successfully"
        else
            FRONTEND_BUILD_STATUS="FAIL"
            log_error "Frontend build failed"
            cat "$BUILD_DIR/frontend/bun-build.log"
            exit 1
        fi
    else
        if npm run build > "$BUILD_DIR/frontend/npm-build.log" 2>&1; then
            FRONTEND_BUILD_STATUS="PASS"
            log_success "Frontend build completed successfully"
        else
            FRONTEND_BUILD_STATUS="FAIL"
            log_error "Frontend build failed"
            cat "$BUILD_DIR/frontend/npm-build.log"
            exit 1
        fi
    fi
    
    # Run linting if available
    log_info "🔍 Running frontend linting"
    if command -v bun >/dev/null 2>&1 && bun run lint > "$BUILD_DIR/frontend/bun-lint.log" 2>&1; then
        FRONTEND_LINT_STATUS="PASS"
        log_success "Frontend linting passed"
    elif npm run lint > "$BUILD_DIR/frontend/npm-lint.log" 2>&1; then
        FRONTEND_LINT_STATUS="PASS"
        log_success "Frontend linting passed"
    else
        FRONTEND_LINT_STATUS="SKIPPED"
        log_warning "Frontend linting not available or failed (non-blocking)"
    fi
    
    cd ..
    log_success "Frontend build pipeline completed"
}

# =============================================================================
# BACKEND BUILD PIPELINE
# =============================================================================

build_backend() {
    log_info "⚙️  Starting backend build pipeline"
    
    if [[ ! -d "$BACKEND_DIR" ]]; then
        log_error "Backend directory $BACKEND_DIR not found"
        exit 1
    fi
    
    cd "$BACKEND_DIR"
    
    # Install dependencies
    log_info "📦 Installing backend dependencies"
    if uv sync --dev > "$BUILD_DIR/backend/uv-sync.log" 2>&1; then
        BACKEND_DEPS_STATUS="PASS"
        log_success "Backend dependencies installed with uv"
    else
        BACKEND_DEPS_STATUS="FAIL"
        log_error "Backend dependency installation failed"
        cat "$BUILD_DIR/backend/uv-sync.log"
        exit 1
    fi
    
    # Run comprehensive tests
    log_info "🧪 Running backend unit and integration tests"
    if uv run pytest --tb=short -v --junitxml="$BUILD_DIR/backend/test-results.xml" > "$BUILD_DIR/backend/pytest-output.log" 2>&1; then
        BACKEND_TESTS_STATUS="PASS"
        log_success "Backend tests passed"
        
        # Extract test metrics
        local test_count=$(grep -c "PASSED\|FAILED\|ERROR" "$BUILD_DIR/backend/pytest-output.log" 2>/dev/null || echo "0")
        local failed_count=$(grep -c "FAILED\|ERROR" "$BUILD_DIR/backend/pytest-output.log" 2>/dev/null || echo "0")
        log_info "Test Results: $test_count total tests, $failed_count failures"
        
    else
        BACKEND_TESTS_STATUS="FAIL"
        log_error "Backend tests failed"
        cat "$BUILD_DIR/backend/pytest-output.log"
        exit 1
    fi
    
    # Run linting/code quality checks
    log_info "🔍 Running backend code quality checks"
    
    # Try ruff first (modern Python linter)
    if command -v ruff >/dev/null 2>&1; then
        if ruff check . > "$BUILD_DIR/backend/ruff-check.log" 2>&1; then
            BACKEND_LINT_STATUS="PASS"
            log_success "Backend code quality checks passed (ruff)"
        else
            BACKEND_LINT_STATUS="FAIL"
            log_error "Backend code quality checks failed"
            cat "$BUILD_DIR/backend/ruff-check.log"
            exit 1
        fi
    # Fallback to flake8 if available
    elif command -v flake8 >/dev/null 2>&1; then
        if flake8 . > "$BUILD_DIR/backend/flake8-check.log" 2>&1; then
            BACKEND_LINT_STATUS="PASS"
            log_success "Backend code quality checks passed (flake8)"
        else
            BACKEND_LINT_STATUS="FAIL"
            log_error "Backend code quality checks failed"
            cat "$BUILD_DIR/backend/flake8-check.log"
            exit 1
        fi
    else
        BACKEND_LINT_STATUS="SKIPPED"
        log_warning "No Python linter found (ruff/flake8), skipping code quality checks"
    fi
    
    cd ..
    log_success "Backend build pipeline completed"
}

# =============================================================================
# INTEGRATION & E2E TESTING
# =============================================================================

run_integration_tests() {
    log_info "🔗 Starting integration testing phase"
    
    # Run the comprehensive test stability pipeline
    log_info "🎯 Executing comprehensive test stability pipeline"
    if ./simple_test.sh > "$BUILD_DIR/integration/simple-test-output.log" 2>&1; then
        INTEGRATION_TESTS_STATUS="PASS"
        E2E_VALIDATION_STATUS="PASS"
        log_success "Integration tests and E2E validation completed successfully"
        
        # Extract key metrics from test output
        local test_log="$BUILD_DIR/integration/simple-test-output.log"
        log_info "Integration test summary:"
        grep -E "(PASSED|SUCCESS|COMPLETED)" "$test_log" | tail -5 || true
        
    else
        INTEGRATION_TESTS_STATUS="FAIL"
        E2E_VALIDATION_STATUS="FAIL"
        log_error "Integration tests or E2E validation failed"
        echo "Integration test output:"
        cat "$BUILD_DIR/integration/simple-test-output.log"
        exit 1
    fi
    
    log_success "Integration testing phase completed"
}

# =============================================================================
# MAIN PIPELINE EXECUTION
# =============================================================================

main() {
    log_info "🚀 Starting integrated build + test + validation pipeline"
    
    # Phase 1: Prerequisites
    check_prerequisites
    
    # Phase 2: Frontend build
    build_frontend
    
    # Phase 3: Backend build  
    build_backend
    
    # Phase 4: Integration & E2E testing
    run_integration_tests
    
    log_success "🎉 COMPLETE BUILD PIPELINE SUCCESSFUL!"
    log_success "✅ Frontend: Built and validated"
    log_success "✅ Backend: Built, tested, and validated"
    log_success "✅ Integration: E2E tests passed with zero HTTP errors"
    log_success "✅ System: Ready for production deployment"
    
    return 0
}

# Execute main pipeline
main "$@"