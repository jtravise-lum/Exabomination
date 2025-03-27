"""Service layer for API endpoints."""

import logging
import time
import uuid
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from langchain.schema import Document

from src.data_processing.vector_store import VectorDatabase
from src.llm_integration.query_engine import QueryEngine
from src.retrieval.retriever import Retriever
from src.retrieval.query_processor import QueryProcessor
from src.retrieval.reranker import Reranker
from src.data_processing.embeddings import MultiModalEmbeddingProvider
from src.config import TOP_K_RETRIEVAL

logger = logging.getLogger(__name__)

# In-memory storage for feedback and query history
feedback_storage = {}
query_history = {}

# List of common follow-up queries by topic to suggest to users
COMMON_FOLLOWUPS = {
    "authentication": [
        "How do I configure SAML authentication?",
        "What are the requirements for implementing OAuth?",
        "How does Exabeam handle multi-factor authentication?",
        "What are the best practices for SSO implementation?"
    ],
    "detection rules": [
        "How do I create a custom detection rule?",
        "What are the components of a detection rule?",
        "How do I test a detection rule before deploying?",
        "What are the most effective detection rules for privilege escalation?"
    ],
    "data sources": [
        "How do I add a new data source?",
        "What are the supported data formats?",
        "How do I troubleshoot data ingestion issues?",
        "What are the requirements for adding a cloud data source?"
    ],
    "parsers": [
        "How do I create a custom parser?",
        "What is the parser validation process?",
        "How do I troubleshoot a parser that isn't working?",
        "What are the best practices for parser optimization?"
    ],
    "security": [
        "What are the security features in Exabeam?",
        "How does Exabeam detect lateral movement?",
        "What detection capabilities exist for data exfiltration?",
        "How does Exabeam detect account takeover attempts?"
    ]
}


class ExasperationService:
    """Service class for EXASPERATION API endpoints."""
    
    def __init__(self, query_engine: Optional[QueryEngine] = None):
        """Initialize the service.
        
        Args:
            query_engine: Optional query engine instance
        """
        self.query_engine = query_engine
        
        if not self.query_engine:
            # Initialize dependencies for query engine
            logger.info("Initializing new query engine")
            try:
                self._initialize_query_engine()
            except Exception as e:
                logger.error(f"Failed to initialize query engine: {str(e)}")
                self.query_engine = None
                
        logger.info("Service initialized")
    
    def _initialize_query_engine(self):
        """Initialize the query engine and its dependencies."""
        from src.data_processing.vector_store import get_vector_store
        
        # Get vector store
        vector_store = get_vector_store()
        
        # Initialize embedding provider
        embedding_provider = MultiModalEmbeddingProvider()
        
        # Initialize query processor
        query_processor = QueryProcessor(embedding_provider=embedding_provider)
        
        # Initialize retriever (without reranker for now)
        retriever = Retriever(
            vector_db=vector_store,
            query_processor=query_processor,
            embedding_provider=embedding_provider,
            top_k=TOP_K_RETRIEVAL
        )
        
        # Try to initialize reranker if available
        try:
            from src.retrieval.reranker import Reranker
            reranker = Reranker()
            retriever.reranker = reranker
            logger.info("Initialized reranker")
        except Exception as e:
            logger.warning(f"Failed to initialize reranker: {str(e)}")
            
        # Initialize query engine
        self.query_engine = QueryEngine(retriever=retriever)
    
    async def process_search_query(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
        user_id: str = "anonymous"
    ) -> Dict[str, Any]:
        """Process a search query.
        
        Args:
            query: User query
            filters: Optional metadata filters
            options: Optional search options
            user_id: User ID for logging
            
        Returns:
            Search response
        """
        start_time = time.time()
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        logger.info(f"Processing search query: '{query}' (request_id: {request_id})")
        
        if not self.query_engine:
            logger.error("Query engine not initialized")
            return self._create_error_response(
                request_id=request_id,
                query=query,
                error_code="service_unavailable",
                error_message="Search service is currently unavailable. Please try again later."
            )
        
        # Default options
        options = options or {}
        max_results = options.get("max_results", 10)
        include_metadata = options.get("include_metadata", True)
        rerank = options.get("rerank", True)
        threshold = options.get("threshold", 0.7)
        
        # Convert filters to backend format if present
        backend_filters = None
        if filters:
            backend_filters = {}
            if filters.get("document_types"):
                backend_filters["doc_type"] = {"$in": filters["document_types"]}
            if filters.get("vendors"):
                backend_filters["vendor"] = {"$in": filters["vendors"]}
            if filters.get("products"):
                backend_filters["product"] = {"$in": filters["products"]}
            if filters.get("created_after"):
                backend_filters["created_at"] = {"$gte": filters["created_after"]}
            if filters.get("created_before"):
                backend_filters["created_at"] = {"$lte": filters["created_before"]}
        
        # Process query with query engine
        try:
            result = self.query_engine.process_query(
                query=query,
                filter=backend_filters,
                temperature=0.2,  # Low temperature for accuracy
                use_cache=True
            )
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return self._create_error_response(
                request_id=request_id,
                query=query,
                error_code="query_processing_error",
                error_message="An error occurred while processing your query."
            )
        
        # Extract documents and ensure they're limited to max_results
        documents = result.get("documents", [])[:max_results]
        
        # Generate suggested follow-up queries
        suggested_queries = self._generate_suggested_queries(query, documents)
        
        # Save to query history
        self._save_to_query_history(user_id, request_id, query, documents)
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Format response
        sources = []
        for i, doc in enumerate(documents):
            # Extract metadata
            metadata = doc.get("metadata", {})
            
            # Create source document entry
            source = {
                "id": metadata.get("doc_id", f"doc_{i}"),
                "title": metadata.get("title", "Untitled Document"),
                "url": metadata.get("url", metadata.get("source", "#")),
                "chunk_id": metadata.get("chunk_id", f"chunk_{i}"),
                "content": doc.get("content", ""),
                "relevance_score": 1.0 - (i * 0.05),  # Simple decreasing score
                "metadata": {
                    "document_type": metadata.get("doc_type", "unknown"),
                    "vendor": metadata.get("vendor", ""),
                    "product": metadata.get("product", ""),
                    "created_at": metadata.get("created_at", ""),
                    "updated_at": metadata.get("updated_at", "")
                }
            }
            sources.append(source)
        
        # Create response
        response = {
            "request_id": request_id,
            "query": query,
            "answer": result.get("answer", "No results found for your query."),
            "sources": sources,
            "suggested_queries": suggested_queries,
            "metadata": {
                "processing_time_ms": processing_time_ms,
                "filter_count": len(backend_filters) if backend_filters else 0,
                "total_matches": len(result.get("documents", [])),
                "threshold_applied": threshold
            }
        }
        
        logger.info(f"Query processed in {processing_time_ms}ms: '{query}'")
        return response

    def _create_error_response(
        self,
        request_id: str,
        query: str,
        error_code: str,
        error_message: str
    ) -> Dict[str, Any]:
        """Create an error response for search queries.
        
        Args:
            request_id: Request ID
            query: Original query
            error_code: Error code
            error_message: Error message
            
        Returns:
            Formatted error response
        """
        return {
            "request_id": request_id,
            "query": query,
            "answer": f"Error: {error_message}",
            "sources": [],
            "suggested_queries": [],
            "metadata": {
                "processing_time_ms": 0,
                "filter_count": 0,
                "total_matches": 0,
                "threshold_applied": 0.0,
                "error": {
                    "code": error_code,
                    "message": error_message
                }
            }
        }
    
    def _generate_suggested_queries(self, query: str, documents: List[Dict]) -> List[str]:
        """Generate suggested follow-up queries based on the original query and results.
        
        Args:
            query: Original query
            documents: Retrieved documents
            
        Returns:
            List of suggested follow-up queries
        """
        # Identify which category the query might belong to
        query_lower = query.lower()
        
        # Check for keywords to identify category
        category = None
        if any(word in query_lower for word in ["login", "sso", "saml", "oauth", "mfa", "authenticate"]):
            category = "authentication"
        elif any(word in query_lower for word in ["rule", "detection", "alert", "trigger", "correlation"]):
            category = "detection rules"
        elif any(word in query_lower for word in ["source", "ingest", "data", "format", "input"]):
            category = "data sources"
        elif any(word in query_lower for word in ["parse", "parser", "extract", "field", "normalize"]):
            category = "parsers"
        elif any(word in query_lower for word in ["secure", "threat", "attack", "lateral", "exfiltration"]):
            category = "security"
        
        # Get suggestions for category or default to empty list
        suggestions = COMMON_FOLLOWUPS.get(category, [])
        
        # If we couldn't identify a category, pick some general suggestions
        if not suggestions:
            # Pick one from each category as a generic set
            suggestions = [
                COMMON_FOLLOWUPS["authentication"][0],
                COMMON_FOLLOWUPS["detection rules"][0],
                COMMON_FOLLOWUPS["data sources"][0]
            ]
        
        # Return up to 3 suggestions
        return suggestions[:3]
    
    def _save_to_query_history(
        self,
        user_id: str,
        request_id: str,
        query: str,
        documents: List[Dict]
    ):
        """Save query to history.
        
        Args:
            user_id: User ID
            request_id: Request ID
            query: Query string
            documents: Retrieved documents
        """
        # Initialize user history if not exists
        if user_id not in query_history:
            query_history[user_id] = []
        
        # Create history entry
        history_entry = {
            "request_id": request_id,
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "doc_count": len(documents)
        }
        
        # Add to history (newest first)
        query_history[user_id].insert(0, history_entry)
        
        # Limit history size
        if len(query_history[user_id]) > 100:
            query_history[user_id] = query_history[user_id][:100]
    
    async def get_query_suggestions(
        self,
        partial_query: str,
        limit: int = 5
    ) -> List[str]:
        """Get query suggestions for a partial query.
        
        Args:
            partial_query: Partial query text
            limit: Maximum number of suggestions
            
        Returns:
            List of query suggestions
        """
        logger.info(f"Getting suggestions for partial query: '{partial_query}'")
        
        # Simple implementation - in a real system, this would use a proper suggestion engine
        # or be based on frequent queries in the system
        
        # Hard-coded suggestions by prefix
        suggestion_prefixes = {
            "how": [
                "How do I configure SAML authentication?",
                "How do I create a custom parser?",
                "How do I add a new data source?",
                "How does the password reset detection rule work?",
                "How can I optimize query performance?",
                "How do I set up the Okta integration?",
                "How does lateral movement detection work?",
                "How do I troubleshoot data lake connectivity issues?"
            ],
            "what": [
                "What are the components of a detection rule?",
                "What is the parser validation process?",
                "What detection capabilities exist for data exfiltration?",
                "What are the supported data formats?",
                "What are the security features in Exabeam?",
                "What are the best practices for SSO implementation?",
                "What events are generated during a password reset?"
            ],
            "where": [
                "Where can I find documentation on data sources?",
                "Where are detection rules stored?",
                "Where should I look for audit logs?",
                "Where can I configure authentication settings?"
            ],
            "can": [
                "Can Exabeam integrate with Splunk?",
                "Can I create custom dashboards?",
                "Can detection rules be exported?",
                "Can data be encrypted at rest?"
            ]
        }
        
        # Default suggestions if nothing matches
        default_suggestions = [
            "How does Exabeam detect threats?",
            "What are the components of Advanced Analytics?",
            "How do I create a custom parser?",
            "What are the best practices for deploying Exabeam?",
            "How can I optimize query performance?"
        ]
        
        # Get first word of query to match against prefixes
        first_word = partial_query.split()[0].lower() if partial_query else ""
        
        # Get suggestions based on prefix
        all_suggestions = suggestion_prefixes.get(first_word, default_suggestions)
        
        # Filter based on partial query
        if partial_query:
            matching_suggestions = [
                s for s in all_suggestions 
                if s.lower().startswith(partial_query.lower())
            ]
            
            # If no exact matches, try contains
            if not matching_suggestions:
                matching_suggestions = [
                    s for s in all_suggestions 
                    if partial_query.lower() in s.lower()
                ]
        else:
            matching_suggestions = all_suggestions
        
        # Return limited results
        return matching_suggestions[:limit]
    
    async def submit_feedback(
        self,
        request_id: str,
        rating: str,
        comments: Optional[str] = None,
        selected_sources: Optional[List[str]] = None,
        user_query_reformulation: Optional[str] = None,
        user_id: str = "anonymous"
    ) -> Dict[str, Any]:
        """Submit feedback for a search result.
        
        Args:
            request_id: Request ID
            rating: Feedback rating ("positive" or "negative")
            comments: Optional feedback comments
            selected_sources: Optional list of selected source document IDs
            user_query_reformulation: Optional user query reformulation
            user_id: User ID
            
        Returns:
            Feedback response
        """
        logger.info(f"Submitting feedback for request {request_id}: {rating}")
        
        # Generate feedback ID
        feedback_id = f"fb_{uuid.uuid4().hex[:12]}"
        
        # Create feedback entry
        feedback_entry = {
            "feedback_id": feedback_id,
            "request_id": request_id,
            "user_id": user_id,
            "rating": rating,
            "comments": comments,
            "selected_sources": selected_sources,
            "user_query_reformulation": user_query_reformulation,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store feedback
        feedback_storage[feedback_id] = feedback_entry
        
        # Return response
        return {
            "status": "success",
            "feedback_id": feedback_id,
            "message": "Thank you for your feedback!"
        }
    
    async def get_metadata_options(self) -> Dict[str, Any]:
        """Get available metadata options for filtering.
        
        Returns:
            Metadata options
        """
        logger.info("Getting metadata options")
        
        # In a real implementation, this would query the database
        # For now, return hardcoded values from the API contract
        
        return {
            "document_types": [
                "use_case",
                "parser",
                "rule",
                "data_source",
                "overview",
                "tutorial"
            ],
            "vendors": [
                "microsoft",
                "cisco",
                "okta",
                "palo_alto",
                "aws"
            ],
            "products": {
                "microsoft": [
                    "active_directory",
                    "azure_ad",
                    "exchange_online",
                    "windows"
                ],
                "cisco": [
                    "asa",
                    "firepower",
                    "ise",
                    "meraki"
                ],
                "okta": [
                    "identity_cloud"
                ]
            },
            "use_cases": [
                "account_takeover",
                "data_exfiltration",
                "lateral_movement",
                "privilege_escalation"
            ],
            "date_range": {
                "oldest": "2022-01-15",
                "newest": "2025-03-27"
            }
        }