"""FastAPI Application for Exabomination API."""

import logging
import uuid
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from frontend.api.routes import router
from frontend.api.auth import RateLimitMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Exabomination API",
    description="API for Exabeam Automated Search Assistant",
    version="1.0.0",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
    openapi_url="/v1/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, this should be restricted
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limit middleware
app.add_middleware(RateLimitMiddleware)


# Add request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next: Callable) -> Response:
    """Add request ID to each request.
    
    Args:
        request: Request
        call_next: Next middleware
        
    Returns:
        Response
    """
    # Generate request ID if not present
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        
    # Add request ID to request state
    request.state.request_id = request_id
    
    # Process request and add ID to response headers
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# Add API router
app.include_router(router)


# Global exception handler
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions.
    
    Args:
        request: Request
        exc: Exception
        
    Returns:
        JSON response
    """
    logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
    
    # Get request ID
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Format error response
    error_content = {
        "error": {
            "code": f"http_{exc.status_code}",
            "message": str(exc.detail)
        },
        "request_id": request_id
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_content
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions.
    
    Args:
        request: Request
        exc: Exception
        
    Returns:
        JSON response
    """
    logger.error(f"Unhandled exception: {str(exc)}")
    
    # Get request ID
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Format error response
    error_content = {
        "error": {
            "code": "internal_server_error",
            "message": "An internal server error occurred"
        },
        "request_id": request_id
    }
    
    return JSONResponse(
        status_code=500,
        content=error_content
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint.
    
    Returns:
        Health status
    """
    return {"status": "ok", "timestamp": time.time()}