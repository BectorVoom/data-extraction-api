from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import logging

from app.models.schemas import (
    QueryPayload, 
    QueryResponse, 
    ErrorResponse,
    ValidationErrorResponse
)
from app.services.database import get_database_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query_data(payload: QueryPayload) -> QueryResponse:
    """
    Query data from DuckDB based on ID and date range.
    
    Args:
        payload: Query parameters including id, fromDate, and toDate
        
    Returns:
        QueryResponse with matching data rows
        
    Raises:
        HTTPException: For various error conditions (400, 422, 500)
    """
    try:
        logger.info(f"Received query request: id={payload.id}, fromDate={payload.fromDate}, toDate={payload.toDate}")
        
        # Get database service
        db_service = get_database_service()
        
        # Parse dates for database query
        from_date, to_date = payload.get_parsed_dates()
        
        # Execute query
        data = db_service.query_events(
            id_filter=str(payload.id), 
            from_date=from_date, 
            to_date=to_date
        )
        
        # Prepare response
        response = QueryResponse(
            data=data,
            count=len(data),
            query_info={
                "id": str(payload.id),
                "fromDate": payload.fromDate,
                "toDate": payload.toDate,
                "date_range_parsed": {
                    "from": from_date.isoformat(),
                    "to": to_date.isoformat()
                }
            }
        )
        
        logger.info(f"Query completed successfully, returned {len(data)} rows")
        return response
        
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        error_response = ValidationErrorResponse(
            error="Validation failed",
            validation_errors=[{"field": err["loc"], "message": err["msg"]} for err in e.errors()],
            status_code=422
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_response.model_dump()
        )
        
    except ValueError as e:
        logger.warning(f"Value error: {e}")
        error_response = ErrorResponse(
            error="Invalid input data",
            details=str(e),
            status_code=400
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response.model_dump()
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during query: {e}", exc_info=True)
        error_response = ErrorResponse(
            error="Internal server error",
            details="An unexpected error occurred while processing the request",
            status_code=500
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump()
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        db_service = get_database_service()
        table_info = db_service.get_table_info()
        
        return {
            "status": "healthy",
            "database": {
                "connected": True,
                "row_count": table_info["row_count"],
                "available_ids": table_info["unique_ids"]
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "error": str(e)
            }
        )


@router.get("/info")
async def database_info():
    """Get database information including schema and sample data."""
    try:
        db_service = get_database_service()
        table_info = db_service.get_table_info()
        
        return {
            "database_info": table_info,
            "api_info": {
                "endpoint": "/api/query",
                "method": "POST",
                "required_fields": ["id", "fromDate", "toDate"],
                "date_format": "yyyy/mm/dd",
                "example_request": {
                    "id": "12345",
                    "fromDate": "2024/01/01",
                    "toDate": "2024/12/31"
                }
            }
        }
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to retrieve database information"}
        )