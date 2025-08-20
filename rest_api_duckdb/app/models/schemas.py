from datetime import datetime, date
from typing import List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class QueryPayload(BaseModel):
    """Request payload for querying data from DuckDB."""
    id: Union[str, int, None] = Field(None, description="Unique identifier to filter rows (optional)")
    fromDate: Union[str, None] = Field(None, description="Start date in yyyy/mm/dd format (inclusive, optional)")
    toDate: Union[str, None] = Field(None, description="End date in yyyy/mm/dd format (inclusive, optional)")
    environment: Union[str, None] = Field(None, description="Environment filter (optional)")
    format: Literal["json", "feature"] = Field("json", description="Response format: 'json' (default) or 'feature' file format")

    @field_validator("fromDate", "toDate")
    @classmethod
    def validate_date_format(cls, v: Union[str, None]) -> Union[str, None]:
        """Validate that dates are in yyyy/mm/dd format."""
        if v is None:
            return v
        
        if not isinstance(v, str):
            raise ValueError("Date must be a string")
        
        try:
            # Strictly enforce yyyy/mm/dd format
            parsed_date = datetime.strptime(v, "%Y/%m/%d")
            # Return the original string if parsing succeeds
            return v
        except ValueError:
            raise ValueError("Date must be in yyyy/mm/dd format")

    @model_validator(mode='after')
    def validate_date_range(self) -> 'QueryPayload':
        """Validate that fromDate is not after toDate."""
        # Skip validation if either date is None
        if self.fromDate is None or self.toDate is None:
            return self
            
        try:
            from_date = datetime.strptime(self.fromDate, "%Y/%m/%d").date()
            to_date = datetime.strptime(self.toDate, "%Y/%m/%d").date()
            
            if from_date > to_date:
                raise ValueError("fromDate must be less than or equal to toDate")
        except ValueError as e:
            if "fromDate must be less than or equal to toDate" in str(e):
                raise e
            # Re-raise date format errors
            raise ValueError("Invalid date format")
        
        return self

    def get_parsed_dates(self) -> tuple[Union[date, None], Union[date, None]]:
        """Get the parsed date objects for database queries."""
        from_date = datetime.strptime(self.fromDate, "%Y/%m/%d").date() if self.fromDate else None
        to_date = datetime.strptime(self.toDate, "%Y/%m/%d").date() if self.toDate else None
        return from_date, to_date


class QueryResponse(BaseModel):
    """Response containing query results."""
    data: List[Dict[str, Any]] = Field(..., description="Array of matching rows")
    count: int = Field(..., description="Number of rows returned")
    query_info: Dict[str, Any] = Field(default_factory=dict, description="Additional query metadata")


class FeatureResponse(BaseModel):
    """Response containing query results in feature file format."""
    features: List[Dict[str, Any]] = Field(..., description="Array of feature records")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Feature collection metadata")
    count: int = Field(..., description="Number of features returned")
    format: str = Field("feature", description="Response format identifier")


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error message")
    details: str = Field(None, description="Additional error details")
    status_code: int = Field(..., description="HTTP status code")


class ValidationErrorResponse(BaseModel):
    """Validation error response with field details."""
    error: str = Field(..., description="Error message")
    validation_errors: List[Dict[str, Any]] = Field(..., description="Field-specific validation errors")
    status_code: int = Field(default=422, description="HTTP status code")