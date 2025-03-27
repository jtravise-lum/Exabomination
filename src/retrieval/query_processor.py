"""Query processing module for enhancing and optimizing search queries."""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple

from src.config import EMBEDDING_MODELS, DEFAULT_EMBEDDING_MODEL
from src.data_processing.embeddings import MultiModalEmbeddingProvider

logger = logging.getLogger(__name__)


class QueryProcessor:
    """Processes and enhances search queries for improved retrieval.
    
    This class handles:
    1. Query preprocessing and normalization
    2. Query type detection (technical, terminology, or conceptual)
    3. Security domain knowledge integration
    4. Query expansion with synonyms and related terms
    5. Metadata extraction for filtering
    """

    def __init__(self, embedding_provider: Optional[MultiModalEmbeddingProvider] = None):
        """Initialize the query processor.
        
        Args:
            embedding_provider: Optional embedding provider for query embedding
        """
        self.embedding_provider = embedding_provider or MultiModalEmbeddingProvider()
        
        # Security domain knowledge initialization
        self._initialize_security_mappings()
        
    def _initialize_security_mappings(self):
        """Initialize security domain-specific mappings for terms, acronyms, and concepts."""
        # Exabeam product and feature mappings
        self.exabeam_products = {
            "advanced analytics": ["aa", "analytics", "exabeam analytics"],
            "data lake": ["dl", "edl", "exabeam data lake"],
            "cloud platform": ["ecp", "platform", "cloud security"],
            "case management": ["ecm", "case manager", "incident management"],
            "entity analytics": ["ea", "entity behavior", "entity profiling"],
            "threat hunter": ["th", "threat hunting", "hunting"],
            "incident responder": ["ir", "incident response", "response"],
            "threat detection": ["td", "detection", "detection rules"],
        }
        
        # Security acronym expansion
        self.security_acronyms = {
            "ueba": "user and entity behavior analytics",
            "siem": "security information and event management",
            "soar": "security orchestration automation and response",
            "edr": "endpoint detection and response",
            "xdr": "extended detection and response",
            "ndr": "network detection and response",
            "mfa": "multi-factor authentication",
            "iam": "identity and access management",
            "pam": "privileged access management",
            "dlp": "data loss prevention",
            "vtm": "vault test model"
        }
        
        # MITRE ATT&CK technique patterns
        self.mitre_pattern = re.compile(r'T\d{4}(?:\.(?:\d{3}|\d{2}|\d{1}))?')
        
        # Technical terms indicating code or parser related content
        self.technical_terms = [
            "parser", "function", "rule", "model", "code", "script", "api", 
            "config", "configuration", "parameter", "syntax", "format", "regex",
            "implementation", "json", "xml", "csv", "field", "mapping"
        ]
        
        # Conceptual terms indicating security concepts
        self.conceptual_terms = [
            "attack", "threat", "risk", "vuln", "incident", "breach", "malware",
            "ransomware", "phishing", "lateral", "privilege", "escalation", "detection",
            "monitor", "alert", "investigation", "response", "strategy", "framework"
        ]

    def detect_query_type(self, query: str) -> str:
        """Detect the type of query to determine appropriate embedding model.
        
        Args:
            query: The query to analyze
            
        Returns:
            Query type: "code" for technical queries, "text" for conceptual queries
        """
        query_lower = query.lower()
        
        # Check for technical indicators
        if any(term in query_lower for term in self.technical_terms):
            logger.debug(f"Query classified as technical: {query}")
            return "code"
            
        # Check for MITRE ATT&CK technique IDs
        if self.mitre_pattern.search(query):
            logger.debug(f"Query contains MITRE ATT&CK technique: {query}")
            return "code"
            
        # Check for parser or implementation related content
        if re.search(r'parser|implementation|configuration|format|field|mapping', query_lower):
            logger.debug(f"Query classified as implementation related: {query}")
            return "code"
            
        # Default to text for conceptual and general queries
        return "text"

    def extract_metadata_filters(self, query: str) -> Tuple[str, Dict[str, Any]]:
        """Extract metadata filters from the query.
        
        Args:
            query: The user query
            
        Returns:
            Tuple of (cleaned query, metadata filters dict)
        """
        metadata_filters = {}
        cleaned_query = query
        
        # Extract vendor information
        vendor_match = re.search(r'(?:from|by|vendor:?)\s+([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)?)', query, re.IGNORECASE)
        if vendor_match:
            metadata_filters["vendor"] = vendor_match.group(1).strip()
            # Remove the vendor specification from the query
            cleaned_query = re.sub(r'(?:from|by|vendor:?)\s+([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)?)', '', cleaned_query)
            
        # Extract product type
        product_match = re.search(r'(?:product:?|type:?)\s+([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)?)', query, re.IGNORECASE)
        if product_match:
            metadata_filters["product_type"] = product_match.group(1).strip()
            # Remove the product specification from the query
            cleaned_query = re.sub(r'(?:product:?|type:?)\s+([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)?)', '', cleaned_query)
            
        # Extract use case
        use_case_match = re.search(r'(?:use\s+case:?|usecase:?)\s+([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)?)', query, re.IGNORECASE)
        if use_case_match:
            metadata_filters["use_case"] = use_case_match.group(1).strip()
            # Remove the use case specification from the query
            cleaned_query = re.sub(r'(?:use\s+case:?|usecase:?)\s+([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)?)', '', cleaned_query)
            
        # Clean up any extra whitespace
        cleaned_query = ' '.join(cleaned_query.split())
        
        if metadata_filters:
            logger.info(f"Extracted metadata filters: {metadata_filters}")
            
        return cleaned_query, metadata_filters

    def expand_exabeam_terms(self, query: str) -> str:
        """Expand Exabeam-specific terms and acronyms.
        
        Args:
            query: The query to expand
            
        Returns:
            Expanded query
        """
        expanded_query = query
        
        # Expand Exabeam product terms
        for product, aliases in self.exabeam_products.items():
            if product in query.lower():
                # Add aliases to query if the product is mentioned
                alias_terms = " OR ".join([f'"{alias}"' for alias in aliases if alias not in query.lower()])
                if alias_terms:
                    expanded_query = f"{expanded_query} {alias_terms}"
                    
        # Expand security acronyms
        for acronym, expansion in self.security_acronyms.items():
            # Look for the acronym as a whole word
            if re.search(r'\b' + acronym + r'\b', query.lower()):
                # Add the expansion if not already in the query
                if expansion not in query.lower():
                    expanded_query = f"{expanded_query} OR \"{expansion}\""
                    
        return expanded_query

    def process_query(self, query: str) -> str:
        """Process and enhance a query for improved retrieval.

        Args:
            query: The original user query

        Returns:
            Enhanced query for retrieval
        """
        if not query or not query.strip():
            logger.warning("Empty query received")
            return query

        # Normalize whitespace
        query = " ".join(query.split())
        logger.info(f"Processing query: {query}")
        
        # Extract metadata filters - we'll use the cleaned query
        cleaned_query, _ = self.extract_metadata_filters(query)
        
        # Expand Exabeam-specific terms
        expanded_query = self.expand_exabeam_terms(cleaned_query)
        
        # Handle MITRE ATT&CK references
        mitre_refs = self.mitre_pattern.findall(expanded_query)
        if mitre_refs:
            logger.info(f"Found MITRE ATT&CK references: {mitre_refs}")
            # Ensure we keep both the ID and potential descriptions
            for ref in mitre_refs:
                # We'll keep both the reference and add weight to it
                expanded_query = expanded_query.replace(ref, f"{ref} {ref}")
        
        logger.info(f"Processed query: {expanded_query}")
        return expanded_query

    def expand_query(self, query: str) -> List[str]:
        """Expand a query into multiple search queries.

        Args:
            query: The original user query

        Returns:
            List of expanded queries
        """
        expanded_queries = []
        
        # Add the original query
        expanded_queries.append(query)
        
        # Add a version with expanded Exabeam terms
        expanded_exabeam = self.expand_exabeam_terms(query)
        if expanded_exabeam != query:
            expanded_queries.append(expanded_exabeam)
        
        # Extract and add keywords as a separate query
        keywords = self.extract_keywords(query)
        if keywords and len(keywords) > 1:
            keyword_query = " ".join(keywords)
            if keyword_query != query:
                expanded_queries.append(keyword_query)
        
        logger.info(f"Expanded query into {len(expanded_queries)} variants")
        return expanded_queries

    def extract_keywords(self, query: str) -> List[str]:
        """Extract key terms from a query.

        Args:
            query: The original user query

        Returns:
            List of key terms
        """
        # Extended stop words list
        stop_words = {
            "the", "a", "an", "in", "on", "at", "for", "with", "by", "to", "of", "and", 
            "or", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", 
            "do", "does", "did", "but", "if", "then", "else", "when", "where", "which", 
            "who", "whom", "whose", "what", "how", "why", "can", "could", "may", "might", 
            "shall", "should", "will", "would", "that", "this", "these", "those", "i", 
            "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them"
        }
        
        # Tokenize and filter
        words = query.lower().split()
        keywords = [word for word in words if word not in stop_words and len(word) > 1]
        
        # Prioritize technical terms and security concepts
        prioritized_keywords = []
        
        # Check for MITRE ATT&CK references first
        mitre_refs = self.mitre_pattern.findall(query)
        prioritized_keywords.extend(mitre_refs)
        
        # Add technical and security terms with priority
        for word in keywords:
            if any(term in word for term in self.technical_terms + self.conceptual_terms):
                prioritized_keywords.append(word)
                
        # Add remaining keywords
        for word in keywords:
            if word not in prioritized_keywords:
                prioritized_keywords.append(word)
                
        logger.info(f"Extracted keywords: {prioritized_keywords}")
        return prioritized_keywords
        
    def embed_query(self, query: str) -> List[float]:
        """Embed the query using the appropriate model.
        
        Args:
            query: The query to embed
            
        Returns:
            Query embedding vector
        """
        # Detect query type to select appropriate model
        query_type = self.detect_query_type(query)
        logger.info(f"Using {query_type} embedding model for query: {query}")
        
        # Use the embedding provider to embed the query
        embedding = self.embedding_provider.embed_query(query, query_type=query_type)
        
        return embedding
