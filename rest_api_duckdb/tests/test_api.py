import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.database import get_database_service, close_database_service


class TestAPIEndpoints:
    """Test FastAPI endpoints with TestClient."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        # Setup: ensure fresh database state
        close_database_service()
        yield
        # Teardown: close database connections
        close_database_service()

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert data["message"] == "Data Extraction API"
        assert "version" in data

    def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data
        assert data["database"]["connected"] is True
        assert "row_count" in data["database"]

    def test_info_endpoint(self, client):
        """Test the database info endpoint."""
        response = client.get("/api/info")
        assert response.status_code == 200
        
        data = response.json()
        assert "database_info" in data
        assert "api_info" in data
        
        # Check database info structure
        db_info = data["database_info"]
        assert "schema" in db_info
        assert "row_count" in db_info
        assert "unique_ids" in db_info
        
        # Check API info
        api_info = data["api_info"]
        assert api_info["endpoint"] == "/api/query"
        assert api_info["method"] == "POST"

    def test_query_endpoint_success(self, client):
        """Test successful query endpoint."""
        payload = {
            "id": "12345",
            "fromDate": "2024/01/01",
            "toDate": "2024/12/31"
        }
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "count" in data
        assert "query_info" in data
        
        assert isinstance(data["data"], list)
        assert isinstance(data["count"], int)
        assert data["count"] == len(data["data"])

    def test_query_endpoint_no_results(self, client):
        """Test query endpoint with no results."""
        payload = {
            "id": "nonexistent",
            "fromDate": "2024/01/01",
            "toDate": "2024/12/31"
        }
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["data"] == []
        assert data["count"] == 0

    def test_query_endpoint_numeric_id(self, client):
        """Test query endpoint with numeric ID."""
        payload = {
            "id": 12345,
            "fromDate": "2024/01/01",
            "toDate": "2024/12/31"
        }
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data

    def test_query_endpoint_invalid_date_format(self, client):
        """Test query endpoint with invalid date format."""
        payload = {
            "id": "12345",
            "fromDate": "2024-01-01",  # Wrong format
            "toDate": "2024/12/31"
        }
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 422  # Validation error

    def test_query_endpoint_invalid_date_range(self, client):
        """Test query endpoint with invalid date range."""
        payload = {
            "id": "12345",
            "fromDate": "2024/12/31",
            "toDate": "2024/01/01"  # fromDate after toDate
        }
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 422  # Validation error

    def test_query_endpoint_missing_fields(self, client):
        """Test query endpoint with missing required fields."""
        payload = {
            "id": "12345"
            # Missing fromDate and toDate
        }
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 422  # Validation error

    def test_query_endpoint_empty_fields(self, client):
        """Test query endpoint with empty fields."""
        payload = {
            "id": "",
            "fromDate": "",
            "toDate": ""
        }
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 422  # Validation error

    def test_query_endpoint_invalid_json(self, client):
        """Test query endpoint with invalid JSON."""
        response = client.post(
            "/api/query",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_query_endpoint_wrong_content_type(self, client):
        """Test query endpoint with wrong content type."""
        response = client.post(
            "/api/query",
            data="id=12345&fromDate=2024/01/01&toDate=2024/12/31",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 422

    def test_query_endpoint_response_structure(self, client):
        """Test that query endpoint response has correct structure."""
        payload = {
            "id": "12345",
            "fromDate": "2024/01/01",
            "toDate": "2024/12/31"
        }
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check top-level structure
        required_fields = ["data", "count", "query_info"]
        for field in required_fields:
            assert field in data
        
        # Check query_info structure
        query_info = data["query_info"]
        assert "id" in query_info
        assert "fromDate" in query_info
        assert "toDate" in query_info
        assert "date_range_parsed" in query_info
        
        # Check data structure (if any results)
        if data["data"]:
            record = data["data"][0]
            required_record_fields = ["id", "event_date", "event_type", "description", "value", "created_at"]
            for field in required_record_fields:
                assert field in record

    def test_cors_headers(self, client):
        """Test that CORS headers are present."""
        # Preflight request
        response = client.options(
            "/api/query",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        # Should allow CORS
        assert response.status_code == 200

    def test_query_endpoint_edge_cases(self, client):
        """Test query endpoint with edge case dates."""
        # Same date for from and to
        payload = {
            "id": "12345",
            "fromDate": "2024/01/15",
            "toDate": "2024/01/15"
        }
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 200

    def test_query_endpoint_leap_year(self, client):
        """Test query endpoint with leap year date."""
        payload = {
            "id": "12345",
            "fromDate": "2024/02/29",  # 2024 is a leap year
            "toDate": "2024/03/01"
        }
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 200

    def test_query_endpoint_invalid_leap_year(self, client):
        """Test query endpoint with invalid leap year date."""
        payload = {
            "id": "12345",
            "fromDate": "2023/02/29",  # 2023 is not a leap year
            "toDate": "2023/03/01"
        }
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 422  # Validation error

    def test_multiple_requests_same_client(self, client):
        """Test multiple requests with the same client."""
        payload1 = {
            "id": "12345",
            "fromDate": "2024/01/01",
            "toDate": "2024/06/30"
        }
        
        payload2 = {
            "id": "67890",
            "fromDate": "2024/07/01",
            "toDate": "2024/12/31"
        }
        
        # First request
        response1 = client.post("/api/query", json=payload1)
        assert response1.status_code == 200
        
        # Second request
        response2 = client.post("/api/query", json=payload2)
        assert response2.status_code == 200
        
        # Results should be independent
        data1 = response1.json()
        data2 = response2.json()
        
        assert data1["query_info"]["id"] == "12345"
        assert data2["query_info"]["id"] == "67890"