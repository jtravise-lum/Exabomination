"""Authentication middleware for API."""

import time
from typing import Optional, Dict, List, Callable
from datetime import datetime, timedelta
import hashlib
import os
import json
import logging
from functools import wraps

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_429_TOO_MANY_REQUESTS
)

from src.config import API_RATE_LIMIT, API_CONCURRENT_LIMIT

logger = logging.getLogger(__name__)

# Simple in-memory session storage
# In production, this should be replaced with a database or Redis
api_key_storage = {}  # Maps API keys to user info
session_storage = {}  # Maps session tokens to user info
rate_limit_storage = {}  # Maps API keys to rate limit info
concurrent_request_count = {}  # Maps API keys to current concurrent request count

# Security bearer token scheme
security = HTTPBearer()


def get_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract and validate API key from authorization header.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Validated API key
        
    Raises:
        HTTPException: If the API key is invalid or missing
    """
    if not credentials or not credentials.credentials:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Missing API key"
        )
    
    api_key = credentials.credentials
    
    # In a real implementation, you would validate the API key against a database
    # For now, we'll just check if it's in our simple in-memory storage
    if api_key not in api_key_storage:
        # For testing purposes, automatically register new API keys
        # In production, this should be removed
        if os.getenv("DEBUG_MODE", "False").lower() in ("true", "t", "1"):
            # Create a new user entry for this API key
            api_key_storage[api_key] = {
                "user_id": f"usr_{hashlib.md5(api_key.encode()).hexdigest()[:8]}",
                "account_tier": "standard",
                "features_enabled": [
                    "basic_search",     # Add basic_search permission
                    "advanced_filtering",
                    "query_history", 
                    "feedback", 
                    "suggestions"
                ]
            }
            logger.info(f"Registered new API key for testing: {api_key[:8]}...")
        else:
            logger.warning(f"Invalid API key: {api_key[:8]}...")
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
    
    return api_key


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for enforcing rate limits on API requests."""
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and enforce rate limits.
        
        Args:
            request: The incoming request
            call_next: The next handler in the middleware chain
            
        Returns:
            The response from the next handler
            
        Raises:
            HTTPException: If the rate limit is exceeded
        """
        # Skip rate limiting for non-API routes
        if not request.url.path.startswith("/v1"):
            return await call_next(request)
        
        # Get API key from auth header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # Let the auth middleware handle this case
            return await call_next(request)
        
        api_key = auth_header.replace("Bearer ", "")
        
        # Check and update rate limits
        now = time.time()
        
        # Initialize rate limit info if not exists
        if api_key not in rate_limit_storage:
            rate_limit_storage[api_key] = {
                "count": 0,
                "reset_at": now + 60,  # Reset after 60 seconds
                "requests": []  # List of timestamps for rolling window
            }
        
        # Clean up old requests from rolling window
        rate_limit_storage[api_key]["requests"] = [
            ts for ts in rate_limit_storage[api_key]["requests"]
            if ts > now - 60  # Keep requests from the last 60 seconds
        ]
        
        # Check if rate limit exceeded
        if len(rate_limit_storage[api_key]["requests"]) >= API_RATE_LIMIT:
            # Reset time is the oldest request time + 60 seconds
            reset_at = rate_limit_storage[api_key]["requests"][0] + 60
            reset_at_iso = datetime.fromtimestamp(reset_at).isoformat()
            
            logger.warning(f"Rate limit exceeded for API key: {api_key[:8]}...")
            
            # Return rate limit error
            error_response = {
                "error": {
                    "code": "rate_limit_exceeded",
                    "message": f"Rate limit of {API_RATE_LIMIT} requests per minute exceeded",
                    "details": {
                        "limit": API_RATE_LIMIT,
                        "reset_at": reset_at_iso
                    }
                },
                "request_id": f"req_{hashlib.md5(str(now).encode()).hexdigest()[:12]}"
            }
            
            return HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                detail=error_response
            )
        
        # Check concurrent request limit
        if api_key not in concurrent_request_count:
            concurrent_request_count[api_key] = 0
            
        if concurrent_request_count[api_key] >= API_CONCURRENT_LIMIT:
            error_response = {
                "error": {
                    "code": "concurrent_limit_exceeded",
                    "message": f"Concurrent request limit of {API_CONCURRENT_LIMIT} exceeded",
                    "details": {
                        "limit": API_CONCURRENT_LIMIT
                    }
                },
                "request_id": f"req_{hashlib.md5(str(now).encode()).hexdigest()[:12]}"
            }
            
            return HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                detail=error_response
            )
            
        # Update rate limit counters
        rate_limit_storage[api_key]["requests"].append(now)
        concurrent_request_count[api_key] += 1
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Add rate limit headers to the response
            remaining = API_RATE_LIMIT - len(rate_limit_storage[api_key]["requests"])
            response.headers["X-Rate-Limit-Limit"] = str(API_RATE_LIMIT)
            response.headers["X-Rate-Limit-Remaining"] = str(remaining)
            response.headers["X-Rate-Limit-Reset"] = str(int(rate_limit_storage[api_key]["reset_at"]))
            
            return response
        finally:
            # Decrement concurrent request count
            concurrent_request_count[api_key] -= 1


def check_permissions(required_permissions: List[str]):
    """Decorator to check if user has required permissions.
    
    Args:
        required_permissions: List of permissions required for the endpoint
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, api_key: str = Depends(get_api_key), **kwargs):
            # Get user info from API key
            user_info = api_key_storage.get(api_key, {})
            account_tier = user_info.get("account_tier", "standard")
            features_enabled = user_info.get("features_enabled", [])
            
            # Check if user has all required permissions
            missing_permissions = [
                perm for perm in required_permissions
                if perm not in features_enabled
            ]
            
            if missing_permissions:
                logger.warning(f"Permission denied for API key: {api_key[:8]}...")
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail={
                        "error": {
                            "code": "insufficient_permissions",
                            "message": "Insufficient permissions",
                            "details": {
                                "missing_permissions": missing_permissions,
                                "account_tier": account_tier
                            }
                        },
                        "request_id": f"req_{hashlib.md5(str(time.time()).encode()).hexdigest()[:12]}"
                    }
                )
            
            return await func(*args, api_key=api_key, **kwargs)
        
        return wrapper
    
    return decorator


def get_session_status(api_key: str) -> Dict:
    """Get session status for a user.
    
    Args:
        api_key: API key
        
    Returns:
        Session status information
    """
    # Get user info
    user_info = api_key_storage.get(api_key, {})
    user_id = user_info.get("user_id", f"usr_{hashlib.md5(api_key.encode()).hexdigest()[:8]}")
    account_tier = user_info.get("account_tier", "standard")
    features_enabled = user_info.get("features_enabled", [])
    
    # Get rate limit info
    now = time.time()
    rate_info = rate_limit_storage.get(api_key, {
        "requests": [],
        "reset_at": now + 60
    })
    
    # Clean up old requests
    rate_info["requests"] = [
        ts for ts in rate_info.get("requests", [])
        if ts > now - 60
    ]
    
    # Calculate remaining requests
    remaining = API_RATE_LIMIT - len(rate_info["requests"])
    
    # Calculate session expiration (24 hours from now)
    session_expires_at = datetime.now() + timedelta(hours=24)
    
    return {
        "authenticated": True,
        "user_id": user_id,
        "session_expires_at": session_expires_at.isoformat(),
        "rate_limit": {
            "limit": API_RATE_LIMIT,
            "remaining": remaining,
            "reset_at": datetime.fromtimestamp(rate_info["reset_at"]).isoformat()
        },
        "account_tier": account_tier,
        "features_enabled": features_enabled
    }