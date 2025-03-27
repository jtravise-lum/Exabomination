#!/usr/bin/env python3
"""
Test script for EXASPERATION query engine.
"""

import os
import sys
import logging
import argparse
from typing import Optional, Dict, Any

from src.data_processing.vector_store import VectorDatabase
from src.data_processing.embeddings import MultiModalEmbeddingProvider
from src.retrieval.query_processor import QueryProcessor
from src.retrieval.retriever import Retriever
from src.retrieval.reranker import Reranker
from src.llm_integration.query_engine import QueryEngine
from src.llm_integration.llm_factory import create_llm, get_default_llm


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("test_query")


def setup_query_engine(
    llm_provider: str = "mock",
    model_name: Optional[str] = None,
    hybrid_search: bool = True,
    top_k: int = 5
) -> QueryEngine:
    """Set up the query engine with all components.
    
    Args:
        llm_provider: LLM provider to use ("anthropic", "openai", or "mock")
        model_name: Optional model name
        hybrid_search: Whether to use hybrid search
        top_k: Number of documents to retrieve
        
    Returns:
        QueryEngine instance
    """
    # Initialize embedding provider first
    logger.info("Initializing MultiModalEmbeddingProvider...")
    embedding_provider = MultiModalEmbeddingProvider()
    
    # Initialize vector database with the embedding provider
    logger.info("Initializing VectorDatabase...")
    vector_db = VectorDatabase(
        embedding_provider=embedding_provider,
        use_server=True
    )
    
    # Initialize query processor
    logger.info("Initializing QueryProcessor...")
    query_processor = QueryProcessor(embedding_provider=embedding_provider)
    
    # Initialize reranker
    logger.info("Initializing Reranker...")
    reranker = Reranker()
    
    # Initialize retriever
    logger.info("Initializing Retriever...")
    retriever = Retriever(
        vector_db=vector_db,
        query_processor=query_processor,
        embedding_provider=embedding_provider,
        reranker=reranker,
        top_k=top_k,
        enable_hybrid_search=hybrid_search
    )
    
    # Initialize LLM
    logger.info(f"Initializing LLM with provider: {llm_provider}")
    if llm_provider.lower() == "default":
        llm = get_default_llm(model_name=model_name)
    else:
        llm = create_llm(provider=llm_provider, model_name=model_name)
    
    # Initialize query engine
    logger.info("Initializing QueryEngine...")
    query_engine = QueryEngine(
        retriever=retriever,
        llm=llm,
        top_k=top_k,
        hybrid_search=hybrid_search
    )
    
    return query_engine


def process_query(
    query_engine: QueryEngine,
    query: str,
    filter: Optional[Dict[str, Any]] = None,
    temperature: float = 0.2
) -> None:
    """Process a query and print the response.
    
    Args:
        query_engine: QueryEngine instance
        query: Query to process
        filter: Optional metadata filters
        temperature: Temperature for response generation
    """
    logger.info(f"Processing query: {query}")
    
    # Process the query
    result = query_engine.process_query(
        query=query,
        filter=filter,
        temperature=temperature
    )
    
    # Print timing information
    timing = result["timing"]
    logger.info(f"Query processed in {timing['total_time']:.2f}s:")
    logger.info(f"  - Retrieval: {timing['retrieval_time']:.2f}s")
    logger.info(f"  - Context: {timing['context_time']:.2f}s")
    logger.info(f"  - Generation: {timing['generation_time']:.2f}s")
    
    # Print token usage
    token_usage = result.get("token_usage", {})
    if token_usage:
        logger.info(f"Token usage:")
        logger.info(f"  - Prompt tokens: {token_usage.get('prompt_tokens', 0)}")
        logger.info(f"  - Completion tokens: {token_usage.get('completion_tokens', 0)}")
        logger.info(f"  - Total tokens: {token_usage.get('total_tokens', 0)}")
    
    # Print document count
    logger.info(f"Retrieved {len(result['documents'])} documents")
    
    # Print answer
    print("\n" + "="*80)
    print(f"QUERY: {query}")
    print("-"*80)
    print(f"ANSWER:\n{result['answer']}")
    print("="*80)
    
    # Display document sources
    print("\nSOURCES:")
    for i, doc in enumerate(result["documents"][:3], 1):
        metadata = doc["metadata"]
        source = metadata.get("source", "Unknown")
        doc_type = metadata.get("doc_type", "")
        print(f"{i}. {source} ({doc_type})")
    
    if len(result["documents"]) > 3:
        print(f"... and {len(result['documents']) - 3} more documents")
    print()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test EXASPERATION query engine")
    parser.add_argument(
        "query",
        nargs="?",
        default="What is Exabeam and what does it do?",
        help="The query to process"
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai", "mock", "default"],
        default="mock",
        help="LLM provider to use (default: mock)"
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name to use (dependent on provider)"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of documents to retrieve"
    )
    parser.add_argument(
        "--no-hybrid",
        action="store_true",
        help="Disable hybrid search"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Temperature for response generation"
    )
    
    args = parser.parse_args()
    
    query_engine = setup_query_engine(
        llm_provider=args.provider,
        model_name=args.model,
        hybrid_search=not args.no_hybrid,
        top_k=args.top_k
    )
    
    process_query(
        query_engine=query_engine,
        query=args.query,
        temperature=args.temperature
    )


if __name__ == "__main__":
    main()