"""Specialized processor for Exabeam Content-Library-CIM2 repository content."""

import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
import re

from langchain.schema import Document

from src.data_processing.document_loader import DocumentLoader
from src.data_processing.chunker import DocumentChunker

logger = logging.getLogger(__name__)


class ExabeamContentProcessor:
    """Processes Exabeam Content-Library-CIM2 repository content for RAG."""

    def __init__(
        self,
        content_dir: str,
        document_loader: Optional[DocumentLoader] = None,
        document_chunker: Optional[DocumentChunker] = None,
    ):
        """Initialize the Exabeam content processor.

        Args:
            content_dir: Path to the Exabeam Content-Library-CIM2 repository
            document_loader: Optional custom document loader
            document_chunker: Optional custom document chunker
        """
        self.content_dir = Path(content_dir)
        if not self.content_dir.exists() or not self.content_dir.is_dir():
            raise ValueError(f"Invalid Exabeam content directory: {content_dir}")

        self.document_loader = document_loader or DocumentLoader()
        self.document_chunker = document_chunker or DocumentChunker()
        
        # Map of document types to directories/patterns
        self.content_map = {
            "overview": [self.content_dir / "README.md"],
            "data_sources": [self.content_dir / "Exabeam Data Sources.md"],
            "use_cases": [self.content_dir / "Exabeam Use Cases.md"],
            "detailed_use_cases": [self.content_dir],  # If UseCases directly specified
            "product_categories": [self.content_dir / "Exabeam Product Categories.md"],
            "correlation_rules": [self.content_dir / "Exabeam Correlation Rules.md"],
            "data_source_details": [self.content_dir / "DS"],
            "mitre": [self.content_dir / "MitreMap.md"],
        }
        
        # Check if we're directly in UseCases directory
        if self.content_dir.name == "UseCases":
            logger.info("Detected direct UseCases directory")
            self.content_map["detailed_use_cases"] = [self.content_dir]
        
        # Files to exclude (if any)
        self.exclude_patterns = [
            r"\.git/",
            r"node_modules/",
            r"\.gitignore",
        ]

    def process_content(self) -> List[Document]:
        """Process all Exabeam content for ingestion into the vector database.

        Returns:
            List of processed document chunks
        """
        logger.info(f"Starting processing of Exabeam content from {self.content_dir}")
        
        all_documents = []
        
        # Process main markdown files first (more structured content)
        main_files = [
            self.content_map["overview"][0],
            self.content_map["data_sources"][0],
            self.content_map["use_cases"][0],
            self.content_map["product_categories"][0],
            self.content_map["correlation_rules"][0],
            self.content_map["mitre"][0],
        ]
        
        for file_path in main_files:
            if file_path.exists():
                logger.info(f"Processing main file: {file_path}")
                try:
                    docs = self.document_loader.load_document(file_path)
                    # Add document type metadata
                    doc_type = self._get_doc_type_for_path(file_path)
                    for doc in docs:
                        doc.metadata["doc_type"] = doc_type
                        doc.metadata["content_section"] = "main"
                    
                    # Chunk the documents
                    chunked_docs = self.document_chunker.split_documents(docs)
                    all_documents.extend(chunked_docs)
                    logger.info(f"Added {len(chunked_docs)} chunks from {file_path}")
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
        
        # Process detailed use cases
        use_case_dir = self.content_map["detailed_use_cases"][0]
        logger.info(f"Checking use case directory: {use_case_dir}")
        
        if use_case_dir.exists():
            logger.info(f"Processing use case files from {use_case_dir}")
            try:
                # Check if the directory contains uc_* files directly
                uc_files = list(use_case_dir.glob("uc_*.md"))
                if uc_files:
                    logger.info(f"Found {len(uc_files)} use case files directly in directory")
                    
                    # Load each file individually
                    use_case_docs = []
                    for file_path in uc_files:
                        try:
                            docs = self.document_loader.load_document(file_path)
                            use_case_docs.extend(docs)
                        except Exception as file_e:
                            logger.error(f"Error loading use case file {file_path}: {str(file_e)}")
                else:
                    # Try loading the entire directory as usual
                    use_case_docs = self.document_loader.load_directory(use_case_dir)
                    
                # Add document type metadata
                for doc in use_case_docs:
                    doc.metadata["doc_type"] = "detailed_use_case"
                    doc.metadata["content_section"] = "use_case"
                    # Extract use case name from filename
                    filename = Path(doc.metadata.get("source", "")).name
                    if filename.startswith("uc_") and filename.endswith(".md"):
                        use_case_name = filename[3:-3].replace("_", " ")
                        doc.metadata["use_case_name"] = use_case_name
                
                # Chunk the documents
                chunked_docs = self.document_chunker.split_documents(use_case_docs)
                all_documents.extend(chunked_docs)
                logger.info(f"Added {len(chunked_docs)} chunks from {len(use_case_docs)} use case files")
            except Exception as e:
                logger.error(f"Error processing use case files: {str(e)}")
        
        # Process data source details - these will be numerous
        ds_dir = self.content_map["data_source_details"][0]
        logger.info(f"Checking data source directory: {ds_dir}")
        if ds_dir.exists():
            logger.info(f"Processing data source files from {ds_dir}")
            try:
                # We'll process the DS directory more selectively to avoid overwhelming the system
                # Get all vendor directories
                vendor_dirs = [d for d in ds_dir.iterdir() if d.is_dir()]
                logger.info(f"Found {len(vendor_dirs)} vendor directories")
                
                for vendor_dir in vendor_dirs:
                    vendor_name = vendor_dir.name
                    # Process the important README.md, RM and Ps files that contain key info
                    for root, dirs, files in os.walk(vendor_dir):
                        for file in files:
                            if file.endswith(".md") and not self._should_exclude(os.path.join(root, file)):
                                file_path = Path(os.path.join(root, file))
                                try:
                                    file_docs = self.document_loader.load_document(file_path)
                                    # Add document type and vendor metadata
                                    for doc in file_docs:
                                        doc.metadata["doc_type"] = "data_source_detail"
                                        doc.metadata["content_section"] = "data_source"
                                        doc.metadata["vendor_name"] = vendor_name
                                        
                                        # Try to extract product name from path
                                        rel_path = str(file_path.relative_to(vendor_dir))
                                        parts = rel_path.split(os.sep)
                                        if len(parts) > 0:
                                            doc.metadata["product_name"] = parts[0]
                                    
                                    # Chunk the documents
                                    chunked_docs = self.document_chunker.split_documents(file_docs)
                                    all_documents.extend(chunked_docs)
                                except Exception as e:
                                    logger.error(f"Error processing {file_path}: {str(e)}")
            except Exception as e:
                logger.error(f"Error processing data source details: {str(e)}")
        
        logger.info(f"Completed processing Exabeam content. Generated {len(all_documents)} document chunks")
        return all_documents

    def _get_doc_type_for_path(self, file_path: Path) -> str:
        """Determine the document type based on the file path.

        Args:
            file_path: Path to the document file

        Returns:
            Document type string
        """
        str_path = str(file_path)
        for doc_type, paths in self.content_map.items():
            for path in paths:
                if str(path) in str_path:
                    return doc_type
        return "unknown"

    def _should_exclude(self, file_path: str) -> bool:
        """Check if a file path should be excluded from processing.

        Args:
            file_path: Path to check

        Returns:
            True if the file should be excluded, False otherwise
        """
        for pattern in self.exclude_patterns:
            if re.search(pattern, file_path):
                return True
        return False
