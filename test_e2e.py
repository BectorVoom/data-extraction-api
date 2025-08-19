#!/usr/bin/env python3
"""
End-to-end acceptance tests for the Data Extraction API system.

This script tests the full system by:
1. Starting the FastAPI backend
2. Testing the API endpoints
3. Verifying all acceptance criteria
4. Testing with the frontend build (if available)

Requirements:
- Backend must be running on port 8000
- Frontend built and available (optional)
"""

import sys
import time
import requests
import subprocess
import signal
import os
from typing import Dict, Any, Optional
from datetime import datetime


class Colors:
    """Terminal colors for output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class E2ETest:
    """End-to-end test runner."""
    
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:5173"
        self.backend_process: Optional[subprocess.Popen] = None
        self.tests_passed = 0
        self.tests_failed = 0
    
    def log(self, message: str, color: str = Colors.BLUE):
        """Log a message with color."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{color}[{timestamp}] {message}{Colors.END}")
    
    def success(self, message: str):
        """Log a success message."""
        self.log(f"✅ {message}", Colors.GREEN)
        self.tests_passed += 1
    
    def error(self, message: str):
        """Log an error message."""
        self.log(f"❌ {message}", Colors.RED)
        self.tests_failed += 1
    
    def warning(self, message: str):
        """Log a warning message."""
        self.log(f"⚠️  {message}", Colors.YELLOW)
    
    def start_backend(self) -> bool:
        """Start the FastAPI backend server."""
        try:
            self.log("Starting FastAPI backend server...")
            
            # Change to backend directory
            backend_dir = "rest_api_duckdb"
            if not os.path.exists(backend_dir):
                self.error(f"Backend directory '{backend_dir}' not found")
                return False
            
            # Start the server
            self.backend_process = subprocess.Popen(
                ["uv", "run", "python", "-m", "app.main"],
                cwd=backend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for server to start
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    response = requests.get(f"{self.backend_url}/", timeout=1)
                    if response.status_code == 200:
                        self.success("Backend server started successfully")
                        return True
                except requests.exceptions.RequestException:
                    time.sleep(1)
                    if attempt % 5 == 0:
                        self.log(f"Waiting for backend server... (attempt {attempt + 1}/{max_attempts})")
            
            self.error("Backend server failed to start within timeout period")
            return False
            
        except Exception as e:
            self.error(f"Failed to start backend server: {e}")
            return False
    
    def stop_backend(self):
        """Stop the FastAPI backend server."""
        if self.backend_process:
            self.log("Stopping backend server...")
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
                self.backend_process.wait()
            self.backend_process = None
            self.success("Backend server stopped")
    
    def test_api_endpoints(self):
        """Test all API endpoints."""
        self.log("Testing API endpoints...")
        
        # Test 1: Root endpoint
        try:
            response = requests.get(f"{self.backend_url}/")
            if response.status_code == 200:
                data = response.json()
                if data.get("message") == "Data Extraction API":
                    self.success("Root endpoint working")
                else:
                    self.error("Root endpoint returned unexpected data")
            else:
                self.error(f"Root endpoint returned status {response.status_code}")
        except Exception as e:
            self.error(f"Root endpoint test failed: {e}")
        
        # Test 2: Health check
        try:
            response = requests.get(f"{self.backend_url}/api/health")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.success("Health check endpoint working")
                else:
                    self.error("Health check returned unhealthy status")
            else:
                self.error(f"Health check returned status {response.status_code}")
        except Exception as e:
            self.error(f"Health check test failed: {e}")
        
        # Test 3: Database info
        try:
            response = requests.get(f"{self.backend_url}/api/info")
            if response.status_code == 200:
                data = response.json()
                if "database_info" in data and "api_info" in data:
                    self.success("Database info endpoint working")
                else:
                    self.error("Database info endpoint returned incomplete data")
            else:
                self.error(f"Database info returned status {response.status_code}")
        except Exception as e:
            self.error(f"Database info test failed: {e}")
    
    def test_query_functionality(self):
        """Test the main query functionality."""
        self.log("Testing query functionality...")
        
        # Test 4: Valid query
        try:
            payload = {
                "id": "12345",
                "fromDate": "2024/01/01",
                "toDate": "2024/12/31"
            }
            response = requests.post(f"{self.backend_url}/api/query", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "count" in data:
                    self.success(f"Valid query returned {data['count']} results")
                else:
                    self.error("Valid query returned malformed response")
            else:
                self.error(f"Valid query returned status {response.status_code}")
        except Exception as e:
            self.error(f"Valid query test failed: {e}")
        
        # Test 5: Query with no results
        try:
            payload = {
                "id": "nonexistent",
                "fromDate": "2024/01/01",
                "toDate": "2024/12/31"
            }
            response = requests.post(f"{self.backend_url}/api/query", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("count") == 0:
                    self.success("No results query handled correctly")
                else:
                    self.error("No results query returned unexpected data")
            else:
                self.error(f"No results query returned status {response.status_code}")
        except Exception as e:
            self.error(f"No results query test failed: {e}")
    
    def test_validation(self):
        """Test input validation."""
        self.log("Testing input validation...")
        
        # Test 6: Invalid date format
        try:
            payload = {
                "id": "12345",
                "fromDate": "2024-01-01",  # Wrong format
                "toDate": "2024/12/31"
            }
            response = requests.post(f"{self.backend_url}/api/query", json=payload)
            
            if response.status_code == 422:
                self.success("Invalid date format rejected correctly")
            else:
                self.error(f"Invalid date format returned status {response.status_code} (expected 422)")
        except Exception as e:
            self.error(f"Invalid date format test failed: {e}")
        
        # Test 7: Invalid date range
        try:
            payload = {
                "id": "12345",
                "fromDate": "2024/12/31",
                "toDate": "2024/01/01"  # fromDate after toDate
            }
            response = requests.post(f"{self.backend_url}/api/query", json=payload)
            
            if response.status_code == 422:
                self.success("Invalid date range rejected correctly")
            else:
                self.error(f"Invalid date range returned status {response.status_code} (expected 422)")
        except Exception as e:
            self.error(f"Invalid date range test failed: {e}")
        
        # Test 8: Missing fields
        try:
            payload = {
                "id": "12345"
                # Missing fromDate and toDate
            }
            response = requests.post(f"{self.backend_url}/api/query", json=payload)
            
            if response.status_code == 422:
                self.success("Missing fields rejected correctly")
            else:
                self.error(f"Missing fields returned status {response.status_code} (expected 422)")
        except Exception as e:
            self.error(f"Missing fields test failed: {e}")
    
    def test_cors(self):
        """Test CORS configuration."""
        self.log("Testing CORS configuration...")
        
        try:
            # Preflight request
            headers = {
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
            response = requests.options(f"{self.backend_url}/api/query", headers=headers)
            
            if response.status_code == 200:
                self.success("CORS preflight request handled correctly")
            else:
                self.error(f"CORS preflight returned status {response.status_code}")
        except Exception as e:
            self.error(f"CORS test failed: {e}")
    
    def check_frontend_build(self):
        """Check if frontend can be built."""
        self.log("Checking frontend build...")
        
        frontend_dir = "frontend_svelte_tailwindcss"
        if not os.path.exists(frontend_dir):
            self.warning("Frontend directory not found, skipping build test")
            return
        
        try:
            # Try to build the frontend
            result = subprocess.run(
                ["bun", "run", "build"],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                self.success("Frontend builds successfully")
            else:
                self.error(f"Frontend build failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            self.error("Frontend build timed out")
        except Exception as e:
            self.error(f"Frontend build test failed: {e}")
    
    def run_acceptance_criteria(self):
        """Run all acceptance criteria tests."""
        self.log(f"{Colors.BOLD}Running acceptance criteria tests...{Colors.END}")
        
        # Acceptance criterion 1: Valid POST returns 200 with array
        self.test_api_endpoints()
        self.test_query_functionality()
        
        # Acceptance criterion 2: Malformed dates return 400/422 with error
        self.test_validation()
        
        # Acceptance criterion 3: CORS is configured
        self.test_cors()
        
        # Additional checks
        self.check_frontend_build()
    
    def run(self):
        """Run all end-to-end tests."""
        self.log(f"{Colors.BOLD}Starting End-to-End Acceptance Tests{Colors.END}")
        
        try:
            # Start backend
            if not self.start_backend():
                return False
            
            # Run all tests
            self.run_acceptance_criteria()
            
            # Summary
            total_tests = self.tests_passed + self.tests_failed
            self.log(f"{Colors.BOLD}Test Summary:{Colors.END}")
            self.log(f"  Total tests: {total_tests}")
            self.log(f"  Passed: {self.tests_passed}", Colors.GREEN)
            self.log(f"  Failed: {self.tests_failed}", Colors.RED)
            
            if self.tests_failed == 0:
                self.log(f"{Colors.BOLD}{Colors.GREEN}🎉 All acceptance tests passed!{Colors.END}")
                return True
            else:
                self.log(f"{Colors.BOLD}{Colors.RED}❌ {self.tests_failed} tests failed{Colors.END}")
                return False
            
        except KeyboardInterrupt:
            self.warning("Tests interrupted by user")
            return False
        except Exception as e:
            self.error(f"Unexpected error during testing: {e}")
            return False
        finally:
            # Always cleanup
            self.stop_backend()


def main():
    """Main entry point."""
    test_runner = E2ETest()
    success = test_runner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()