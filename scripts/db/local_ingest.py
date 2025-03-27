#!/usr/bin/env python3
"""
Local version of the document ingestion pipeline that uses ChromaDB in local mode
instead of server mode to avoid permission/Docker issues.
"""

import logging
import os
import sys
import time
import argparse
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Add the project root to Python path
sys.path.append(str(Path(__file__).resolve().parent))

# Import the necessary modules
from langchain.schema import Document
from src.config import CHROMA_DB_PATH
from src.data_processing.embeddings import MultiModalEmbeddingProvider
from src.data_processing.exabeam_processor import ExabeamContentProcessor
from src.data_processing.exabeam_loader import ExabeamDocumentLoader
from src.data_processing.exabeam_chunker import ExabeamChunker
from src.data_processing.vector_store import VectorDatabase

def sanitize_metadata(metadata):
    """Sanitize document metadata for ChromaDB compatibility."""
    if not metadata:
        return {}
        
    sanitized = {}
    for key, value in metadata.items():
        # Skip None values
        if value is None:
            continue
            
        # Convert lists to comma-separated strings
        if isinstance(value, (list, tuple)):
            sanitized[key] = ", ".join(str(item) for item in value)
        # Convert dicts to JSON-like strings
        elif isinstance(value, dict):
            sanitized[key] = str(value)
        # Pass through scalar types supported by ChromaDB
        elif isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        # Convert anything else to string
        else:
            sanitized[key] = str(value)
            
    return sanitized

def ingest_documents(content_dir, batch_size=20, max_docs=None, reset=False):
    """Process documents and add them to ChromaDB in local mode."""
    local_db_path = os.path.join(os.getcwd(), "data", "local_chromadb")
    logger.info(f"Using local ChromaDB at: {local_db_path}")
    
    if reset and os.path.exists(local_db_path):
        logger.info(f"Resetting local ChromaDB at: {local_db_path}")
        import shutil
        shutil.rmtree(local_db_path, ignore_errors=True)
    
    # Create directory if it doesn't exist
    os.makedirs(local_db_path, exist_ok=True)
    
    # Initialize components for processing
    logger.info(f"Processing documents from: {content_dir}")
    document_loader = ExabeamDocumentLoader(content_dir=content_dir)
    chunker = ExabeamChunker()
    embedding_provider = MultiModalEmbeddingProvider(max_workers=4)
    
    # Initialize content processor
    processor = ExabeamContentProcessor(
        content_dir=content_dir,
        document_loader=document_loader,
        document_chunker=chunker,
    )
    
    # Initialize vector database in LOCAL mode (not server mode)
    vector_db = VectorDatabase(
        embedding_provider=embedding_provider,
        db_path=local_db_path,
        collection_name="exabeam_docs",
        use_server=False  # Use local mode to avoid Docker/permission issues
    )
    
    # Process content to get document chunks
    logger.info("Processing content...")
    documents = processor.process_content()
    if max_docs:
        documents = documents[:max_docs]
    
    logger.info(f"Processed {len(documents)} document chunks")
    if not documents:
        logger.warning("No documents to ingest")
        return
    
    # Sanitize metadata for ChromaDB
    sanitized_documents = []
    for doc in documents:
        sanitized_doc = Document(
            page_content=doc.page_content,
            metadata=sanitize_metadata(doc.metadata)
        )
        sanitized_documents.append(sanitized_doc)
    
    # Add documents in batches
    total_batches = (len(sanitized_documents) + batch_size - 1) // batch_size
    
    successful_docs = 0
    for i in range(0, len(sanitized_documents), batch_size):
        batch = sanitized_documents[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        
        logger.info(f"Processing batch {batch_num}/{total_batches} with {len(batch)} documents")
        
        try:
            # Add batch to vector database
            start_time = time.time()
            ids = vector_db.add_documents(batch)
            elapsed = time.time() - start_time
            
            successful_docs += len(batch)
            logger.info(f"Added batch {batch_num}/{total_batches} in {elapsed:.2f} seconds")
            
            # Check current count
            count = vector_db.vectorstore._collection.count()
            logger.info(f"Collection now has {count} documents")
            
        except Exception as e:
            logger.error(f"Error processing batch {batch_num}: {str(e)}", exc_info=True)
    
    # Final verification
    try:
        final_count = vector_db.vectorstore._collection.count()
        logger.info(f"Ingestion complete. Collection size: {final_count}")
        
        # Verify with a sample query
        logger.info("Verifying with sample query...")
        results = vector_db.similarity_search("Exabeam", k=2)
        logger.info(f"Retrieved {len(results)} documents")
        
        # Log sample document
        if results:
            doc = results[0]
            logger.info(f"Sample document: {doc.page_content[:100]}...")
            logger.info(f"Sample metadata: {doc.metadata}")
    
    except Exception as e:
        logger.error(f"Error during verification: {str(e)}", exc_info=True)
    
    return successful_docs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local ChromaDB ingestion tool")
    parser.add_argument(
        "--content-dir",
        type=str,
        default="data/content-library-cim2",
        help="Path to the content directory"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Number of documents to process in each batch"
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=None,
        help="Maximum number of documents to process (for testing)"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the database before processing"
    )
    
    args = parser.parse_args()
    
    # Run the ingestion
    ingest_documents(
        content_dir=args.content_dir,
        batch_size=args.batch_size,
        max_docs=args.max_docs,
        reset=args.reset
    )