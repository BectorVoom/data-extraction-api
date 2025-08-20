import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.database import get_database_service, close_database_service
import pyarrow.feather as feather
from io import BytesIO


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
        assert "feather_endpoint" in data
        assert data["feather_endpoint"] == "/api/query/feather"

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
        
        # Check API info structure
        api_info = data["api_info"]
        assert "json_endpoint" in api_info
        assert "feather_endpoint" in api_info
        
        # Check JSON endpoint info
        json_endpoint = api_info["json_endpoint"]
        assert json_endpoint["endpoint"] == "/api/query"
        assert json_endpoint["method"] == "POST"
        assert json_endpoint["response_format"] == "JSON"
        
        # Check Feather endpoint info
        feather_endpoint = api_info["feather_endpoint"]
        assert feather_endpoint["endpoint"] == "/api/query/feather"
        assert feather_endpoint["method"] == "POST"
        assert feather_endpoint["response_format"] == "Apache Arrow Feather (binary)"
        assert feather_endpoint["media_type"] == "application/octet-stream"

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
        """Test query endpoint with partial fields (now all fields are optional)."""
        payload = {
            "id": "12345"
            # Missing fromDate and toDate - this should now work fine
        }
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 200  # Should succeed with optional fields
        
        data = response.json()
        assert data["query_info"]["id"] == "12345"
        assert data["query_info"]["fromDate"] is None
        assert data["query_info"]["toDate"] is None

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

    def test_query_endpoint_optional_fields_all_data(self, client):
        """Test query endpoint with no filters (all data)."""
        payload = {}
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "count" in data
        assert isinstance(data["data"], list)
        assert data["count"] == len(data["data"])
        # Should return all records since no filters applied
        assert data["count"] > 0

    def test_query_endpoint_optional_fields_id_only(self, client):
        """Test query endpoint with only ID filter."""
        payload = {"id": "12345"}
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["query_info"]["id"] == "12345"
        assert data["query_info"]["fromDate"] is None
        assert data["query_info"]["toDate"] is None
        assert data["query_info"]["environment"] is None

    def test_query_endpoint_optional_fields_environment_only(self, client):
        """Test query endpoint with only environment filter."""
        payload = {"environment": "production"}
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["query_info"]["id"] is None
        assert data["query_info"]["environment"] == "production"
        # Should return only production records
        for record in data["data"]:
            assert record["environment"] == "production"

    def test_query_endpoint_optional_fields_date_range_only(self, client):
        """Test query endpoint with only date range."""
        payload = {
            "fromDate": "2024/01/01",
            "toDate": "2024/12/31"
        }
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["query_info"]["id"] is None
        assert data["query_info"]["fromDate"] == "2024/01/01"
        assert data["query_info"]["toDate"] == "2024/12/31"
        assert data["query_info"]["environment"] is None

    def test_query_endpoint_optional_fields_from_date_only(self, client):
        """Test query endpoint with only from date (unbounded to)."""
        payload = {"fromDate": "2024/06/01"}
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["query_info"]["fromDate"] == "2024/06/01"
        assert data["query_info"]["toDate"] is None

    def test_query_endpoint_optional_fields_to_date_only(self, client):
        """Test query endpoint with only to date (unbounded from)."""
        payload = {"toDate": "2024/06/01"}
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["query_info"]["fromDate"] is None
        assert data["query_info"]["toDate"] == "2024/06/01"

    def test_query_endpoint_optional_fields_null_values(self, client):
        """Test query endpoint with explicit null values."""
        payload = {
            "id": None,
            "fromDate": None,
            "toDate": None,
            "environment": None
        }
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["query_info"]["id"] is None
        assert data["query_info"]["fromDate"] is None
        assert data["query_info"]["toDate"] is None
        assert data["query_info"]["environment"] is None

    def test_query_endpoint_optional_fields_mixed_filters(self, client):
        """Test query endpoint with mixed optional filters."""
        payload = {
            "id": "12345",
            "environment": "production"
            # No date filters
        }
        
        response = client.post("/api/query", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["query_info"]["id"] == "12345"
        assert data["query_info"]["environment"] == "production"
        assert data["query_info"]["fromDate"] is None
        assert data["query_info"]["toDate"] is None
        
        # All returned records should match both filters
        for record in data["data"]:
            assert record["id"] == "12345"
            assert record["environment"] == "production"


class TestFeatherAPIEndpoints:
    """Test Feather-specific API endpoints."""

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

    def test_feather_endpoint_success(self, client):
        """Test successful Feather query endpoint."""
        payload = {
            "id": "12345",
            "fromDate": "2024/01/01",
            "toDate": "2024/12/31"
        }
        
        response = client.post("/api/query/feather", json=payload)
        assert response.status_code == 200
        
        # Check headers
        assert response.headers["content-type"] == "application/octet-stream"
        assert "attachment" in response.headers["content-disposition"]
        assert ".feather" in response.headers["content-disposition"]
        
        # Verify Feather content
        feather_table = feather.read_table(BytesIO(response.content))
        assert len(feather_table) > 0
        
        # Check schema
        column_names = feather_table.schema.names
        expected_columns = ['id', 'event_date', 'event_type', 'description', 'value', 'environment', 'created_at']
        for col in expected_columns:
            assert col in column_names

    def test_feather_endpoint_no_results(self, client):
        """Test Feather endpoint with no results."""
        payload = {
            "id": "nonexistent",
            "fromDate": "2024/01/01",
            "toDate": "2024/12/31"
        }
        
        response = client.post("/api/query/feather", json=payload)
        assert response.status_code == 200
        
        # Even with no results, should return valid Feather file
        feather_table = feather.read_table(BytesIO(response.content))
        assert len(feather_table) == 0

    def test_feather_endpoint_all_data(self, client):
        """Test Feather endpoint with no filters (all data)."""
        payload = {}
        
        response = client.post("/api/query/feather", json=payload)
        assert response.status_code == 200
        
        feather_table = feather.read_table(BytesIO(response.content))
        assert len(feather_table) > 0

    def test_feather_endpoint_filename_generation(self, client):
        """Test that Feather endpoint generates appropriate filenames."""
        test_cases = [
            ({"id": "12345"}, "id_12345"),
            ({"environment": "production"}, "env_production"),
            ({"fromDate": "2024/01/01", "toDate": "2024/12/31"}, "from_2024_01_01_to_2024_12_31"),
            ({"id": "12345", "environment": "production"}, "id_12345_env_production"),
            ({}, "data")  # Default filename for no filters
        ]
        
        for payload, expected_filename_part in test_cases:
            response = client.post("/api/query/feather", json=payload)
            assert response.status_code == 200
            
            content_disposition = response.headers["content-disposition"]
            assert expected_filename_part in content_disposition
            assert ".feather" in content_disposition

    def test_feather_endpoint_data_integrity(self, client):
        """Test that Feather data matches JSON data."""
        payload = {"id": "12345"}
        
        # Get JSON response
        json_response = client.post("/api/query", json=payload)
        json_data = json_response.json()["data"]
        
        # Get Feather response
        feather_response = client.post("/api/query/feather", json=payload)
        feather_table = feather.read_table(BytesIO(feather_response.content))
        
        # Convert Feather to dict format
        feather_data = []
        for i in range(len(feather_table)):
            row = {}
            for field_idx, field in enumerate(feather_table.schema):
                column = feather_table.column(field_idx)
                value = column[i].as_py()
                
                # Handle date conversion for comparison
                if field.name == 'event_date' and value:
                    value = str(value)
                elif field.name == 'created_at' and value:
                    value = value.isoformat()
                
                row[field.name] = value
            feather_data.append(row)
        
        # Compare row counts
        assert len(json_data) == len(feather_data)
        
        # Compare IDs (should all be 12345)
        for json_row, feather_row in zip(json_data, feather_data):
            assert json_row["id"] == feather_row["id"]

    def test_feather_endpoint_invalid_date_format(self, client):
        """Test Feather endpoint with invalid date format."""
        payload = {
            "id": "12345",
            "fromDate": "2024-01-01",  # Wrong format
            "toDate": "2024/12/31"
        }
        
        response = client.post("/api/query/feather", json=payload)
        assert response.status_code == 422  # Validation error

    def test_feather_endpoint_invalid_date_range(self, client):
        """Test Feather endpoint with invalid date range."""
        payload = {
            "id": "12345",
            "fromDate": "2024/12/31",
            "toDate": "2024/01/01"  # fromDate after toDate
        }
        
        response = client.post("/api/query/feather", json=payload)
        assert response.status_code == 422  # Validation error

    def test_feather_endpoint_environment_filter(self, client):
        """Test Feather endpoint with environment filter."""
        payload = {"environment": "production"}
        
        response = client.post("/api/query/feather", json=payload)
        assert response.status_code == 200
        
        feather_table = feather.read_table(BytesIO(response.content))
        
        # Check that all rows have production environment
        env_column = feather_table.column('environment')
        for i in range(len(feather_table)):
            assert env_column[i].as_py() == "production"

    def test_feather_endpoint_mixed_filters(self, client):
        """Test Feather endpoint with mixed filters."""
        payload = {
            "id": "12345",
            "environment": "production"
        }
        
        response = client.post("/api/query/feather", json=payload)
        assert response.status_code == 200
        
        feather_table = feather.read_table(BytesIO(response.content))
        
        # Check filters are applied
        id_column = feather_table.column('id')
        env_column = feather_table.column('environment')
        
        for i in range(len(feather_table)):
            assert id_column[i].as_py() == "12345"
            assert env_column[i].as_py() == "production"

    def test_feather_endpoint_performance(self, client):
        """Test Feather endpoint performance (file size should be reasonable)."""
        payload = {}  # All data
        
        response = client.post("/api/query/feather", json=payload)
        assert response.status_code == 200
        
        feather_size = len(response.content)
        
        # Get equivalent JSON response
        json_response = client.post("/api/query", json=payload)
        json_size = len(json_response.content)
        
        # Feather should be reasonably sized (not massively larger than JSON)
        # This is a basic sanity check
        assert feather_size > 0
        assert feather_size < json_size * 10  # Arbitrary reasonable upper bound