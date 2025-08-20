import pytest
from datetime import date
from pydantic import ValidationError
from app.models.schemas import QueryPayload, QueryResponse, ErrorResponse, ValidationErrorResponse


class TestQueryPayload:
    """Test QueryPayload model validation."""

    def test_valid_payload(self):
        """Test creating a valid QueryPayload."""
        payload = QueryPayload(
            id="12345",
            fromDate="2024/01/15",
            toDate="2024/12/31"
        )
        assert payload.id == "12345"
        assert payload.fromDate == "2024/01/15"
        assert payload.toDate == "2024/12/31"

    def test_valid_payload_with_numeric_id(self):
        """Test creating a valid QueryPayload with numeric ID."""
        payload = QueryPayload(
            id=12345,
            fromDate="2024/01/15",
            toDate="2024/12/31"
        )
        assert payload.id == 12345
        assert payload.fromDate == "2024/01/15"
        assert payload.toDate == "2024/12/31"

    def test_invalid_date_format(self):
        """Test validation error with invalid date format."""
        with pytest.raises(ValidationError) as exc_info:
            QueryPayload(
                id="12345",
                fromDate="2024-01-15",  # Wrong format
                toDate="2024/12/31"
            )
        
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('fromDate',) for error in errors)

    def test_invalid_date_format_multiple_fields(self):
        """Test validation error with invalid date format in multiple fields."""
        with pytest.raises(ValidationError) as exc_info:
            QueryPayload(
                id="12345",
                fromDate="15/01/2024",  # Wrong format
                toDate="31-12-2024"     # Wrong format
            )
        
        errors = exc_info.value.errors()
        assert len(errors) >= 2

    def test_date_range_validation_from_after_to(self):
        """Test validation error when fromDate is after toDate."""
        with pytest.raises(ValidationError) as exc_info:
            QueryPayload(
                id="12345",
                fromDate="2024/12/31",
                toDate="2024/01/01"
            )
        
        errors = exc_info.value.errors()
        assert any("fromDate must be less than or equal to toDate" in str(error) for error in errors)

    def test_missing_required_fields(self):
        """Test that all fields are now optional."""
        # This should now succeed since all fields are optional
        payload = QueryPayload()
        assert payload.id is None
        assert payload.fromDate is None
        assert payload.toDate is None
        assert payload.environment is None

    def test_empty_string_dates(self):
        """Test validation error with empty string dates."""
        with pytest.raises(ValidationError):
            QueryPayload(
                id="12345",
                fromDate="",
                toDate=""
            )

    def test_get_parsed_dates(self):
        """Test the get_parsed_dates method."""
        payload = QueryPayload(
            id="12345",
            fromDate="2024/01/15",
            toDate="2024/12/31"
        )
        
        from_date, to_date = payload.get_parsed_dates()
        
        assert from_date == date(2024, 1, 15)
        assert to_date == date(2024, 12, 31)

    def test_get_parsed_dates_with_nulls(self):
        """Test the get_parsed_dates method with null dates."""
        payload = QueryPayload(id="12345")  # No dates provided
        
        from_date, to_date = payload.get_parsed_dates()
        
        assert from_date is None
        assert to_date is None

    def test_leap_year_date(self):
        """Test with leap year date."""
        payload = QueryPayload(
            id="12345",
            fromDate="2024/02/29",  # 2024 is a leap year
            toDate="2024/03/01"
        )
        
        from_date, to_date = payload.get_parsed_dates()
        assert from_date == date(2024, 2, 29)
        assert to_date == date(2024, 3, 1)

    def test_invalid_leap_year_date(self):
        """Test with invalid leap year date."""
        with pytest.raises(ValidationError):
            QueryPayload(
                id="12345",
                fromDate="2023/02/29",  # 2023 is not a leap year
                toDate="2023/03/01"
            )

    def test_edge_case_dates(self):
        """Test with edge case dates."""
        # Same date
        payload = QueryPayload(
            id="12345",
            fromDate="2024/01/15",
            toDate="2024/01/15"
        )
        assert payload.fromDate == payload.toDate

        # Year boundaries
        payload2 = QueryPayload(
            id="12345",
            fromDate="2023/12/31",
            toDate="2024/01/01"
        )
        assert payload2.fromDate == "2023/12/31"
        assert payload2.toDate == "2024/01/01"


class TestQueryResponse:
    """Test QueryResponse model."""

    def test_valid_response(self):
        """Test creating a valid QueryResponse."""
        data = [
            {
                "id": "12345",
                "event_date": "2024-01-15",
                "event_type": "login",
                "description": "User login",
                "value": 1.0,
                "created_at": "2024-01-15T10:30:00"
            }
        ]
        
        response = QueryResponse(
            data=data,
            count=1,
            query_info={"test": "info"}
        )
        
        assert response.data == data
        assert response.count == 1
        assert response.query_info == {"test": "info"}

    def test_empty_response(self):
        """Test creating an empty QueryResponse."""
        response = QueryResponse(
            data=[],
            count=0
        )
        
        assert response.data == []
        assert response.count == 0
        assert response.query_info == {}


class TestErrorResponse:
    """Test ErrorResponse model."""

    def test_basic_error_response(self):
        """Test creating a basic ErrorResponse."""
        response = ErrorResponse(
            error="Test error",
            status_code=400
        )
        
        assert response.error == "Test error"
        assert response.status_code == 400
        assert response.details is None

    def test_error_response_with_details(self):
        """Test creating an ErrorResponse with details."""
        response = ErrorResponse(
            error="Validation failed",
            details="Invalid date format",
            status_code=422
        )
        
        assert response.error == "Validation failed"
        assert response.details == "Invalid date format"
        assert response.status_code == 422


class TestValidationErrorResponse:
    """Test ValidationErrorResponse model."""

    def test_validation_error_response(self):
        """Test creating a ValidationErrorResponse."""
        validation_errors = [
            {"field": ["fromDate"], "message": "Invalid date format"}
        ]
        
        response = ValidationErrorResponse(
            error="Validation failed",
            validation_errors=validation_errors
        )
        
        assert response.error == "Validation failed"
        assert response.validation_errors == validation_errors
        assert response.status_code == 422