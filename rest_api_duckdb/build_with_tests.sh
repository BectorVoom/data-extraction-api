#!/bin/bash

# Production Build Script with Test Gates
# This script ensures tests pass before deployment

set -e  # Exit immediately if any command fails

echo "🔧 Data Extraction API - Production Build with Test Gates"
echo "========================================================="

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Step 1: Install dependencies
echo "📦 Installing dependencies..."
uv sync --dev

# Step 2: Run linting and type checking (if tools are available)
if command -v ruff &> /dev/null; then
    echo "🔍 Running linting..."
    uv run ruff check app/
fi

# Step 3: Run all tests (BLOCKING)
echo "🧪 Running all tests (REQUIRED TO PASS)..."
uv run pytest tests/ -v --tb=short

# Step 4: Run specific validation tests for production features
echo "🔐 Running production validation tests..."
uv run pytest tests/ -k "health or info or query" -v

# Step 5: Run E2E test suite
echo "🎯 Running E2E acceptance tests..."
PYTHONPATH=$(pwd) uv run python ../test_e2e_complete.py

# Step 6: Verify feature file format works
echo "🚀 Testing new feature file format..."
uv run python -c "
import requests
import json
try:
    from app.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.post('/api/query', json={'format': 'feature'})
    assert response.status_code == 200
    data = response.json()
    assert 'features' in data
    assert 'metadata' in data
    print('✅ Feature file format validation passed')
except Exception as e:
    print(f'❌ Feature format test failed: {e}')
    exit(1)
"

echo ""
echo "✅ ALL BUILD GATES PASSED! 🎉"
echo "🚀 System is ready for production deployment"
echo "📋 Summary of validations:"
echo "   • Dependencies installed ✅"
echo "   • Unit tests passed ✅"  
echo "   • Integration tests passed ✅"
echo "   • E2E tests passed ✅"
echo "   • Feature file format validated ✅"
echo ""
echo "💡 Deploy with: uv run python -m app.main"