import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.api.query import router as query_router
from app.api.error_logging import router as error_logging_router
from app.services.database import close_database_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    logger.info("Starting up Data Extraction API...")
    yield
    logger.info("Shutting down Data Extraction API...")
    close_database_service()


# Create FastAPI application
app = FastAPI(
    title="Data Extraction API",
    description="REST API for querying data from DuckDB based on ID and date range",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
import os
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,https://localhost:3000,http://localhost:5173,http://127.0.0.1:5173,https://localhost:5173,https://127.0.0.1:5173,https://excel.office.com,https://excel.office.live.com,https://excel.officeapps.live.com,https://outlook.office.com,https://outlook.live.com,https://www.office.com").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    """Add security headers for production deployment."""
    response = await call_next(request)
    
    # Security headers for HTTPS
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    
    # Remove server information
    if "server" in response.headers:
        del response.headers["server"]
    
    return response

# Include routers
app.include_router(query_router)
app.include_router(error_logging_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Data Extraction API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_check": "/api/health",
        "database_info": "/api/info",
        "query_endpoint": "/api/query",
        "feather_endpoint": "/api/query/feather",
        "error_logging": "/api/log-client-error",
        "error_stats": "/api/error-stats",
        "error_dashboard": "/api/error-dashboard"
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Enhanced global exception handler with structured logging."""
    import traceback
    import uuid
    
    # Generate unique error ID for tracking
    error_id = str(uuid.uuid4())
    
    # Collect request information
    request_info = {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown")
    }
    
    # Sanitize sensitive headers
    sensitive_headers = ["authorization", "cookie", "x-api-key"]
    for header in sensitive_headers:
        if header in request_info["headers"]:
            request_info["headers"][header] = "[REDACTED]"
    
    # Create structured error log
    error_log = {
        "error_id": error_id,
        "timestamp": datetime.now().isoformat(),
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "request_info": request_info,
        "stack_trace": traceback.format_exc()
    }
    
    # Log the structured error
    logger.error(f"Unhandled server exception: {error_log}")
    
    # Return user-friendly error response
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "details": "An unexpected error occurred",
            "error_id": error_id,
            "timestamp": datetime.now().isoformat()
        }
    )


def main():
    """Main entry point for running the application."""
    import os
    
    # Check for SSL configuration
    ssl_keyfile = os.getenv("SSL_KEYFILE")
    ssl_certfile = os.getenv("SSL_CERTFILE")
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    if ssl_keyfile and ssl_certfile:
        # Production HTTPS configuration
        logger.info(f"Starting server with HTTPS/HTTP2 on {host}:{port}")
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            # http="h2",  # HTTP/2 support requires additional dependencies
            reload=False,  # Disable reload in production
            log_level="info",
            server_header=False,
            date_header=False,
            access_log=True,
            workers=1  # Can be increased for production
        )
    else:
        # Development HTTP configuration
        logger.info(f"Starting server with HTTP on {host}:{port}")
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )


if __name__ == "__main__":
    main()