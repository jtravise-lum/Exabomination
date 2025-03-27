"""Pydantic models for API requests and responses."""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class SearchFilters(BaseModel):
    """Filters for search queries."""
    
    document_types: Optional[List[str]] = Field(None, description="Document type filters")
    vendors: Optional[List[str]] = Field(None, description="Vendor filters")
    products: Optional[List[str]] = Field(None, description="Product filters")
    created_after: Optional[str] = Field(None, description="Filter for documents created after this date (ISO format)")
    created_before: Optional[str] = Field(None, description="Filter for documents created before this date (ISO format)")


class SearchOptions(BaseModel):
    """Options for search queries."""
    
    max_results: Optional[int] = Field(10, description="Maximum number of results to return")
    include_metadata: Optional[bool] = Field(True, description="Whether to include document metadata")
    rerank: Optional[bool] = Field(True, description="Whether to rerank results")
    threshold: Optional[float] = Field(0.7, description="Threshold for relevance")


class SearchRequest(BaseModel):
    """Search request model."""
    
    query: str = Field(..., description="Search query")
    filters: Optional[SearchFilters] = Field(None, description="Search filters")
    options: Optional[SearchOptions] = Field(None, description="Search options")


class DocumentMetadata(BaseModel):
    """Document metadata model."""
    
    document_type: Optional[str] = Field(None, description="Document type")
    vendor: Optional[str] = Field(None, description="Vendor")
    product: Optional[str] = Field(None, description="Product")
    created_at: Optional[str] = Field(None, description="Creation date")
    updated_at: Optional[str] = Field(None, description="Last update date")


class SourceDocument(BaseModel):
    """Source document model."""
    
    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    url: str = Field(..., description="Document URL")
    # Allow chunk_id to be either string or int since the API is returning integers
    chunk_id: Union[str, int] = Field(..., description="Chunk ID")
    content: str = Field(..., description="Document content")
    relevance_score: float = Field(..., description="Relevance score")
    metadata: DocumentMetadata = Field(..., description="Document metadata")
    
    # Model validators to ensure type consistency
    @field_validator('chunk_id')
    @classmethod
    def convert_chunk_id_to_str(cls, v):
        # Ensure chunk_id is always a string
        return str(v)


class SearchMetadata(BaseModel):
    """Metadata for search response."""
    
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    filter_count: int = Field(..., description="Number of filters applied")
    total_matches: int = Field(..., description="Total number of matches")
    threshold_applied: float = Field(..., description="Threshold applied")


class SearchResponse(BaseModel):
    """Search response model."""
    
    request_id: str = Field(..., description="Request ID")
    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="Generated answer")
    sources: List[SourceDocument] = Field(..., description="Source documents")
    suggested_queries: List[str] = Field(..., description="Suggested follow-up queries")
    metadata: SearchMetadata = Field(..., description="Response metadata")


class SuggestionsResponse(BaseModel):
    """Suggestions response model."""
    
    suggestions: List[str] = Field(..., description="Query suggestions")
    metadata: Dict[str, Any] = Field(..., description="Response metadata")


class FeedbackRequest(BaseModel):
    """Feedback request model."""
    
    request_id: str = Field(..., description="Request ID")
    rating: str = Field(..., description="Rating (positive or negative)")
    comments: Optional[str] = Field(None, description="Feedback comments")
    selected_sources: Optional[List[str]] = Field(None, description="Selected source document IDs")
    user_query_reformulation: Optional[str] = Field(None, description="User's query reformulation")


class FeedbackResponse(BaseModel):
    """Feedback response model."""
    
    status: str = Field(..., description="Status")
    feedback_id: str = Field(..., description="Feedback ID")
    message: str = Field(..., description="Response message")


class MetadataOptionsResponse(BaseModel):
    """Metadata options response model."""
    
    document_types: List[str] = Field(..., description="Available document types")
    vendors: List[str] = Field(..., description="Available vendors")
    products: Dict[str, List[str]] = Field(..., description="Available products by vendor")
    use_cases: List[str] = Field(..., description="Available use cases")
    date_range: Dict[str, str] = Field(..., description="Available date range")


class RateLimit(BaseModel):
    """Rate limit information model."""
    
    limit: int = Field(..., description="Rate limit (requests per minute)")
    remaining: int = Field(..., description="Remaining requests")
    reset_at: str = Field(..., description="Time when the rate limit resets")


class SessionStatusResponse(BaseModel):
    """Session status response model."""
    
    authenticated: bool = Field(..., description="Whether the user is authenticated")
    user_id: str = Field(..., description="User ID")
    session_expires_at: str = Field(..., description="Session expiration time")
    rate_limit: RateLimit = Field(..., description="Rate limit information")
    account_tier: str = Field(..., description="Account tier")
    features_enabled: List[str] = Field(..., description="Enabled features")


class ErrorDetail(BaseModel):
    """Error detail model."""
    
    parameter: Optional[str] = Field(None, description="Parameter that caused the error")
    reason: Optional[str] = Field(None, description="Reason for the error")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: Dict[str, Any] = Field(..., description="Error information")
    request_id: str = Field(..., description="Request ID")


class PaginationInfo(BaseModel):
    """Pagination information model."""
    
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Current offset")
    total: int = Field(..., description="Total items")
    next_offset: Optional[int] = Field(None, description="Next page offset")
    has_more: bool = Field(..., description="Whether there are more items")