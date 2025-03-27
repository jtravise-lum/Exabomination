#!/usr/bin/env python3
"""Initialize the vector database with Exabeam content."""

import argparse
import logging
import os
import sys
import json
from pathlib import Path

from src.config import (
    CHROMA_DB_PATH, 
    CHROMA_SERVER_HOST, 
    CHROMA_SERVER_PORT
)
from src.data_processing.exabeam_ingestion import ExabeamIngestionPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Initialize the vector database with Exabeam content.")
    parser.add_argument(
        "--content-dir",
        type=str,
        default=os.path.join(Path(__file__).parent.parent, "data", "content-library-cim2"),
        help="Path to the Exabeam Content-Library-CIM2 repository",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=CHROMA_DB_PATH,
        help=f"Path to the vector database (default: {CHROMA_DB_PATH})",
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default="exabeam_docs",
        help="Name of the vector database collection",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the database before initialization",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of documents to process in each batch",
    )
    parser.add_argument(
        "--use-server",
        action="store_true",
        default=True,
        help="Use ChromaDB server mode (default: True)",
    )
    parser.add_argument(
        "--server-host",
        type=str,
        default=CHROMA_SERVER_HOST,
        help=f"ChromaDB server host (default: {CHROMA_SERVER_HOST})",
    )
    parser.add_argument(
        "--server-port",
        type=int,
        default=CHROMA_SERVER_PORT,
        help=f"ChromaDB server port (default: {CHROMA_SERVER_PORT})",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify the ingestion with a test query",
    )
    parser.add_argument(
        "--stats-file",
        type=str,
        default="ingestion_stats.json",
        help="File to write ingestion statistics to",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers for embedding process",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar display",
    )
    return parser.parse_args()


def main():
    """Initialize the database with Exabeam content."""
    args = parse_args()

    logger.info(f"Initializing database at {args.db_path}")
    logger.info(f"Using content from {args.content_dir}")
    logger.info(f"Collection name: {args.collection_name}")
    logger.info(f"Using server mode: {args.use_server}")
    if args.use_server:
        logger.info(f"Server host: {args.server_host}")
        logger.info(f"Server port: {args.server_port}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Reset database: {args.reset}")

    try:
        # Initialize the ingestion pipeline
        pipeline = ExabeamIngestionPipeline(
            content_dir=args.content_dir,
            db_path=args.db_path,
            collection_name=args.collection_name,
            use_server=args.use_server,
            server_host=args.server_host,
            server_port=args.server_port,
            batch_size=args.batch_size,
            max_threads=args.workers,
            disable_progress_bar=args.no_progress,
        )
        
        # Run the ingestion pipeline
        stats = pipeline.run(reset_db=args.reset)
        
        # Save statistics to file
        if args.stats_file:
            stats_path = os.path.join(Path(__file__).parent.parent, args.stats_file)
            with open(stats_path, 'w') as f:
                json.dump(stats, f, indent=2)
            logger.info(f"Saved ingestion statistics to {stats_path}")
        
        # Verify ingestion if requested
        if args.verify:
            logger.info("Verifying ingestion with test query")
            results = pipeline.verify_ingestion("Exabeam security use cases")
            logger.info(f"Retrieved {len(results)} documents")
        
        logger.info(f"Database initialization completed successfully. Summary:")
        logger.info(f"  - Total documents processed: {stats['total_documents']}")
        logger.info(f"  - Successfully embedded: {stats['successful_chunks']}")
        logger.info(f"  - Failed to embed: {stats['failed_chunks']}")
        if stats['processing_time'] is not None:
            logger.info(f"  - Total processing time: {stats['processing_time']:.2f} seconds")
        else:
            logger.info("  - Total processing time: N/A")
        
        return 0
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())