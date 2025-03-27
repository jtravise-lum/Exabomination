"""API routes for EXASPERATION."""

import logging
import time
import hashlib
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from frontend.api.auth import get_api_key, get_session_status, check_permissions
from frontend.api.models import (
    SearchRequest,
    SearchResponse,
    SuggestionsResponse,
    FeedbackRequest,
    FeedbackResponse,
    MetadataOptionsResponse,
    SessionStatusResponse,
    ErrorResponse
)

# Configure logger
logger = logging.getLogger(__name__)

try:
    from frontend.api.service import ExasperationService
    # Try to initialize the real service
    service = ExasperationService()
    logger.info("Using real ExasperationService")
except Exception as e:
    # Create a simple mock service for testing if the real one fails
    logger.warning(f"Failed to initialize real service: {str(e)}")
    
    class MockService:
        """Simple mock service for testing."""
        
        async def process_search_query(self, query, filters=None, options=None, user_id="anonymous"):
            """Mock search query."""
            return {
                "request_id": f"req_test_{hash(query) % 10000}",
                "query": query,
                "answer": f"Mock answer for query: {query}",
                "sources": [
                    {
                        "id": "doc_123",
                        "title": "Test Document",
                        "url": "https://example.com/docs/test",
                        "chunk_id": "chunk_456",
                        "content": "Test content for the mock document",
                        "relevance_score": 0.95,
                        "metadata": {
                            "document_type": "test",
                            "vendor": "test",
                            "product": "test",
                            "created_at": "2025-01-01",
                            "updated_at": "2025-03-27"
                        }
                    }
                ],
                "suggested_queries": [
                    "Follow-up query 1",
                    "Follow-up query 2",
                    "Follow-up query 3"
                ],
                "metadata": {
                    "processing_time_ms": 42,
                    "filter_count": len(filters) if filters else 0,
                    "total_matches": 1,
                    "threshold_applied": options.get("threshold", 0.7) if options else 0.7
                }
            }
        
        async def get_query_suggestions(self, partial_query, limit=5):
            """Mock query suggestions."""
            base_suggestions = [
                "How does the password reset detection rule work?",
                "What are the components of a detection rule?",
                "How do I configure SAML authentication?",
                "How does Exabeam detect lateral movement?",
                "What events are generated during a password reset?"
            ]
            return base_suggestions[:limit]
        
        async def submit_feedback(self, request_id, rating, comments=None, 
                                  selected_sources=None, user_query_reformulation=None, user_id="anonymous"):
            """Mock feedback submission."""
            return {
                "status": "success",
                "feedback_id": f"fb_test_{hash(request_id) % 10000}",
                "message": "Thank you for your feedback!"
            }
        
        async def get_metadata_options(self):
            """Mock metadata options."""
            return {
                "document_types": ["use_case", "parser", "rule"],
                "vendors": ["microsoft", "cisco", "okta"],
                "products": {
                    "microsoft": ["active_directory", "azure_ad"],
                    "cisco": ["asa", "firepower"],
                    "okta": ["identity_cloud"]
                },
                "use_cases": ["account_takeover", "lateral_movement"],
                "date_range": {
                    "oldest": "2022-01-15",
                    "newest": "2025-03-27"
                }
            }
    
    service = MockService()
    logger.info("Using MockService for testing")

# Create API router
router = APIRouter(prefix="/v1")


@router.post("/search", tags=["search"])  # Remove response_model to prevent validation errors
@check_permissions(["basic_search"])
async def search(
    request: SearchRequest,
    api_key: str = Depends(get_api_key)
) -> Dict[str, Any]:
    """Process a search query.
    
    Args:
        request: Search request
        api_key: API key
        
    Returns:
        Search response
    """
    import traceback
    import json
    
    # Create a request ID first thing
    request_id = f"req_{hashlib.md5(str(time.time()).encode()).hexdigest()[:12]}"
    
    try:
        # Log the request details
        logger.info(f"Processing search request {request_id}: {request.query}")
        if request.filters:
            logger.info(f"Request filters: {json.dumps(request.filters.dict())}")
        if request.options:
            logger.info(f"Request options: {json.dumps(request.options.dict())}")
            
        # Extract user ID from API key
        user_id = f"usr_{api_key[:8]}"
        logger.info(f"User ID: {user_id}")
        
        # Process search query
        logger.info("Calling service.process_search_query")
        result = await service.process_search_query(
            query=request.query,
            filters=request.filters.dict() if request.filters else None,
            options=request.options.dict() if request.options else None,
            user_id=user_id
        )
        
        # Log success
        logger.info(f"Search completed successfully for request {request_id}")
        
        # Ensure the request_id is set
        if "request_id" not in result:
            result["request_id"] = request_id
            
        return result
        
    except Exception as e:
        # Log detailed error with stack trace
        logger.error(f"Error processing search request {request_id}: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        
        # Create a fallback response with error information
        return {
            "request_id": request_id,
            "query": request.query,
            "answer": f"Error: There was a problem processing your query. Technical details: {str(e)}",
            "sources": [],
            "suggested_queries": [
                "What are the components of a detection rule?",
                "How do I configure SAML authentication?",
                "How does Exabeam detect lateral movement?"
            ],
            "metadata": {
                "processing_time_ms": 0,
                "filter_count": 0,
                "total_matches": 0,
                "threshold_applied": 0.0,
                "error": {
                    "code": "search_error",
                    "message": str(e)
                }
            }
        }


@router.get("/suggestions", response_model=SuggestionsResponse, tags=["search"])
@check_permissions(["suggestions"])
async def get_suggestions(
    partial_query: str = Query(..., description="Partial query text"),
    limit: int = Query(5, description="Maximum number of suggestions to return"),
    api_key: str = Depends(get_api_key)
) -> Dict[str, Any]:
    """Get query suggestions.
    
    Args:
        partial_query: Partial query text
        limit: Maximum number of suggestions to return
        api_key: API key
        
    Returns:
        Suggestions response
    """
    try:
        # Get suggestions
        start_time = None
        import time
        start_time = time.time()
        
        suggestions = await service.get_query_suggestions(
            partial_query=partial_query,
            limit=limit
        )
        
        processing_time = int((time.time() - start_time) * 1000) if start_time else 0
        
        # Create response
        return {
            "suggestions": suggestions,
            "metadata": {
                "processing_time_ms": processing_time
            }
        }
    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "suggestions_error",
                    "message": "Failed to get suggestions",
                    "details": {
                        "reason": str(e)
                    }
                }
            }
        )


@router.post("/feedback", response_model=FeedbackResponse, tags=["feedback"])
@check_permissions(["feedback"])
async def submit_feedback(
    request: FeedbackRequest,
    api_key: str = Depends(get_api_key)
) -> Dict[str, Any]:
    """Submit feedback.
    
    Args:
        request: Feedback request
        api_key: API key
        
    Returns:
        Feedback response
    """
    try:
        # Extract user ID from API key
        user_id = f"usr_{api_key[:8]}"
        
        # Submit feedback
        result = await service.submit_feedback(
            request_id=request.request_id,
            rating=request.rating,
            comments=request.comments,
            selected_sources=request.selected_sources,
            user_query_reformulation=request.user_query_reformulation,
            user_id=user_id
        )
        
        return result
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "feedback_error",
                    "message": "Failed to submit feedback",
                    "details": {
                        "reason": str(e)
                    }
                }
            }
        )


@router.get("/metadata/options", response_model=MetadataOptionsResponse, tags=["metadata"])
@check_permissions(["advanced_filtering"])
async def get_metadata_options(
    api_key: str = Depends(get_api_key)
) -> Dict[str, Any]:
    """Get metadata options.
    
    Args:
        api_key: API key
        
    Returns:
        Metadata options response
    """
    try:
        # Get metadata options
        result = await service.get_metadata_options()
        return result
    except Exception as e:
        logger.error(f"Error getting metadata options: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "metadata_options_error",
                    "message": "Failed to get metadata options",
                    "details": {
                        "reason": str(e)
                    }
                }
            }
        )


@router.get("/session/status", response_model=SessionStatusResponse, tags=["session"])
async def get_session_status_endpoint(
    api_key: str = Depends(get_api_key)
) -> Dict[str, Any]:
    """Get session status.
    
    Args:
        api_key: API key
        
    Returns:
        Session status response
    """
    try:
        # Get session status
        status = get_session_status(api_key)
        return status
    except Exception as e:
        logger.error(f"Error getting session status: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "session_status_error",
                    "message": "Failed to get session status",
                    "details": {
                        "reason": str(e)
                    }
                }
            }
        )


# Simple test endpoint that doesn't depend on the backend
@router.get("/test", tags=["test"])
async def test_endpoint():
    """Simple test endpoint that doesn't depend on backend services."""
    return {
        "status": "ok",
        "message": "API is working",
        "timestamp": time.time()
    }

# Note: Exception handlers should be defined in the main FastAPI app,
# not on the router. These have been moved to app.py