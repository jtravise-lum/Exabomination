"""Retrieval module for finding relevant documents for a query."""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple, Set, Union
from collections import defaultdict, Counter

from langchain.schema import Document

from src.config import TOP_K_RETRIEVAL, RERANKER_THRESHOLD
from src.data_processing.vector_store import VectorDatabase
from src.data_processing.embeddings import MultiModalEmbeddingProvider
from src.retrieval.query_processor import QueryProcessor
from src.retrieval.reranker import Reranker

logger = logging.getLogger(__name__)


class Retriever:
    """Handles retrieval of relevant documents for a query.
    
    This class implements:
    1. Hybrid search (vector + keyword)
    2. Metadata-based filtering
    3. Context assembly with proper citations
    4. Result diversification
    5. Fallback strategies for failed queries
    """
    
    def _normalize_filter(self, filter_dict: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Normalize filter dictionary to be compatible with ChromaDB.
        
        Args:
            filter_dict: The filter dictionary to normalize
            
        Returns:
            Normalized filter dictionary or None
        """
        if not filter_dict:
            return None
            
        # For empty filters, return None to avoid ChromaDB errors
        if not any(filter_dict.values()):
            return None
            
        # For ChromaDB compatibility, we need to convert the filter format
        normalized = {}
        
        # Process each filter type
        for key, value in filter_dict.items():
            if isinstance(value, dict) and "$in" in value:
                # Convert $in operator to ChromaDB's format
                if value["$in"]:  # Only add if the list is not empty
                    normalized[key] = {"$in": value["$in"]}
            elif isinstance(value, dict) and ("$gte" in value or "$lte" in value):
                # For date ranges, handle differently
                condition = {}
                if "$gte" in value:
                    condition["$gte"] = value["$gte"]
                if "$lte" in value:
                    condition["$lte"] = value["$lte"]
                normalized[key] = condition
            elif value:  # Only add non-empty values
                normalized[key] = value
                
        # Return None if no valid filters remain
        return normalized if normalized else None

    def __init__(
        self,
        vector_db: VectorDatabase,
        query_processor: Optional[QueryProcessor] = None,
        embedding_provider: Optional[MultiModalEmbeddingProvider] = None,
        reranker: Optional[Reranker] = None,
        top_k: int = TOP_K_RETRIEVAL,
        rerank_threshold: float = RERANKER_THRESHOLD,
        hybrid_search_weight: float = 0.7,
        enable_hybrid_search: bool = True
    ):
        """Initialize the retriever.

        Args:
            vector_db: Vector database for similarity search
            query_processor: Optional query processor for query enhancement
            embedding_provider: Optional embedding provider for query embeddings
            reranker: Optional reranker for improving search results
            top_k: Number of documents to retrieve
            rerank_threshold: Threshold for reranker relevance
            hybrid_search_weight: Weight to balance vector (default) vs keyword search (0-1)
            enable_hybrid_search: Whether to use hybrid search or vector-only
        """
        self.vector_db = vector_db
        self.embedding_provider = embedding_provider or MultiModalEmbeddingProvider()
        self.query_processor = query_processor or QueryProcessor(embedding_provider=self.embedding_provider)
        self.reranker = reranker
        self.top_k = top_k
        self.rerank_threshold = rerank_threshold
        self.hybrid_search_weight = hybrid_search_weight
        self.enable_hybrid_search = enable_hybrid_search
        
        # Initialize result cache for frequently queried terms
        self._result_cache = {}
        self._cache_max_size = 100
        
        logger.info(f"Initialized retriever with top_k={top_k}, hybrid_weight={hybrid_search_weight}")

    def retrieve(self, query: str, filter: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Retrieve relevant documents for a query using hybrid search.

        Args:
            query: The search query
            filter: Optional metadata filters

        Returns:
            List of relevant documents
        """
        if not query or not query.strip():
            logger.warning("Empty query received")
            return []

        # Check cache first (only if filters are not applied)
        cache_key = f"{query}_{str(filter)}"
        if cache_key in self._result_cache:
            logger.info(f"Using cached results for query: {query}")
            return self._result_cache[cache_key]

        # Process the query and extract metadata filters
        processed_query = self.query_processor.process_query(query)
        logger.info(f"Processed query: {processed_query}")
        
        # Extract any metadata filters from the query itself
        _, query_filters = self.query_processor.extract_metadata_filters(query)
        
        # Combine explicit filters with those extracted from the query
        combined_filter = filter or {}
        combined_filter.update(query_filters)
        
        # Determine query type for embedding model selection
        query_type = self.query_processor.detect_query_type(query)
        
        # Hybrid search
        if self.enable_hybrid_search:
            results = self._hybrid_search(processed_query, query_type, combined_filter)
        else:
            # Vector-only search
            results = self._vector_search(processed_query, query_type, combined_filter)
            
        # If no results, try fallback strategies
        if not results:
            logger.warning(f"No results found for '{query}', trying fallback strategies")
            results = self._fallback_search(query, processed_query, query_type, combined_filter)

        # Ensure we have diverse results
        if results:
            results = self._diversify_results(results)

        # If reranker is available, apply it
        if self.reranker and len(results) > 1:
            reranked_docs = self.reranker.rerank(query, results, threshold=self.rerank_threshold)
            logger.info(f"Reranked documents, kept {len(reranked_docs)} above threshold")
            
            # If we have enough reranked documents, use them; otherwise use original results
            if len(reranked_docs) >= min(3, self.top_k):
                results = reranked_docs

        # Limit to top_k
        results = results[:self.top_k]
        
        # Cache results if we have any (and there's no complex filter)
        if results and not combined_filter:
            # Manage cache size
            if len(self._result_cache) >= self._cache_max_size:
                # Remove a random entry if cache is full
                self._result_cache.pop(next(iter(self._result_cache)))
            
            self._result_cache[cache_key] = results

        return results

    def _vector_search(
        self, 
        query: str, 
        query_type: str, 
        filter: Optional[Dict[str, Any]] = None,
        k: Optional[int] = None
    ) -> List[Document]:
        """Perform vector search using appropriate embedding model.
        
        Args:
            query: Processed query text
            query_type: Type of query ('text' or 'code')
            filter: Optional metadata filters
            k: Number of results to retrieve (defaults to self.top_k)
            
        Returns:
            List of relevant documents
        """
        # Get query embedding using the appropriate model
        query_embedding = self.query_processor.embed_query(query)
        
        # If k is not provided, use top_k * 2 to allow for post-processing
        search_k = k or (self.top_k * 2)
        
        # Perform vector search
        try:
            # Normalize filter for compatibility with ChromaDB
            normalized_filter = self._normalize_filter(filter)
            
            # Compatibility with different VectorDatabase implementations
            if hasattr(self.vector_db, 'similarity_search_by_vector'):
                results = self.vector_db.similarity_search_by_vector(
                    embedding=query_embedding,
                    k=search_k,
                    filter=normalized_filter
                )
            else:
                # Fallback to standard similarity search
                results = self.vector_db.similarity_search(
                    query=query,
                    k=search_k, 
                    filter=normalized_filter,
                    query_type=query_type
                )
            logger.info(f"Vector search found {len(results)} documents")
            return results
        except Exception as e:
            logger.error(f"Error in vector search: {str(e)}")
            return []

    def _keyword_search(
        self, 
        query: str, 
        filter: Optional[Dict[str, Any]] = None,
        k: Optional[int] = None
    ) -> List[Document]:
        """Perform keyword-based search.
        
        Args:
            query: Processed query text
            filter: Optional metadata filters
            k: Number of results to retrieve
            
        Returns:
            List of relevant documents
        """
        # Extract keywords for search
        keywords = self.query_processor.extract_keywords(query)
        
        # If k is not provided, use top_k * 2 to allow for post-processing
        search_k = k or (self.top_k * 2)
        
        # If we have at least one keyword, perform keyword search
        if keywords:
            keyword_query = " ".join(keywords)
            try:
                # Normalize filter for compatibility with ChromaDB
                normalized_filter = self._normalize_filter(filter)
                
                # Compatibility with different VectorDatabase implementations
                if hasattr(self.vector_db, 'keyword_search'):
                    results = self.vector_db.keyword_search(
                        query=keyword_query,
                        k=search_k,
                        filter=normalized_filter
                    )
                else:
                    # Fallback to standard similarity search
                    results = self.vector_db.similarity_search(
                        query=keyword_query,
                        k=search_k,
                        filter=normalized_filter
                    )
                logger.info(f"Keyword search found {len(results)} documents")
                return results
            except Exception as e:
                logger.error(f"Error in keyword search: {str(e)}")
                return []
        
        # No keywords available
        return []

    def _hybrid_search(
        self, 
        query: str, 
        query_type: str,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Combine vector and keyword search for improved results.
        
        Args:
            query: Processed query text
            query_type: Type of query ('text' or 'code')
            filter: Optional metadata filters
            
        Returns:
            List of relevant documents
        """
        # Get vector search results
        vector_results = self._vector_search(query, query_type, filter, k=self.top_k * 2)
        
        # Get keyword search results
        keyword_results = self._keyword_search(query, filter, k=self.top_k * 2)
        
        # Combine results with weighting
        if vector_results and keyword_results:
            # Create a map of document ID to document and score
            combined_docs = {}
            
            # Add vector results with vector weight
            for i, doc in enumerate(vector_results):
                # Calculate a score based on position (higher = better)
                vector_score = (len(vector_results) - i) / len(vector_results)
                doc_id = doc.metadata.get("chunk_id", f"vector_{i}")
                
                combined_docs[doc_id] = {
                    "document": doc,
                    "score": vector_score * self.hybrid_search_weight,
                    "vector_rank": i
                }
            
            # Add keyword results with keyword weight
            for i, doc in enumerate(keyword_results):
                # Calculate a score based on position (higher = better)
                keyword_score = (len(keyword_results) - i) / len(keyword_results)
                doc_id = doc.metadata.get("chunk_id", f"keyword_{i}")
                
                # If document already exists, update score
                if doc_id in combined_docs:
                    combined_docs[doc_id]["score"] += keyword_score * (1 - self.hybrid_search_weight)
                    combined_docs[doc_id]["keyword_rank"] = i
                else:
                    combined_docs[doc_id] = {
                        "document": doc,
                        "score": keyword_score * (1 - self.hybrid_search_weight),
                        "keyword_rank": i
                    }
            
            # Sort by combined score and extract documents
            ranked_results = sorted(combined_docs.values(), key=lambda x: x["score"], reverse=True)
            hybrid_results = [item["document"] for item in ranked_results]
            
            logger.info(f"Hybrid search combined {len(vector_results)} vector and {len(keyword_results)} keyword results into {len(hybrid_results)} documents")
            return hybrid_results
            
        # If one search type failed, return the other
        if vector_results:
            return vector_results
        return keyword_results

    def _fallback_search(
        self, 
        original_query: str,
        processed_query: str,
        query_type: str,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Implement fallback strategies when main search returns no results.
        
        Args:
            original_query: The original query text
            processed_query: The processed query text
            query_type: Type of query ('text' or 'code')
            filter: Optional metadata filters
            
        Returns:
            List of relevant documents from fallback strategies
        """
        # Strategy 1: Try with expanded queries
        expanded_queries = self.query_processor.expand_query(original_query)
        for expanded_query in expanded_queries:
            if expanded_query != processed_query:  # Skip if it's the same as the already tried query
                logger.info(f"Fallback: Trying expanded query: {expanded_query}")
                fallback_results = self._vector_search(expanded_query, query_type, filter)
                if fallback_results:
                    return fallback_results
        
        # Strategy 2: Try with relaxed filters
        if filter:
            logger.info(f"Fallback: Trying search without filters")
            fallback_results = self._vector_search(processed_query, query_type, filter=None)
            if fallback_results:
                return fallback_results
        
        # Strategy 3: Try keyword search if hybrid was not enabled
        if not self.enable_hybrid_search:
            logger.info(f"Fallback: Trying keyword search")
            fallback_results = self._keyword_search(processed_query, filter=None)
            if fallback_results:
                return fallback_results
        
        # Strategy 4: Try more general search with just important keywords
        keywords = self.query_processor.extract_keywords(original_query)
        if len(keywords) > 1:
            # Try with just the top 2 keywords
            simplified_query = " ".join(keywords[:2])
            logger.info(f"Fallback: Trying simplified query: {simplified_query}")
            fallback_results = self._vector_search(simplified_query, query_type, filter=None)
            if fallback_results:
                return fallback_results
        
        logger.warning("All fallback strategies failed to find results")
        return []

    def _diversify_results(self, documents: List[Document]) -> List[Document]:
        """Ensure diversity in the results by considering content and metadata.
        
        Args:
            documents: List of retrieved documents
            
        Returns:
            List of diversified documents
        """
        if not documents or len(documents) <= 3:
            return documents
            
        # Count document types
        doc_types = Counter([doc.metadata.get("doc_type", "unknown") for doc in documents])
        source_files = Counter([doc.metadata.get("file_name", "unknown") for doc in documents])
        
        # If we have too many documents of the same type or from the same file,
        # try to diversify by taking a mix of different types/sources
        diversified = []
        included_files = set()
        included_types = set()
        
        # First pass: include varied document types and sources
        for doc in documents:
            doc_type = doc.metadata.get("doc_type", "unknown")
            file_name = doc.metadata.get("file_name", "unknown")
            
            # If we already have many documents of this type/file, skip for now
            if (doc_type in included_types and len([d for d in diversified if d.metadata.get("doc_type") == doc_type]) >= 2 and
                file_name in included_files and len([d for d in diversified if d.metadata.get("file_name") == file_name]) >= 2):
                continue
                
            diversified.append(doc)
            included_files.add(file_name)
            included_types.add(doc_type)
            
            # If we have enough diversified documents, stop
            if len(diversified) >= self.top_k:
                break
                
        # Second pass: fill up to top_k with remaining documents
        if len(diversified) < self.top_k:
            for doc in documents:
                if doc not in diversified:
                    diversified.append(doc)
                    if len(diversified) >= self.top_k:
                        break
        
        return diversified

    def retrieve_with_scores(
        self, query: str, filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """Retrieve relevant documents with similarity scores.

        Args:
            query: The search query
            filter: Optional metadata filters

        Returns:
            List of (document, score) tuples
        """
        if not query or not query.strip():
            logger.warning("Empty query received")
            return []
            
        # Process the query and extract metadata filters
        processed_query = self.query_processor.process_query(query)
        
        # Extract any metadata filters from the query itself
        _, query_filters = self.query_processor.extract_metadata_filters(query)
        
        # Combine explicit filters with those extracted from the query
        combined_filter = filter or {}
        combined_filter.update(query_filters)
        
        # Get query embedding
        query_embedding = self.query_processor.embed_query(processed_query)
        
        # Perform similarity search with scores
        try:
            # Normalize filter for compatibility with ChromaDB
            normalized_filter = self._normalize_filter(combined_filter)
            
            # Compatibility with different VectorDatabase implementations
            if hasattr(self.vector_db, 'similarity_search_by_vector_with_score'):
                retrieved_docs = self.vector_db.similarity_search_by_vector_with_score(
                    embedding=query_embedding,
                    k=self.top_k,
                    filter=normalized_filter
                )
            else:
                # Fallback to standard similarity search with score
                retrieved_docs = self.vector_db.similarity_search_with_score(
                    query=processed_query,
                    k=self.top_k,
                    filter=normalized_filter,
                    query_type=self.query_processor.detect_query_type(query)
                )
            
            logger.info(f"Retrieved {len(retrieved_docs)} scored documents from vector database")
            return retrieved_docs
        except Exception as e:
            logger.error(f"Error in similarity search with scores: {str(e)}")
            return []

    def assemble_context(self, documents: List[Document], max_tokens: int = 4000) -> str:
        """Assemble retrieved documents into a context string for the LLM.

        Args:
            documents: List of retrieved documents
            max_tokens: Maximum number of tokens for the assembled context

        Returns:
            Assembled context string
        """
        if not documents:
            return ""

        context_parts = []
        total_length = 0
        char_to_token_ratio = 4  # Approximate ratio of characters to tokens
        max_chars = max_tokens * char_to_token_ratio

        for i, doc in enumerate(documents, 1):
            # Extract metadata for rich context
            source = doc.metadata.get("source", "Unknown source")
            doc_type = doc.metadata.get("doc_type", "")
            vendor = doc.metadata.get("vendor", "")
            product = doc.metadata.get("product", "")
            use_case = doc.metadata.get("use_case", "")
            
            # Build citation string with available metadata
            citation_parts = [f"Source: {source}"]
            if doc_type:
                citation_parts.append(f"Type: {doc_type}")
            if vendor:
                citation_parts.append(f"Vendor: {vendor}")
            if product:
                citation_parts.append(f"Product: {product}")
            if use_case:
                citation_parts.append(f"Use case: {use_case}")
                
            citation = ", ".join(citation_parts)
            
            # Format the document with citation
            content = f"Document {i} ({citation}):\n{doc.page_content}\n"
            
            # Check if adding this document would exceed the token limit
            if total_length + len(content) > max_chars:
                # If we're about to exceed the limit, add a note and stop
                context_parts.append(f"\n[Note: Additional {len(documents) - i + 1} documents omitted due to context length limitations]")
                break
                
            context_parts.append(content)
            total_length += len(content)

        return "\n\n".join(context_parts)
