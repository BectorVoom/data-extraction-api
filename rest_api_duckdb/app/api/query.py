from typing import Union
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError
import logging
from io import BytesIO

from app.models.schemas import (
    QueryPayload, 
    QueryResponse, 
    FeatureResponse,
    ErrorResponse,
    ValidationErrorResponse
)
from app.services.database import get_database_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=Union[QueryResponse, FeatureResponse])
async def query_data(payload: QueryPayload) -> Union[QueryResponse, FeatureResponse]:
    """
    Query data from DuckDB based on ID, date range, and environment.
    
    Args:
        payload: Query parameters including optional id, fromDate, toDate, and environment
        
    Returns:
        QueryResponse with matching data rows
        
    Raises:
        HTTPException: For various error conditions (400, 422, 500)
    """
    try:
        logger.info(f"Received query request: id={payload.id}, fromDate={payload.fromDate}, toDate={payload.toDate}, environment={payload.environment}")
        
        # Get database service
        db_service = get_database_service()
        
        # Parse dates for database query
        from_date, to_date = payload.get_parsed_dates()
        
        # Execute query with optional parameters
        data = db_service.query_events(
            id_filter=str(payload.id) if payload.id is not None else None, 
            from_date=from_date, 
            to_date=to_date,
            environment=payload.environment
        )
        
        # Prepare response based on requested format
        if payload.format == "feature":
            # Convert data to feature format
            features = []
            for row in data:
                feature = {
                    "type": "Feature",
                    "id": row.get("id"),
                    "properties": {k: v for k, v in row.items() if k != "id"},
                    "geometry": None  # Could be extended to include spatial data
                }
                features.append(feature)
            
            metadata = {
                "query_parameters": {
                    "id": str(payload.id) if payload.id is not None else None,
                    "fromDate": payload.fromDate,
                    "toDate": payload.toDate,
                    "environment": payload.environment
                },
                "generated_at": datetime.now().isoformat()
            }
            
            # Add parsed date range info if dates were provided
            if from_date is not None or to_date is not None:
                metadata["date_range_parsed"] = {
                    "from": from_date.isoformat() if from_date else None,
                    "to": to_date.isoformat() if to_date else None
                }
            
            response = FeatureResponse(
                features=features,
                count=len(features),
                metadata=metadata
            )
        else:
            # Default JSON format
            query_info = {
                "id": str(payload.id) if payload.id is not None else None,
                "fromDate": payload.fromDate,
                "toDate": payload.toDate,
                "environment": payload.environment
            }
            
            # Add parsed date range info if dates were provided
            if from_date is not None or to_date is not None:
                query_info["date_range_parsed"] = {
                    "from": from_date.isoformat() if from_date else None,
                    "to": to_date.isoformat() if to_date else None
                }
            
            response = QueryResponse(
                data=data,
                count=len(data),
                query_info=query_info
            )
        
        logger.info(f"Query completed successfully, returned {len(data)} rows in {payload.format} format")
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


@router.post("/query/feather")
async def query_data_feather(payload: QueryPayload) -> StreamingResponse:
    """
    Query data from DuckDB and return as Apache Arrow Feather file.
    
    Args:
        payload: Query parameters including optional id, fromDate, toDate, and environment
        
    Returns:
        StreamingResponse with Feather file content
        
    Raises:
        HTTPException: For various error conditions (400, 422, 500)
    """
    try:
        logger.info(f"Received Feather query request: id={payload.id}, fromDate={payload.fromDate}, toDate={payload.toDate}, environment={payload.environment}")
        
        # Get database service
        db_service = get_database_service()
        
        # Parse dates for database query
        from_date, to_date = payload.get_parsed_dates()
        
        # Execute query and get Feather bytes
        feather_bytes = db_service.query_events_to_feather(
            id_filter=str(payload.id) if payload.id is not None else None, 
            from_date=from_date, 
            to_date=to_date,
            environment=payload.environment
        )
        
        # Generate a filename based on query parameters
        filename_parts = []
        if payload.id is not None:
            filename_parts.append(f"id_{payload.id}")
        if payload.fromDate:
            filename_parts.append(f"from_{payload.fromDate.replace('/', '_')}")
        if payload.toDate:
            filename_parts.append(f"to_{payload.toDate.replace('/', '_')}")
        if payload.environment:
            filename_parts.append(f"env_{payload.environment}")
        
        filename = "_".join(filename_parts) if filename_parts else "data"
        filename = f"query_results_{filename}.feather"
        
        logger.info(f"Feather query completed successfully, returning {len(feather_bytes)} bytes as {filename}")
        
        # Create streaming response with Feather content
        feather_stream = BytesIO(feather_bytes)
        
        return StreamingResponse(
            feather_stream,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/octet-stream",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
        
    except ValidationError as e:
        logger.warning(f"Validation error in Feather endpoint: {e}")
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
        logger.warning(f"Value error in Feather endpoint: {e}")
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
        logger.error(f"Unexpected error during Feather query: {e}", exc_info=True)
        error_response = ErrorResponse(
            error="Internal server error",
            details="An unexpected error occurred while processing the Feather request",
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
                "json_endpoint": {
                    "endpoint": "/api/query",
                    "method": "POST",
                    "required_fields": [],
                    "optional_fields": ["id", "fromDate", "toDate", "environment", "format"],
                    "date_format": "yyyy/mm/dd",
                    "response_format": "JSON",
                    "notes": "All fields are optional. Null values create unbounded queries."
                },
                "feather_endpoint": {
                    "endpoint": "/api/query/feather",
                    "method": "POST",
                    "required_fields": [],
                    "optional_fields": ["id", "fromDate", "toDate", "environment"],
                    "date_format": "yyyy/mm/dd",
                    "response_format": "Apache Arrow Feather (binary)",
                    "media_type": "application/octet-stream",
                    "notes": "Returns data as Feather file for optimal performance and Excel integration. All fields are optional."
                },
                "example_requests": [
                    {
                        "description": "Query all data (no filters)",
                        "payload": {}
                    },
                    {
                        "description": "Query by ID only",
                        "payload": {"id": "12345"}
                    },
                    {
                        "description": "Query by date range only", 
                        "payload": {"fromDate": "2024/01/01", "toDate": "2024/12/31"}
                    },
                    {
                        "description": "Query by environment only",
                        "payload": {"environment": "production"}
                    },
                    {
                        "description": "Query with all filters",
                        "payload": {
                            "id": "12345",
                            "fromDate": "2024/01/01", 
                            "toDate": "2024/12/31",
                            "environment": "production"
                        }
                    },
                    {
                        "description": "Query with feature file format",
                        "payload": {
                            "id": "12345",
                            "environment": "production",
                            "format": "feature"
                        }
                    },
                    {
                        "description": "Query for Feather file (use /api/query/feather endpoint)",
                        "payload": {
                            "id": "12345",
                            "fromDate": "2024/01/01", 
                            "toDate": "2024/12/31",
                            "environment": "production"
                        },
                        "notes": "Returns Apache Arrow Feather file instead of JSON"
                    }
                ]
            }
        }
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to retrieve database information"}
        )