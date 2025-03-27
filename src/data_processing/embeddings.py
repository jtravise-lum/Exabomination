"""Embeddings module for converting text to vectors using Voyage AI."""

import logging
import os
import time
import requests
import concurrent.futures
from typing import List, Dict, Any, Optional, Union, Tuple

from langchain.embeddings.base import Embeddings
from langchain.schema import Document

from src.config import EMBEDDING_MODELS, DEFAULT_EMBEDDING_MODEL, VOYAGE_API_KEY

logger = logging.getLogger(__name__)


class VoyageAIEmbeddings(Embeddings):
    """Custom integration with Voyage AI embedding models."""
    
    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        batch_size: int = 8, 
        request_timeout: Optional[float] = None,
        retry_max: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize Voyage AI embeddings.
        
        Args:
            model_name: Voyage AI model name to use
            api_key: Voyage AI API key
            batch_size: Batch size for embedding multiple texts
            request_timeout: Request timeout in seconds
            retry_max: Maximum number of retries
            retry_delay: Delay between retries in seconds
        """
        self.model_name = model_name
        self.api_key = api_key or VOYAGE_API_KEY
        if not self.api_key:
            raise ValueError(
                "Voyage AI API key is required. Set it in the .env file as VOYAGE_API_KEY."
            )
        
        self.batch_size = batch_size
        self.request_timeout = request_timeout
        self.retry_max = retry_max
        self.retry_delay = retry_delay
        
        self.api_base_url = "https://api.voyageai.com/v1/embeddings"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Model dimensions (will be updated on first call)
        self._dimensions = None
        
        logger.info(f"Initialized Voyage AI embeddings with model: {model_name}")
    
    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimensions.
        
        Returns:
            Number of dimensions in the embedding vector
        """
        if self._dimensions is None:
            # Get dimensions by embedding a test string
            sample = self.embed_query("test")
            self._dimensions = len(sample)
        return self._dimensions

    def _create_embeddings(self, texts: List[str], retry_count: int = 0) -> List[List[float]]:
        """Create embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
            retry_count: Current retry attempt
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
            
        try:
            response = requests.post(
                self.api_base_url,
                headers=self.headers,
                json={
                    "model": self.model_name,
                    "input": texts,
                },
                timeout=self.request_timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Extract embeddings from response
            embeddings = [item["embedding"] for item in data["data"]]
            return embeddings
            
        except (requests.RequestException, KeyError) as e:
            if retry_count < self.retry_max:
                # Exponential backoff
                wait_time = self.retry_delay * (2 ** retry_count)
                logger.warning(f"Voyage API request failed: {str(e)}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                return self._create_embeddings(texts, retry_count + 1)
            else:
                logger.error(f"Failed to create embeddings after {self.retry_max} retries: {str(e)}")
                raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
            
        # Filter out empty strings
        non_empty_texts = [text for text in texts if text.strip()]
        if len(non_empty_texts) != len(texts):
            logger.warning(f"Filtered out {len(texts) - len(non_empty_texts)} empty texts")
            
        if not non_empty_texts:
            return []
            
        # Process in batches to avoid API limits
        all_embeddings = []
        for i in range(0, len(non_empty_texts), self.batch_size):
            batch = non_empty_texts[i:i+self.batch_size]
            logger.debug(f"Embedding batch of {len(batch)} texts")
            
            batch_embeddings = self._create_embeddings(batch)
            all_embeddings.extend(batch_embeddings)
            
            # Add a small delay between batches to avoid rate limits
            if i + self.batch_size < len(non_empty_texts):
                time.sleep(0.5)
                
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        if not text.strip():
            # Return zero vector if text is empty
            dimensions = self.embedding_dimension if self._dimensions else 1024
            return [0.0] * dimensions
            
        result = self.embed_documents([text])
        return result[0] if result else []


class MultiModalEmbeddingProvider:
    """Provides embeddings using multiple specialized embedding models."""

    def __init__(
        self,
        model_config: Optional[Dict[str, str]] = None,
        default_model: Optional[str] = None,
        max_workers: int = 4
    ):
        """Initialize the multi-modal embedding provider.

        Args:
            model_config: Map of content types to model names
            default_model: Default model to use
            max_workers: Maximum number of parallel workers for embedding
        """
        self.model_config = model_config or EMBEDDING_MODELS
        self.default_model = default_model or DEFAULT_EMBEDDING_MODEL
        self.embeddings_cache = {}
        self.max_workers = max_workers
        
        logger.info(f"Initializing multi-modal embedding provider with models: {self.model_config}")
        logger.info(f"Default model: {self.default_model}")
        logger.info(f"Using {self.max_workers} parallel workers for embedding")
        
        # Initialize models
        for content_type, model_name in self.model_config.items():
            self.embeddings_cache[model_name] = VoyageAIEmbeddings(model_name=model_name)
            
        # Ensure default model is initialized
        if self.default_model not in self.embeddings_cache:
            self.embeddings_cache[self.default_model] = VoyageAIEmbeddings(model_name=self.default_model)
    
    def _get_model_for_content(self, document: Document) -> str:
        """Determine the best embedding model for the given document.

        Args:
            document: Document to analyze

        Returns:
            Name of the appropriate embedding model
        """
        doc_type = document.metadata.get("doc_type", "")
        content = document.page_content
        
        # Use code model for parser and technical content
        if any([
            doc_type == "parser",
            "```" in content,  # Contains code blocks
            "Ps" in document.metadata.get("source", ""),  # Parser files
            document.metadata.get("parser_name", "")  # Has parser name metadata
        ]):
            return self.model_config.get("code", self.default_model)
            
        # Use text model for natural language content
        return self.model_config.get("text", self.default_model)
    
    def embed_documents(self, documents: List[Document]) -> List[Tuple[List[float], Document]]:
        """Embed a list of documents using the appropriate model for each, with parallel processing.

        Args:
            documents: List of documents to embed

        Returns:
            List of (embedding, document) tuples
        """
        if not documents:
            return []
        
        # Group documents by appropriate model
        model_docs: Dict[str, List[Tuple[int, Document]]] = {}
        
        for i, doc in enumerate(documents):
            model_name = self._get_model_for_content(doc)
            if model_name not in model_docs:
                model_docs[model_name] = []
            model_docs[model_name].append((i, doc))
        
        # Create embeddings using each model with parallel processing
        result_embeddings = [None] * len(documents)
        
        # Function to process a batch of documents with a specific model
        def process_batch(batch_data):
            model_name, batch_indices, batch_docs, batch_texts = batch_data
            embedder = self.embeddings_cache[model_name]
            
            try:
                batch_embeddings = embedder.embed_documents(batch_texts)
                # Return successful results
                return [(idx, embedding, doc, model_name, None) 
                        for idx, embedding, doc in zip(batch_indices, batch_embeddings, batch_docs)]
            except Exception as e:
                # Return error to be handled later
                return [(idx, None, doc, model_name, str(e)) 
                        for idx, doc in zip(batch_indices, batch_docs)]
        
        # Prepare batches for parallel processing
        all_batches = []
        for model_name, doc_list in model_docs.items():
            indices = [item[0] for item in doc_list]
            docs = [item[1] for item in doc_list]
            texts = [doc.page_content for doc in docs]
            
            # Create smaller sub-batches for better parallelism
            sub_batch_size = 10  # Adjust based on your needs
            for i in range(0, len(indices), sub_batch_size):
                batch_indices = indices[i:i+sub_batch_size]
                batch_docs = docs[i:i+sub_batch_size]
                batch_texts = texts[i:i+sub_batch_size]
                
                all_batches.append((model_name, batch_indices, batch_docs, batch_texts))
        
        logger.info(f"Processing {len(documents)} documents in {len(all_batches)} parallel batches with {self.max_workers} workers")
        
        # Process batches in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            batch_results = list(executor.map(process_batch, all_batches))
        
        # Flatten results and handle errors
        for batch_result in batch_results:
            for idx, embedding, doc, model_name, error in batch_result:
                if error is None:
                    # Successful embedding
                    result_embeddings[idx] = (embedding, doc)
                else:
                    # Handle error with fallback
                    logger.error(f"Error embedding document with model {model_name}: {error}")
                    if model_name != self.default_model:
                        logger.info(f"Falling back to default model {self.default_model}")
                        try:
                            default_embedder = self.embeddings_cache[self.default_model]
                            fallback_embedding = default_embedder.embed_documents([doc.page_content])[0]
                            result_embeddings[idx] = (fallback_embedding, doc)
                        except Exception as fallback_error:
                            logger.error(f"Fallback embedding also failed: {str(fallback_error)}")
        
        # Filter out any None values (should not happen with fallback)
        return [item for item in result_embeddings if item is not None]
    
    def embed_query(self, query: str, query_type: str = "text") -> List[float]:
        """Embed a query string using the appropriate model.

        Args:
            query: Query string to embed
            query_type: Type of query ("text" or "code")

        Returns:
            Embedding vector
        """
        model_name = self.model_config.get(query_type, self.default_model)
        embedder = self.embeddings_cache[model_name]
        
        return embedder.embed_query(query)


# For backward compatibility, define EmbeddingProvider as an alias
EmbeddingProvider = MultiModalEmbeddingProvider
