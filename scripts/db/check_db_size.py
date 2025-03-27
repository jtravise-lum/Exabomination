#!/usr/bin/env python3
"""
Check the ChromaDB database size and content.
"""

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to Python path
sys.path.append(str(Path(__file__).resolve().parent))

from chromadb import Client as ChromaClient
from chromadb.config import Settings
from src.config import CHROMA_SERVER_HOST, CHROMA_SERVER_PORT

def check_database_size():
    """Check the physical size of the database files."""
    db_path = Path("data/chromadb")
    if not db_path.exists():
        logger.error(f"Database path {db_path} does not exist")
        return
    
    # Check the total size of the database directory
    total_size = sum(f.stat().st_size for f in db_path.glob('**/*') if f.is_file())
    logger.info(f"Total database size: {total_size / 1024:.2f} KB")
    
    # Check the size of the SQLite file
    sqlite_file = db_path / "chroma.sqlite3"
    if sqlite_file.exists():
        sqlite_size = sqlite_file.stat().st_size
        logger.info(f"SQLite file size: {sqlite_size / 1024:.2f} KB")
    else:
        logger.warning(f"SQLite file {sqlite_file} does not exist")
    
    # List all collections directory sizes
    for collection_dir in db_path.glob('*'):
        if collection_dir.is_dir():
            dir_size = sum(f.stat().st_size for f in collection_dir.glob('**/*') if f.is_file())
            logger.info(f"Collection directory {collection_dir.name}: {dir_size / 1024:.2f} KB")

def check_collections():
    """Check all collections in the database."""
    try:
        client = ChromaClient(
            Settings(
                chroma_server_host=CHROMA_SERVER_HOST,
                chroma_server_http_port=CHROMA_SERVER_PORT
            )
        )
        
        # List all collections
        collections = client.list_collections()
        logger.info(f"Found {len(collections)} collections in the database")
        
        # Check each collection
        for collection_info in collections:
            if hasattr(collection_info, 'name'):
                name = collection_info.name
            elif isinstance(collection_info, dict) and 'name' in collection_info:
                name = collection_info['name']
            else:
                name = str(collection_info)
                
            collection = client.get_collection(name=name)
            count = collection.count()
            logger.info(f"Collection '{name}' has {count} documents")
            
            # Get a sample of documents if any exist
            if count > 0:
                sample_size = min(5, count)
                logger.info(f"Sampling {sample_size} documents from collection '{name}':")
                
                # Get metadata for all documents
                results = collection.get(limit=sample_size, include=["metadatas", "documents"])
                
                for i, (doc_id, doc_text, metadata) in enumerate(zip(results["ids"], results["documents"], results["metadatas"])):
                    logger.info(f"  Document {i+1}: ID={doc_id}, Metadata={metadata}")
                    logger.info(f"    Content preview: {doc_text[:100]}...")
                    
    except Exception as e:
        logger.error(f"Error checking collections: {str(e)}")

if __name__ == "__main__":
    logger.info("Checking ChromaDB database size and content")
    check_database_size()
    logger.info("\nChecking collections:")
    check_collections()