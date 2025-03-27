"""Reranking module for improving search result relevance."""

import logging
import os
import re
import time
import json
from typing import List, Dict, Any, Optional, Tuple, Union, Set
from collections import defaultdict

import requests
from langchain.schema import Document

logger = logging.getLogger(__name__)


class Reranker:
    """Reranks and filters retrieved documents by relevance.
    
    This class implements:
    1. Integration with external reranking APIs
    2. Relevance threshold filtering
    3. Query-document relevance scoring
    4. Result diversification strategies
    5. Citation extraction for proper attribution
    """

    def __init__(
        self, 
        provider: str = "anthropic",  # Options: "anthropic", "openai", "voyage", "heuristic"
        api_base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        cache_size: int = 100
    ):
        """Initialize the reranker.

        Args:
            provider: The API provider to use for reranking ("anthropic", "openai", "voyage", "heuristic")
            api_base_url: Optional API endpoint for hosted reranker
            api_key: Optional API key for the reranking service
            cache_size: Maximum number of query-document pairs to cache
        """
        self.provider = provider.lower()
        self.api_base_url = api_base_url
        
        # Initialize API keys from environment if not provided
        if api_key:
            self.api_key = api_key
        else:
            if self.provider == "anthropic":
                self.api_key = os.environ.get("ANTHROPIC_API_KEY")
            elif self.provider == "openai":
                self.api_key = os.environ.get("OPENAI_API_KEY")
            elif self.provider == "voyage":
                self.api_key = os.environ.get("VOYAGE_API_KEY")
            else:
                self.api_key = None
        
        # Initialize cache for repeated query-document pairs
        self._scores_cache = {}
        self._cache_size = cache_size
        
        logger.info(f"Initialized reranker with provider: {self.provider}")
        
        # Heuristic scoring patterns (used as fallback or if provider is "heuristic")
        self._init_scoring_patterns()
        
    def _init_scoring_patterns(self):
        """Initialize patterns for heuristic scoring when model is unavailable."""
        # Keywords that indicate high relevance
        self.relevance_keywords = {
            "definition": 3.0,
            "example": 2.5,
            "implementation": 2.0,
            "configuration": 2.0,
            "explanation": 2.0,
            "overview": 1.5,
            "summary": 1.5,
            "guide": 1.5,
            "tutorial": 1.5,
            "setup": 1.5,
            "syntax": 1.5,
            "reference": 1.0,
            "details": 1.0
        }
        
        # Document type ranking factors (higher = more relevant)
        self.doc_type_weights = {
            "overview": 1.5,
            "parser": 1.2,
            "rule": 1.2,
            "model": 1.2,
            "use_case": 1.3,
            "data_source": 1.1,
            "reference": 0.9
        }

    def compute_api_scores(
        self, query: str, documents: List[Document]
    ) -> List[Tuple[Document, float]]:
        """Compute relevance scores using the configured API provider.
        
        Args:
            query: The search query
            documents: List of documents to score
            
        Returns:
            List of (document, score) tuples
        """
        if not documents:
            return []
            
        # Check if we have a valid provider and API key
        if self.provider not in ["anthropic", "openai", "voyage"] or not self.api_key:
            logger.warning(f"Invalid provider '{self.provider}' or missing API key, falling back to heuristic scoring")
            return self.compute_heuristic_scores(query, documents)
            
        # For large document sets, batching is more efficient
        if len(documents) > 10:
            return self._batch_score_documents(query, documents)
            
        # Create query-document pairs
        pairs = [(query, doc.page_content) for doc in documents]
        
        try:
            if self.provider == "anthropic":
                return self._score_with_anthropic(query, documents)
            elif self.provider == "openai":
                return self._score_with_openai(query, documents)
            elif self.provider == "voyage":
                return self._score_with_voyage(query, documents)
        except Exception as e:
            logger.error(f"Error computing API scores with {self.provider}: {str(e)}")
            logger.info("Falling back to heuristic scoring")
                
        # If API scoring fails, fall back to heuristic scoring
        return self.compute_heuristic_scores(query, documents)
        
    def _score_with_anthropic(self, query: str, documents: List[Document]) -> List[Tuple[Document, float]]:
        """Use Anthropic Claude to score documents.
        
        Args:
            query: The search query
            documents: List of documents to score
            
        Returns:
            List of (document, score) tuples
        """
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            # For each document, ask Claude to rate relevance from 0-100
            scored_docs = []
            
            for i, doc in enumerate(documents):
                cache_key = f"{query}_{hash(doc.page_content)}"
                if cache_key in self._scores_cache:
                    scored_docs.append((doc, self._scores_cache[cache_key]))
                    continue
                    
                prompt = f"""
                <instruction>
                Rate how relevant the document is to the query. Return ONLY a number between 0 and 100, where:
                - 0 means completely irrelevant
                - 100 means perfect match answering the query completely
                
                Query: "{query}"
                
                Document:
                {doc.page_content}
                </instruction>
                """
                
                response = client.messages.create(
                    model="claude-3-haiku-20240307",  # Use smallest, fastest model for efficiency
                    max_tokens=5,
                    temperature=0,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                try:
                    # Extract score from response
                    score_text = response.content[0].text.strip()
                    score = float(score_text) / 100.0  # Normalize to 0-1
                    
                    # Cap score at 1.0
                    score = min(score, 1.0)
                    
                    # Cache the score
                    self._scores_cache[cache_key] = score
                    
                    scored_docs.append((doc, score))
                except (ValueError, IndexError) as e:
                    logger.error(f"Error parsing score from Claude response: {e}")
                    scored_docs.append((doc, 0.5))  # Default to middle score on error
            
            return scored_docs
            
        except ImportError:
            logger.error("Anthropic package not installed. Install with 'pip install anthropic'")
            return self.compute_heuristic_scores(query, documents)
            
    def _score_with_openai(self, query: str, documents: List[Document]) -> List[Tuple[Document, float]]:
        """Use OpenAI to score documents.
        
        Args:
            query: The search query
            documents: List of documents to score
            
        Returns:
            List of (document, score) tuples
        """
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            
            # For each document, ask GPT to rate relevance from 0-100
            scored_docs = []
            
            for i, doc in enumerate(documents):
                cache_key = f"{query}_{hash(doc.page_content)}"
                if cache_key in self._scores_cache:
                    scored_docs.append((doc, self._scores_cache[cache_key]))
                    continue
                    
                prompt = f"""
                Rate how relevant the following document is to the query. Return ONLY a number between 0 and 100, where:
                - 0 means completely irrelevant
                - 100 means perfect match answering the query completely
                
                Query: "{query}"
                
                Document:
                {doc.page_content}
                """
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",  # Use smallest, fastest model for efficiency
                    max_tokens=5,
                    temperature=0,
                    messages=[
                        {"role": "system", "content": "You are a document relevance rater. Output only a number from 0-100."},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                try:
                    # Extract score from response
                    score_text = response.choices[0].message.content.strip()
                    score = float(score_text) / 100.0  # Normalize to 0-1
                    
                    # Cap score at 1.0
                    score = min(score, 1.0)
                    
                    # Cache the score
                    self._scores_cache[cache_key] = score
                    
                    scored_docs.append((doc, score))
                except (ValueError, IndexError, AttributeError) as e:
                    logger.error(f"Error parsing score from OpenAI response: {e}")
                    scored_docs.append((doc, 0.5))  # Default to middle score on error
            
            return scored_docs
            
        except ImportError:
            logger.error("OpenAI package not installed. Install with 'pip install openai'")
            return self.compute_heuristic_scores(query, documents)
            
    def _score_with_voyage(self, query: str, documents: List[Document]) -> List[Tuple[Document, float]]:
        """Use Voyage AI to score documents.
        
        Args:
            query: The search query
            documents: List of documents to score
            
        Returns:
            List of (document, score) tuples
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Voyage doesn't offer a direct reranking model, but we can use document similarity
        scored_docs = []
        
        try:
            # First, embed the query
            query_payload = {
                "model": "voyage-large-2",
                "input": query,
                "task_type": "search_query"
            }
            
            query_response = requests.post(
                "https://api.voyageai.com/v1/embeddings",
                headers=headers,
                json=query_payload
            )
            
            if not query_response.ok:
                raise Exception(f"Voyage API error: {query_response.status_code}, {query_response.text}")
                
            query_embedding = query_response.json()["embeddings"][0]
            
            # Then embed each document
            for doc in documents:
                cache_key = f"{query}_{hash(doc.page_content)}"
                if cache_key in self._scores_cache:
                    scored_docs.append((doc, self._scores_cache[cache_key]))
                    continue
                
                doc_payload = {
                    "model": "voyage-large-2",
                    "input": doc.page_content,
                    "task_type": "retrieval_document"
                }
                
                doc_response = requests.post(
                    "https://api.voyageai.com/v1/embeddings",
                    headers=headers,
                    json=doc_payload
                )
                
                if not doc_response.ok:
                    logger.error(f"Voyage API error: {doc_response.status_code}, {doc_response.text}")
                    scored_docs.append((doc, 0.5))  # Default to middle score on error
                    continue
                    
                doc_embedding = doc_response.json()["embeddings"][0]
                
                # Calculate cosine similarity as relevance score
                score = self._cosine_similarity(query_embedding, doc_embedding)
                
                # Cache the score
                self._scores_cache[cache_key] = score
                
                scored_docs.append((doc, score))
            
            return scored_docs
            
        except Exception as e:
            logger.error(f"Error scoring with Voyage: {str(e)}")
            return self.compute_heuristic_scores(query, documents)
            
    def _cosine_similarity(self, v1, v2):
        """Calculate cosine similarity between two vectors."""
        import numpy as np
        v1, v2 = np.array(v1), np.array(v2)
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        
    def _batch_score_documents(self, query: str, documents: List[Document]) -> List[Tuple[Document, float]]:
        """Score documents in batches for efficiency."""
        # For large document sets, we'll use heuristic scoring since it's much more efficient
        # and doesn't require multiple API calls
        return self.compute_heuristic_scores(query, documents)

    def compute_heuristic_scores(
        self, query: str, documents: List[Document]
    ) -> List[Tuple[Document, float]]:
        """Compute relevance scores using heuristics when model is unavailable.
        
        Args:
            query: The search query
            documents: List of documents to score
            
        Returns:
            List of (document, score) tuples
        """
        query_lower = query.lower()
        query_terms = set(re.findall(r'\b\w+\b', query_lower))
        
        scored_docs = []
        for doc in documents:
            # Start with base score
            score = 0.5
            
            # Calculate term overlap
            doc_lower = doc.page_content.lower()
            doc_terms = set(re.findall(r'\b\w+\b', doc_lower))
            
            # Term overlap ratio
            if query_terms and doc_terms:
                overlap = len(query_terms.intersection(doc_terms)) / len(query_terms)
                score += overlap * 0.3
            
            # Check for exact phrases (exact matches weighted heavily)
            if len(query) > 5:  # Only check if query is non-trivial
                phrases = [phrase for phrase in re.findall(r'\b\w+(?:\s+\w+){1,5}\b', query_lower) if len(phrase) > 5]
                for phrase in phrases:
                    if phrase in doc_lower:
                        score += 0.15
            
            # Add relevance keyword bonuses
            for keyword, weight in self.relevance_keywords.items():
                if keyword in doc_lower:
                    score += 0.05 * weight
            
            # Adjust by document type if available
            doc_type = doc.metadata.get("doc_type", "").lower()
            if doc_type in self.doc_type_weights:
                score *= self.doc_type_weights[doc_type]
            
            # Cap score at 1.0 (to simulate probability)
            score = min(score, 1.0)
            
            scored_docs.append((doc, score))
            
        return scored_docs

    def extract_citations(self, document: Document) -> Dict[str, Any]:
        """Extract citation information from document metadata.
        
        Args:
            document: Document to extract citations from
            
        Returns:
            Dictionary of citation information
        """
        citation = {}
        
        # Extract basic information
        citation["source"] = document.metadata.get("source", "")
        citation["file_name"] = document.metadata.get("file_name", "")
        citation["doc_type"] = document.metadata.get("doc_type", "")
        
        # Extract vendor information if available
        if "vendor" in document.metadata:
            citation["vendor"] = document.metadata["vendor"]
            
        # Extract product information if available
        if "product" in document.metadata:
            citation["product"] = document.metadata["product"]
            
        # Extract use case information if available
        if "use_case" in document.metadata:
            citation["use_case"] = document.metadata["use_case"]
            
        # Extract MITRE ATT&CK information if available
        if "mitre_attack" in document.metadata:
            citation["mitre_attack"] = document.metadata["mitre_attack"]
            
        # Extract content section if available
        if "content_section" in document.metadata:
            citation["content_section"] = document.metadata["content_section"]
            
        # Add chunk identifier for reference
        if "chunk_id" in document.metadata:
            citation["chunk_id"] = document.metadata["chunk_id"]
            
        return citation

    def diversify_results(
        self, scored_docs: List[Tuple[Document, float]]
    ) -> List[Tuple[Document, float]]:
        """Ensure diversity in the top results.
        
        Args:
            scored_docs: List of (document, score) tuples
            
        Returns:
            Diversified list of (document, score) tuples
        """
        if len(scored_docs) <= 3:
            return scored_docs
            
        # Group by document type
        type_groups = defaultdict(list)
        for doc, score in scored_docs:
            doc_type = doc.metadata.get("doc_type", "unknown")
            type_groups[doc_type].append((doc, score))
            
        # Ensure we have a mix of document types
        diversified = []
        
        # First take the top document from each type (if score is good enough)
        for doc_type, docs in type_groups.items():
            if docs:
                # Sort by score within each type
                sorted_docs = sorted(docs, key=lambda x: x[1], reverse=True)
                top_doc, top_score = sorted_docs[0]
                
                # Only include if score is good
                if top_score >= 0.6:
                    diversified.append((top_doc, top_score))
                    
        # Then fill in with the best remaining documents
        remaining = [item for item in scored_docs if item not in diversified]
        remaining.sort(key=lambda x: x[1], reverse=True)
        
        # Add remaining high-scoring documents
        for doc, score in remaining:
            if score >= 0.5:
                diversified.append((doc, score))
                
        # Sort final list by score
        diversified.sort(key=lambda x: x[1], reverse=True)
        
        return diversified

    def rerank(
        self, query: str, documents: List[Document], threshold: float = 0.7
    ) -> List[Document]:
        """Rerank documents based on relevance to the query.

        Args:
            query: The search query
            documents: List of documents to rerank
            threshold: Minimum relevance score threshold

        Returns:
            Reranked list of documents
        """
        if not documents:
            return []

        logger.info(f"Reranking {len(documents)} documents using {self.provider} provider")
        
        # Generate scores using API provider or fall back to heuristics
        scored_docs = self.compute_api_scores(query, documents)
        
        # Log scores for debugging
        for i, (doc, score) in enumerate(scored_docs[:5]):
            doc_preview = doc.page_content[:50].replace('\n', ' ') + '...'
            logger.debug(f"Doc {i+1}: Score {score:.4f} - {doc_preview}")
        
        # Ensure diversity in top results
        diversified_docs = self.diversify_results(scored_docs)
        
        # Filter by threshold and extract documents
        filtered_docs = [doc for doc, score in diversified_docs if score >= threshold]
        
        # If we filtered too aggressively, keep at least 3 documents
        if len(filtered_docs) < 3 and scored_docs:
            # Sort by score and take the top 3
            top_docs = sorted(scored_docs, key=lambda x: x[1], reverse=True)
            filtered_docs = [doc for doc, _ in top_docs[:3]]
            
        logger.info(f"Reranking complete. Kept {len(filtered_docs)} documents above threshold {threshold}")
        return filtered_docs

    def rerank_with_scores(
        self, query: str, documents: List[Document], threshold: float = 0.0
    ) -> List[Tuple[Document, float]]:
        """Rerank documents and return with relevance scores.

        Args:
            query: The search query
            documents: List of documents to rerank
            threshold: Minimum relevance score threshold

        Returns:
            Reranked list of (document, score) tuples
        """
        if not documents:
            return []

        # Generate scores using API provider or fall back to heuristics
        scored_docs = self.compute_api_scores(query, documents)
        
        # Ensure diversity in top results
        diversified_docs = self.diversify_results(scored_docs)
        
        # Filter by threshold 
        filtered_docs = [(doc, score) for doc, score in diversified_docs if score >= threshold]
        
        # Sort by score
        filtered_docs.sort(key=lambda x: x[1], reverse=True)
        
        return filtered_docs
