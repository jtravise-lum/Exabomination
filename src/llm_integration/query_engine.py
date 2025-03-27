"""Query engine for EXASPERATION."""

import logging
import time
from typing import Dict, List, Any, Optional, Union

from src.llm_integration.base import BaseLLM
from src.llm_integration.llm_factory import get_default_llm
from src.llm_integration.prompt_templates import PromptTemplates
from src.retrieval.retriever import Retriever
from src.retrieval.query_processor import QueryProcessor
from src.config import TOP_K_RETRIEVAL

logger = logging.getLogger(__name__)


class QueryEngine:
    """Query engine for retrieving information and generating responses.
    
    This class integrates the retriever and LLM components to provide a complete
    end-to-end RAG pipeline.
    """
    
    def __init__(
        self,
        retriever: Retriever,
        llm: Optional[BaseLLM] = None,
        prompt_templates: Optional[PromptTemplates] = None,
        max_context_tokens: int = 4000,
        include_citations: bool = True,
        hybrid_search: bool = True,
        top_k: int = TOP_K_RETRIEVAL
    ):
        """Initialize the query engine.
        
        Args:
            retriever: Retriever instance for document retrieval
            llm: Optional LLM instance (defaults to default provider)
            prompt_templates: Optional prompt templates
            max_context_tokens: Maximum tokens for context
            include_citations: Whether to include document citations in context
            hybrid_search: Whether to use hybrid search for retrieval
            top_k: Number of documents to retrieve
        """
        self.retriever = retriever
        self.llm = llm or get_default_llm()
        self.prompt_templates = prompt_templates or PromptTemplates()
        self.max_context_tokens = max_context_tokens
        self.include_citations = include_citations
        self.hybrid_search = hybrid_search
        self.top_k = top_k
        
        logger.info(f"Initialized QueryEngine with {self.llm.__class__.__name__} "
                   f"using model: {self.llm.model_name}")
        
        # Initialize results cache
        self._results_cache = {}
        self._cache_size = 50
    
    def process_query(
        self,
        query: str,
        filter: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Process a query and return a response with context.
        
        Args:
            query: User query
            filter: Optional metadata filters for retrieval
            max_tokens: Optional maximum tokens for response
            temperature: Optional temperature for response generation
            use_cache: Whether to use cached results for identical queries
            
        Returns:
            Dictionary with response, context, documents, and timing information
        """
        # Check cache if enabled
        cache_key = f"{query}_{str(filter)}"
        if use_cache and cache_key in self._results_cache:
            logger.info(f"Using cached result for query: {query}")
            return self._results_cache[cache_key]
        
        # Start timing
        start_time = time.time()
        
        # Retrieve relevant documents
        retrieval_start = time.time()
        documents = self.retriever.retrieve(
            query=query,
            filter=filter
        )
        retrieval_time = time.time() - retrieval_start
        
        # Assemble context from retrieved documents
        context_start = time.time()
        context = self.retriever.assemble_context(
            documents=documents,
            max_tokens=self.max_context_tokens
        )
        context_time = time.time() - context_start
        
        # If no context was found, return early with a no-information response
        if not context:
            logger.warning(f"No context found for query: {query}")
            response = {
                "answer": "I don't have enough information to answer this question based on the available documentation.",
                "context": "",
                "documents": [],
                "timing": {
                    "retrieval_time": retrieval_time,
                    "context_time": context_time,
                    "generation_time": 0,
                    "total_time": time.time() - start_time
                }
            }
            return response
        
        # Format prompt based on query type
        prompt_start = time.time()
        prompts = self.prompt_templates.format_prompt(query, context)
        prompt_time = time.time() - prompt_start
        
        # Generate response with LLM
        generation_start = time.time()
        answer = self.llm.generate(
            prompt=prompts["user_prompt"],
            system_prompt=prompts["system_prompt"],
            max_tokens=max_tokens,
            temperature=temperature
        )
        generation_time = time.time() - generation_start
        
        # Prepare response
        response = {
            "answer": answer,
            "context": context if self.include_citations else "",
            "documents": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in documents
            ] if self.include_citations else [],
            "timing": {
                "retrieval_time": retrieval_time,
                "context_time": context_time,
                "prompt_time": prompt_time,
                "generation_time": generation_time,
                "total_time": time.time() - start_time
            },
            "token_usage": self.llm.get_token_usage()
        }
        
        # Cache result if enabled
        if use_cache:
            # Manage cache size
            if len(self._results_cache) >= self._cache_size:
                # Remove a random entry
                self._results_cache.pop(next(iter(self._results_cache)))
            
            self._results_cache[cache_key] = response
        
        logger.info(f"Processed query in {response['timing']['total_time']:.2f}s: {query}")
        return response
    
    def get_llm_models(self) -> Dict[str, Any]:
        """Get information about the available LLM models.
        
        Returns:
            Dictionary with provider and model information
        """
        model_info = {
            "current_model": {
                "provider": self.llm.__class__.__name__,
                "model_name": self.llm.model_name
            },
            "available_models": {
                "anthropic": [
                    "claude-3-5-sonnet-20240620",
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307"
                ],
                "openai": [
                    "gpt-4o",
                    "gpt-4-turbo",
                    "gpt-4",
                    "gpt-3.5-turbo"
                ]
            }
        }
        return model_info
    
    def change_llm(
        self,
        provider: str,
        model_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Change the LLM provider and model.
        
        Args:
            provider: New provider ("anthropic", "openai", or "mock")
            model_name: New model name
            **kwargs: Additional parameters for the new LLM
            
        Returns:
            Dictionary with status and model information
        """
        from src.llm_integration.llm_factory import create_llm
        
        try:
            # Create new LLM instance
            new_llm = create_llm(
                provider=provider,
                model_name=model_name,
                **kwargs
            )
            
            # Test the new LLM with a simple query
            test_response = new_llm.generate("Hello world")
            
            # If successful, update the instance
            self.llm = new_llm
            
            return {
                "status": "success",
                "message": f"Changed LLM to {provider}/{model_name}",
                "model_info": {
                    "provider": provider,
                    "model_name": model_name
                }
            }
        except Exception as e:
            logger.error(f"Failed to change LLM: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to change LLM: {str(e)}",
                "model_info": {
                    "provider": self.llm.__class__.__name__,
                    "model_name": self.llm.model_name
                }
            }