"""API client for the EXASPERATION backend."""

import json
import time
from typing import Dict, Any, List, Optional, Union

import httpx
import streamlit as st

from frontend.api.models import (
    SearchRequest, 
    SearchResponse, 
    SearchFilters, 
    SearchOptions,
    SuggestionsResponse,
    FeedbackRequest,
    FeedbackResponse,
    MetadataOptionsResponse,
    SessionStatusResponse,
    ErrorResponse
)
from frontend.config import API_URL, API_KEY, API_TIMEOUT

# Default API URL points to the API server being developed in parallel
# API uses a /v1 prefix as defined in frontend/api/app.py and routes.py


class APIClient:
    """Client for interacting with the EXASPERATION backend API."""

    def __init__(self, base_url: str = API_URL, api_key: str = API_KEY, timeout: int = API_TIMEOUT):
        """Initialize the API client.
        
        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
            timeout: Timeout for API requests in seconds
        """
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def search(
        self, 
        query: str, 
        filters: Optional[SearchFilters] = None, 
        options: Optional[SearchOptions] = None
    ) -> Union[SearchResponse, ErrorResponse]:
        """Submit a search query to the backend.
        
        Args:
            query: User's natural language query
            filters: Optional search filters
            options: Optional search options
            
        Returns:
            Response from the API as a SearchResponse or ErrorResponse
        """
        # Cache key elements
        filters_json = None if filters is None else filters.model_dump_json()
        options_json = None if options is None else options.model_dump_json()
        
        return self._search_cached(
            query,
            filters_json,
            options_json,
            self.base_url,
            json.dumps(self.headers)
        )
            
    @st.cache_data(ttl=300)
    def _search_cached(
        self,
        query: str,
        filters_json: Optional[str],
        options_json: Optional[str],
        base_url: str,
        headers_json: str
    ) -> Union[SearchResponse, ErrorResponse]:
        """Cached version of search query.
        
        Args:
            query: Search query text
            filters_json: JSON string of filters for caching
            options_json: JSON string of options for caching
            base_url: Base URL of the API
            headers_json: JSON string of headers for caching
            
        Returns:
            Response from the API
        """
        # API endpoint defined in frontend/api/routes.py
        url = f"{base_url}/search"
        headers = json.loads(headers_json)
        
        # Reconstruct request objects
        filters = None if filters_json is None else SearchFilters.model_validate_json(filters_json)
        options = None if options_json is None else SearchOptions.model_validate_json(options_json)
        
        search_request = SearchRequest(
            query=query,
            filters=filters,
            options=options
        )
        
        try:
            response = self.client.post(
                url, 
                headers=headers,
                content=search_request.model_dump_json()
            )
            
            if response.status_code == 200:
                return SearchResponse.model_validate(response.json())
            else:
                return ErrorResponse.model_validate(response.json())
                
        except httpx.RequestError as e:
            # Handle connection errors
            error_response = {
                "error": {
                    "code": "connection_error",
                    "message": f"Failed to connect to API: {str(e)}",
                    "details": {
                        "reason": "network_error"
                    }
                },
                "request_id": f"local_{int(time.time())}"
            }
            return ErrorResponse.model_validate(error_response)
    
    def get_suggestions(self, partial_query: str, limit: int = 5) -> Union[SuggestionsResponse, ErrorResponse]:
        """Get query suggestions based on a partial query.
        
        Args:
            partial_query: Partial query to get suggestions for
            limit: Maximum number of suggestions to return
            
        Returns:
            Response from the API as a SuggestionsResponse or ErrorResponse
        """
        return self._get_suggestions_cached(
            partial_query,
            limit,
            self.base_url,
            json.dumps(self.headers)
        )

    @st.cache_data(ttl=60)
    def _get_suggestions_cached(
        self,
        partial_query: str,
        limit: int,
        base_url: str,
        headers_json: str
    ) -> Union[SuggestionsResponse, ErrorResponse]:
        """Cached version of query suggestions.
        
        Args:
            partial_query: Partial query to get suggestions for
            limit: Maximum number of suggestions to return
            base_url: Base URL of the API
            headers_json: JSON string of headers for caching
            
        Returns:
            Response from the API
        """
        url = f"{base_url}/suggestions?partial_query={partial_query}&limit={limit}"
        headers = json.loads(headers_json)
        
        try:
            response = self.client.get(url, headers=headers)
            
            if response.status_code == 200:
                return SuggestionsResponse.model_validate(response.json())
            else:
                return ErrorResponse.model_validate(response.json())
                
        except httpx.RequestError as e:
            error_response = {
                "error": {
                    "code": "connection_error",
                    "message": f"Failed to connect to API: {str(e)}",
                    "details": {
                        "reason": "network_error"
                    }
                },
                "request_id": f"local_{int(time.time())}"
            }
            return ErrorResponse.model_validate(error_response)
    
    def submit_feedback(
        self, 
        request_id: str, 
        rating: str, 
        comments: Optional[str] = None,
        selected_sources: Optional[List[str]] = None,
        user_query_reformulation: Optional[str] = None
    ) -> Union[FeedbackResponse, ErrorResponse]:
        """Submit feedback for a search result.
        
        Args:
            request_id: ID of the search request
            rating: Rating (positive or negative)
            comments: Optional feedback comments
            selected_sources: Optional list of selected source document IDs
            user_query_reformulation: Optional user's query reformulation
            
        Returns:
            Response from the API as a FeedbackResponse or ErrorResponse
        """
        url = f"{self.base_url}/feedback"
        
        feedback_request = FeedbackRequest(
            request_id=request_id,
            rating=rating,
            comments=comments,
            selected_sources=selected_sources,
            user_query_reformulation=user_query_reformulation
        )
        
        try:
            response = self.client.post(
                url, 
                headers=self.headers,
                content=feedback_request.model_dump_json()
            )
            
            if response.status_code == 200:
                return FeedbackResponse.model_validate(response.json())
            else:
                return ErrorResponse.model_validate(response.json())
                
        except httpx.RequestError as e:
            error_response = {
                "error": {
                    "code": "connection_error",
                    "message": f"Failed to connect to API: {str(e)}",
                    "details": {
                        "reason": "network_error"
                    }
                },
                "request_id": f"local_{int(time.time())}"
            }
            return ErrorResponse.model_validate(error_response)
    
    def get_metadata_options(self) -> Union[MetadataOptionsResponse, ErrorResponse]:
        """Get available metadata options for filtering.
        
        Returns:
            Response from the API as a MetadataOptionsResponse or ErrorResponse
        """
        return self._get_metadata_options_cached(
            self.base_url, 
            json.dumps(self.headers)  # Convert headers to string for caching
        )
            
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def _get_metadata_options_cached(self, base_url: str, headers_json: str) -> Union[MetadataOptionsResponse, ErrorResponse]:
        """Cached version of metadata options retrieval.
        
        Args:
            base_url: Base URL of the API
            headers_json: JSON string of headers for caching
            
        Returns:
            Response from the API as a MetadataOptionsResponse or ErrorResponse
        """
        url = f"{base_url}/metadata/options"
        headers = json.loads(headers_json)
        
        try:
            response = self.client.get(url, headers=headers)
            
            if response.status_code == 200:
                return MetadataOptionsResponse.model_validate(response.json())
            else:
                return ErrorResponse.model_validate(response.json())
                
        except httpx.RequestError as e:
            error_response = {
                "error": {
                    "code": "connection_error",
                    "message": f"Failed to connect to API: {str(e)}",
                    "details": {
                        "reason": "network_error"
                    }
                },
                "request_id": f"local_{int(time.time())}"
            }
            return ErrorResponse.model_validate(error_response)
    
    def check_session_status(self) -> Union[SessionStatusResponse, ErrorResponse]:
        """Check status of the current session.
        
        Returns:
            Response from the API as a SessionStatusResponse or ErrorResponse
        """
        url = f"{self.base_url}/session/status"
        
        try:
            response = self.client.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return SessionStatusResponse.model_validate(response.json())
            else:
                return ErrorResponse.model_validate(response.json())
                
        except httpx.RequestError as e:
            error_response = {
                "error": {
                    "code": "connection_error",
                    "message": f"Failed to connect to API: {str(e)}",
                    "details": {
                        "reason": "network_error"
                    }
                },
                "request_id": f"local_{int(time.time())}"
            }
            return ErrorResponse.model_validate(error_response)
            
    def is_api_available(self) -> bool:
        """Check if the API is available.
        
        Returns:
            True if the API is available, False otherwise
        """
        try:
            # Use the correct health endpoint at /v1/health
            response = self.client.get(
                f"{self.base_url}/health", 
                timeout=5  # Short timeout for health check
            )
            return response.status_code == 200
        except Exception as e:
            # Try the explicit v1/health path
            try:
                response = self.client.get(
                    f"{self.base_url.split('/v1')[0]}/v1/health",
                    timeout=5
                )
                return response.status_code == 200
            except:
                # All attempts failed, but API could still be working (other endpoints)
                # Let's check a known working endpoint
                try:
                    response = self.client.get(
                        f"{self.base_url}/metadata/options",
                        headers=self.headers,
                        timeout=5
                    )
                    return response.status_code == 200
                except:
                    # All attempts failed
                    return False


# Create a singleton instance
api_client = APIClient()