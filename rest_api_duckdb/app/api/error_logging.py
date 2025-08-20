# rest_api_duckdb/app/api/error_logging.py
# FastAPI endpoint for client error collection with Python-based processing

import logging
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator
import asyncio
import os

# Configure logging for error collection
logger = logging.getLogger(__name__)

# Create router for error logging endpoints
router = APIRouter(prefix="/api", tags=["error-logging"])

# Configure templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

# Rate limiting configuration
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_ERRORS = 20  # max errors per client per window
RATE_LIMIT_MAX_ERRORS_GLOBAL = 200  # max errors globally per window

# In-memory storage for rate limiting (in production, use Redis or similar)
client_error_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
global_error_count = {"count": 0, "window_start": datetime.now()}

# Error classification patterns
ERROR_CLASSIFICATION_PATTERNS = {
    "validation_error": [
        r"validation failed",
        r"must be in yyyy/mm/dd format",
        r"invalid date format",
        r"required field"
    ],
    "api_error": [
        r"http \d{3}",
        r"network error",
        r"fetch failed",
        r"connection refused",
        r"timeout"
    ],
    "excel_error": [
        r"office\.js",
        r"excel",
        r"workbook",
        r"worksheet",
        r"range",
        r"context\.sync"
    ],
    "javascript_error": [
        r"referenceerror",
        r"typeerror",
        r"syntaxerror",
        r"rangeerror"
    ]
}

class ErrorPayload(BaseModel):
    """Model for client error reports"""
    type: str = Field(..., description="Error type (e.g., 'javascript_error', 'api_error')")
    message: str = Field(..., description="Error message")
    stack: Optional[str] = Field(None, description="Stack trace")
    filename: Optional[str] = Field(None, description="Source filename")
    lineno: Optional[int] = Field(None, description="Line number")
    colno: Optional[int] = Field(None, description="Column number")
    userAgent: str = Field(..., description="User agent string")
    url: str = Field(..., description="Current page URL")
    timestamp: str = Field(..., description="ISO timestamp")
    sessionId: str = Field(..., description="Session identifier")
    errorId: str = Field(..., description="Unique error identifier")
    officeContext: Optional[Dict[str, Any]] = Field(None, description="Office.js context")
    excelContext: Optional[Dict[str, Any]] = Field(None, description="Excel-specific context")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    operation: Optional[str] = Field(None, description="Operation that failed")
    endpoint: Optional[str] = Field(None, description="API endpoint for API errors")
    field: Optional[str] = Field(None, description="Field name for validation errors")
    formData: Optional[Dict[str, Any]] = Field(None, description="Form data for validation errors")
    requestContext: Optional[Dict[str, Any]] = Field(None, description="Request context for API errors")

    @validator('message')
    def sanitize_message(cls, v):
        """Sanitize error message to remove potential PII"""
        if not v:
            return v
        
        # Truncate very long messages
        if len(v) > 2000:
            v = v[:2000] + "... [TRUNCATED]"
        
        # Mask potential PII patterns
        v = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', v)
        v = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CARD_REDACTED]', v)
        v = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', v)
        
        return v

    @validator('stack')
    def sanitize_stack(cls, v):
        """Sanitize stack trace"""
        if not v:
            return v
        
        # Truncate very long stack traces
        if len(v) > 8000:
            v = v[:8000] + "... [TRUNCATED]"
        
        return v

class ErrorResponse(BaseModel):
    """Response model for error logging"""
    status: str
    errorId: str
    message: str

def get_client_identifier(request: Request) -> str:
    """Get client identifier for rate limiting"""
    # Use X-Forwarded-For if available (for proxied requests), otherwise use client IP
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    
    # Include user agent for more specific client identification
    user_agent = request.headers.get("user-agent", "")[:100]  # Truncate to avoid huge strings
    return f"{client_ip}:{hash(user_agent) % 10000}"

def is_rate_limited(client_id: str) -> bool:
    """Check if client is rate limited"""
    now = datetime.now()
    current_minute = int(now.timestamp() // RATE_LIMIT_WINDOW)
    
    # Clean up old entries
    client_data = client_error_counts[client_id]
    old_keys = [k for k in client_data.keys() if int(k) < current_minute - 1]
    for key in old_keys:
        del client_data[key]
    
    # Check client rate limit
    current_count = client_data.get(str(current_minute), 0)
    if current_count >= RATE_LIMIT_MAX_ERRORS:
        return True
    
    # Check global rate limit
    global global_error_count
    if (now - global_error_count["window_start"]).seconds >= RATE_LIMIT_WINDOW:
        global_error_count = {"count": 0, "window_start": now}
    
    if global_error_count["count"] >= RATE_LIMIT_MAX_ERRORS_GLOBAL:
        return True
    
    # Increment counters
    client_error_counts[client_id][str(current_minute)] += 1
    global_error_count["count"] += 1
    
    return False

def classify_error(error_payload: ErrorPayload) -> List[str]:
    """Classify error based on type and message content"""
    classifications = []
    
    # Add explicit type classification
    classifications.append(error_payload.type)
    
    # Pattern-based classification
    message_lower = error_payload.message.lower()
    stack_lower = (error_payload.stack or "").lower()
    combined_text = f"{message_lower} {stack_lower}"
    
    for classification, patterns in ERROR_CLASSIFICATION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, combined_text):
                if classification not in classifications:
                    classifications.append(classification)
                break
    
    return classifications

def should_forward_to_claude(error_payload: ErrorPayload, classifications: List[str]) -> bool:
    """Determine if error should be forwarded to Claude Code for analysis"""
    
    # Forward Excel-specific errors (these are likely most valuable to analyze)
    if "excel_error" in classifications:
        return True
    
    # Forward API errors with specific patterns
    if "api_error" in classifications:
        api_error_keywords = ["timeout", "500", "502", "503", "connection refused"]
        if any(keyword in error_payload.message.lower() for keyword in api_error_keywords):
            return True
    
    # Forward validation errors that might indicate UX issues
    if "validation_error" in classifications:
        validation_keywords = ["format", "required", "invalid"]
        if any(keyword in error_payload.message.lower() for keyword in validation_keywords):
            return True
    
    # Forward JavaScript errors that might indicate code issues
    if "javascript_error" in classifications:
        js_error_keywords = ["referenceerror", "typeerror"]
        if any(keyword in error_payload.message.lower() for keyword in js_error_keywords):
            return True
    
    return False

async def persist_error(error_payload: ErrorPayload, classifications: List[str]):
    """Persist error to storage (implement based on your storage solution)"""
    
    # For now, log to application logger
    # In production, you might want to store in database, send to monitoring service, etc.
    
    error_record = {
        "timestamp": error_payload.timestamp,
        "type": error_payload.type,
        "classifications": classifications,
        "message": error_payload.message,
        "session_id": error_payload.sessionId,
        "error_id": error_payload.errorId,
        "user_agent": error_payload.userAgent,
        "url": error_payload.url
    }
    
    # Add context information if available
    if error_payload.officeContext:
        error_record["office_context"] = error_payload.officeContext
    
    if error_payload.excelContext:
        error_record["excel_context"] = error_payload.excelContext
    
    # Log the error
    logger.info(f"Client error collected: {json.dumps(error_record)}")

async def forward_to_claude_analysis(error_payload: ErrorPayload, classifications: List[str]):
    """Forward error to Claude Code for analysis"""
    
    from app.services.claude_analyzer import claude_analyzer
    
    try:
        # Convert Pydantic model to dict for analysis
        payload_dict = {
            "errorId": error_payload.errorId,
            "type": error_payload.type,
            "message": error_payload.message,
            "stack": error_payload.stack,
            "timestamp": error_payload.timestamp,
            "office_context": error_payload.officeContext,
            "excel_context": error_payload.excelContext,
            "operation": error_payload.operation,
            "endpoint": error_payload.endpoint,
            "userAgent": error_payload.userAgent,
            "url": error_payload.url
        }
        
        # Perform Claude analysis
        analysis_result = await claude_analyzer.analyze_error(payload_dict, classifications)
        
        if analysis_result:
            logger.info(f"Claude analysis completed for error {error_payload.errorId}: {json.dumps(analysis_result, indent=2)}")
            
            # Here you could store the analysis result in a database or send it to monitoring systems
            # For now, we'll just log it
            
        else:
            logger.warning(f"Claude analysis failed or disabled for error {error_payload.errorId}")
            
    except Exception as e:
        logger.error(f"Error during Claude analysis for {error_payload.errorId}: {e}")

@router.post("/log-client-error", response_model=ErrorResponse)
async def log_client_error(
    error_payload: ErrorPayload,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Endpoint for collecting client-side errors from the Excel Add-in
    
    This endpoint:
    1. Validates and sanitizes incoming error data
    2. Applies rate limiting to prevent abuse
    3. Classifies errors for better analysis
    4. Persists errors to storage
    5. Forwards high-priority errors to Claude Code analysis
    """
    
    # Rate limiting check
    client_id = get_client_identifier(request)
    if is_rate_limited(client_id):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Too many errors reported."
        )
    
    try:
        # Classify the error
        classifications = classify_error(error_payload)
        
        # Schedule background tasks for processing
        background_tasks.add_task(persist_error, error_payload, classifications)
        
        # Check if error should be forwarded to Claude
        if should_forward_to_claude(error_payload, classifications):
            background_tasks.add_task(forward_to_claude_analysis, error_payload, classifications)
        
        return ErrorResponse(
            status="accepted",
            errorId=error_payload.errorId,
            message="Error logged successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to process client error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process error report"
        )

@router.get("/error-stats")
async def get_error_stats(request: Request):
    """
    Get basic error statistics (for debugging/monitoring)
    
    This endpoint provides basic stats about error collection rates
    """
    
    client_id = get_client_identifier(request)
    now = datetime.now()
    current_minute = int(now.timestamp() // RATE_LIMIT_WINDOW)
    
    client_data = client_error_counts.get(client_id, {})
    current_client_count = client_data.get(str(current_minute), 0)
    
    return {
        "rate_limiting": {
            "client_id": client_id,
            "current_minute_errors": current_client_count,
            "max_errors_per_minute": RATE_LIMIT_MAX_ERRORS,
            "global_errors_current_window": global_error_count["count"],
            "global_max_per_window": RATE_LIMIT_MAX_ERRORS_GLOBAL
        },
        "error_classification": {
            "available_patterns": list(ERROR_CLASSIFICATION_PATTERNS.keys())
        }
    }

@router.get("/error-dashboard", response_class=HTMLResponse)
async def error_dashboard(request: Request):
    """
    Serve the error monitoring dashboard
    
    This endpoint serves a web interface for viewing and analyzing collected errors
    """
    
    return templates.TemplateResponse("error_dashboard.html", {"request": request})