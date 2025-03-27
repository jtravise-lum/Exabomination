#!/usr/bin/env python3
"""
Fixed version of the ingestion pipeline that bypasses ChromaDB server
to directly access the database files.
"""

import logging
import os
import sys
import uuid
import time
from pathlib import Path
import shutil
import argparse

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
import chromadb
from chromadb.config import Settings

def reset_chromadb():
    """Reset the ChromaDB database by stopping Docker and cleaning up."""
    logger.info("Stopping ChromaDB container...")
    os.system("docker compose stop chromadb")
    
    data_dir = Path("data/chromadb")
    logger.info(f"Removing ChromaDB data directory: {data_dir}")
    
    try:
        # Try using rmtree (may require sudo in some cases)
        if data_dir.exists():
            shutil.rmtree(data_dir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Error removing data directory: {e}")
        logger.info("Trying with sudo...")
        os.system(f"sudo rm -rf {data_dir}")
    
    # Create fresh data directory with proper permissions
    logger.info("Creating fresh data directory...")
    data_dir.mkdir(parents=True, exist_ok=True)
    os.system(f"chmod -R 777 {data_dir}")
    
    # Create logs directory
    logs_dir = Path("data/chromadb_logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    os.system(f"chmod -R 777 {logs_dir}")
    
    # Start ChromaDB container
    logger.info("Starting ChromaDB container...")
    os.system("docker compose up -d chromadb")
    
    # Wait for container to be ready
    logger.info("Waiting for ChromaDB to be ready...")
    time.sleep(5)

def direct_add_documents(content_dir, batch_size=10, max_docs=None, reset=False):
    """Process and add documents directly to ChromaDB using local API.
    
    Args:
        content_dir: Directory containing documents to process
        batch_size: Number of documents to process in each batch
        max_docs: Maximum number of documents to process (for testing)
        reset: Whether to reset the database before processing
    """
    if reset:
        reset_chromadb()
    
    # Import here to avoid circular imports
    from src.data_processing.embeddings import MultiModalEmbeddingProvider
    from src.data_processing.exabeam_processor import ExabeamContentProcessor
    from src.data_processing.exabeam_loader import ExabeamDocumentLoader
    from src.data_processing.exabeam_chunker import ExabeamChunker
    
    # Initialize components for document loading and processing
    logger.info(f"Initializing document processing components for {content_dir}")
    document_loader = ExabeamDocumentLoader(content_dir=content_dir)
    chunker = ExabeamChunker()
    embedding_provider = MultiModalEmbeddingProvider(max_workers=4)
    
    # Initialize processor with our specialized components
    content_processor = ExabeamContentProcessor(
        content_dir=content_dir,
        document_loader=document_loader,
        document_chunker=chunker,
    )
    
    # Process content to get document chunks
    logger.info("Processing content...")
    documents = content_processor.process_content()
    if max_docs:
        documents = documents[:max_docs]
    
    logger.info(f"Processed {len(documents)} document chunks")
    if not documents:
        logger.warning("No documents to ingest")
        return
    
    # Sanitize metadata for ChromaDB
    logger.info("Sanitizing document metadata for ChromaDB compatibility")
    sanitized_documents = []
    for doc in documents:
        sanitized_metadata = {}
        for key, value in doc.metadata.items():
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                sanitized_metadata[key] = ", ".join(str(item) for item in value)
            elif isinstance(value, dict):
                sanitized_metadata[key] = str(value)
            elif isinstance(value, (str, int, float, bool)):
                sanitized_metadata[key] = value
            else:
                sanitized_metadata[key] = str(value)
        
        # Create a sanitized document
        sanitized_doc = Document(
            page_content=doc.page_content,
            metadata=sanitized_metadata
        )
        sanitized_documents.append(sanitized_doc)
    
    # Now use direct local ChromaDB access
    logger.info("Initializing direct local ChromaDB client")
    client = chromadb.PersistentClient(path="data/chromadb")
    
    # Create collection
    collection_name = "exabeam_docs"
    logger.info(f"Creating collection: {collection_name}")
    
    try:
        # Delete collection if it exists
        try:
            client.delete_collection(collection_name)
            logger.info(f"Deleted existing collection: {collection_name}")
        except Exception as e:
            logger.info(f"Collection {collection_name} does not exist or could not be deleted: {e}")
        
        # Create fresh collection
        collection = client.create_collection(name=collection_name)
        logger.info(f"Created collection: {collection_name}")
        
        # Add documents in batches
        total_batches = (len(sanitized_documents) + batch_size - 1) // batch_size
        
        successful_docs = 0
        for i in range(0, len(sanitized_documents), batch_size):
            batch = sanitized_documents[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            
            logger.info(f"Processing batch {batch_num}/{total_batches} with {len(batch)} documents")
            
            try:
                # Prepare data for ChromaDB format
                ids = [str(uuid.uuid4()) for _ in batch]
                texts = [doc.page_content for doc in batch]
                metadatas = [doc.metadata for doc in batch]
                
                # Get embeddings
                logger.info(f"Generating embeddings for batch {batch_num}")
                embedding_results = embedding_provider.embed_documents(batch)
                embeddings = [emb for emb, _ in embedding_results]
                
                # Add to collection
                collection.add(
                    ids=ids,
                    documents=texts,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
                
                # Verify count to ensure persistence
                count = collection.count()
                successful_docs += len(batch)
                
                logger.info(f"Added batch {batch_num}/{total_batches}. Collection now has {count} documents")
                
                # Add a small delay between batches
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {str(e)}", exc_info=True)
        
        # Final verification
        final_count = collection.count()
        logger.info(f"Ingestion complete. Added {successful_docs} documents. Collection size: {final_count}")
        
        return successful_docs
    
    except Exception as e:
        logger.error(f"Error during direct ingestion: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Direct ChromaDB ingestion tool")
    parser.add_argument(
        "--content-dir",
        type=str,
        default="data/content-library-cim2",
        help="Path to the content directory"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
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
    
    # Run the direct ingestion
    direct_add_documents(
        content_dir=args.content_dir,
        batch_size=args.batch_size,
        max_docs=args.max_docs,
        reset=args.reset
    )