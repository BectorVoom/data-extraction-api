#!/bin/bash

# Simple acceptance test
echo "🚀 Simple Acceptance Test"
echo "=================================="

# Start backend in background
echo "Starting backend..."
cd rest_api_duckdb
uv run python -m app.main &
BACKEND_PID=$!
cd ..

echo "Waiting for server..."
sleep 5

# Test endpoints
echo "Testing root endpoint..."
curl -s http://localhost:8000/ | head -1

echo "Testing health endpoint..."
curl -s http://localhost:8000/api/health | head -1

echo "Testing valid query..."
curl -s -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"id": "12345", "fromDate": "2024/01/01", "toDate": "2024/12/31"}' | head -1

echo "Testing invalid date format (should get 422)..."
curl -s -w "HTTP %{http_code}\n" -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"id": "12345", "fromDate": "2024-01-01", "toDate": "2024/12/31"}' > /dev/null

# Cleanup
echo "Cleaning up..."
kill $BACKEND_PID
wait $BACKEND_PID 2>/dev/null

echo "✅ Simple test completed"