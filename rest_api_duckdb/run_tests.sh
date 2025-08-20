#!/bin/bash

# Data Extraction API Test Runner
# This script demonstrates uv-based testing automation

set -e

echo "🧪 Running Data Extraction API Tests with UV"
echo "============================================="

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Install/update dependencies
echo "📦 Installing dependencies with uv..."
uv sync --dev

# Run all tests
echo -e "\n🔍 Running all tests..."
uv run pytest

# Run specific test categories
echo -e "\n📋 Running optional field tests..."
uv run pytest tests/test_api.py -k "optional_fields" -v

echo -e "\n🏥 Running health and info endpoint tests..."
uv run pytest tests/test_api.py -k "health or info" -v

# Run tests with coverage if available
if command -v coverage &> /dev/null; then
    echo -e "\n📊 Running tests with coverage..."
    uv run coverage run -m pytest
    uv run coverage report --show-missing
fi

echo -e "\n✅ All tests completed successfully!"
echo -e "💡 To run tests manually: uv run pytest"
echo -e "💡 To run specific tests: uv run pytest tests/test_api.py -k 'test_name' -v"