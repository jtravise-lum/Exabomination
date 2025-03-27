"""Specialized document loader for Exabeam Content-Library-CIM2 repository."""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

from langchain.schema import Document
from langchain_community.document_loaders import TextLoader

logger = logging.getLogger(__name__)


class ExabeamDocumentLoader:
    """Specialized loader for Exabeam Content-Library-CIM2 content."""

    def __init__(self, content_dir: str):
        """Initialize the Exabeam document loader.

        Args:
            content_dir: Path to the Exabeam Content-Library-CIM2 repository
        """
        self.content_dir = Path(content_dir)
        if not self.content_dir.exists() or not self.content_dir.is_dir():
            raise ValueError(f"Invalid Exabeam content directory: {content_dir}")
        
        # Define document categories and their paths
        self.content_categories = {
            "overview": [self.content_dir / "README.md"],
            "data_sources": [self.content_dir / "Exabeam Data Sources.md"],
            "use_cases": [self.content_dir / "Exabeam Use Cases.md"],
            "product_categories": [self.content_dir / "Exabeam Product Categories.md"],
            "correlation_rules": [self.content_dir / "Exabeam Correlation Rules.md"],
            "mitre_map": [self.content_dir / "MitreMap.md"],
            "use_case_details": list(self.content_dir.glob("UseCases/uc_*.md")),
            "ds_vendor_products": list(self.content_dir.glob("DS/*/*/ds_*.md")),
            "ds_parsers": list(self.content_dir.glob("DS/*/*/Ps/*.md")),
            "ds_rules_models": list(self.content_dir.glob("DS/*/*/RM/*.md")),
        }
        
        # Patterns to extract metadata
        self.vendor_pattern = re.compile(r"Vendor:\s+([^\n]+)")
        self.product_pattern = re.compile(r"Product:\s+([^\n]+)")
        self.usecase_pattern = re.compile(r"Use-Case:\s+\[(.*?)\]")
        self.mitre_pattern = re.compile(r"MITRE ATT&CK® TTP[s]?[:\s]+(.*?)(?=\n\n|\Z)")

    def load_document(self, file_path: Union[str, Path]) -> List[Document]:
        """Load a document from a file path and extract its content.

        Args:
            file_path: Path to the document file

        Returns:
            List of Document objects with content and metadata
        """
        file_path = Path(file_path) if isinstance(file_path, str) else file_path
        
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} does not exist")
            
        # Select the appropriate loader based on file extension
        extension = file_path.suffix.lower()
        if extension == ".md":
            # Use markdown loader for Exabeam content
            try:
                from langchain_community.document_loaders import UnstructuredMarkdownLoader
                loader = UnstructuredMarkdownLoader(str(file_path))
            except ImportError:
                # Fall back to text loader if unstructured is not installed
                logger.warning(f"UnstructuredMarkdownLoader not available, falling back to TextLoader for {file_path}")
                loader = TextLoader(str(file_path))
        else:
            # Default to text loader for other formats
            loader = TextLoader(str(file_path))
            
        try:
            # Load the document
            documents = loader.load()
            
            # Extract and add metadata
            for doc in documents:
                metadata = self._extract_metadata_from_content(doc.page_content, file_path)
                doc.metadata.update(metadata)
                
            return documents
        except Exception as e:
            logger.error(f"Error loading document {file_path}: {str(e)}")
            # Return empty list on error
            return []
            
    def load_directory(self, directory_path: Union[str, Path]) -> List[Document]:
        """Load all documents from a directory.

        Args:
            directory_path: Path to the directory

        Returns:
            List of Document objects with content and metadata
        """
        directory_path = Path(directory_path) if isinstance(directory_path, str) else directory_path
        
        if not directory_path.exists() or not directory_path.is_dir():
            raise ValueError(f"Invalid directory: {directory_path}")
            
        documents = []
        for file_path in directory_path.glob("**/*"):
            if file_path.is_file() and file_path.suffix.lower() in [".md", ".txt"]:
                try:
                    docs = self.load_document(file_path)
                    documents.extend(docs)
                except Exception as e:
                    logger.error(f"Error loading document {file_path}: {str(e)}")
                    
        return documents
    
    def _extract_metadata_from_content(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from document content and path.
        
        Args:
            content: Document content
            file_path: Path to the document file
            
        Returns:
            Dictionary of metadata extracted from content
        """
        metadata = {
            "source": str(file_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix[1:] if file_path.suffix else "",
        }
        
        # Add relative path to content directory
        try:
            rel_path = file_path.relative_to(self.content_dir)
            metadata["relative_path"] = str(rel_path)
        except ValueError:
            metadata["relative_path"] = str(file_path)
        
        # Determine document type from path
        if "DS" in str(file_path):
            metadata["doc_type"] = "data_source"
            
            # Extract vendor and product from path
            path_parts = file_path.parts
            ds_index = path_parts.index("DS") if "DS" in path_parts else -1
            
            if ds_index >= 0 and ds_index + 1 < len(path_parts):
                metadata["vendor"] = path_parts[ds_index + 1]
                
            if ds_index >= 0 and ds_index + 2 < len(path_parts):
                metadata["product"] = path_parts[ds_index + 2]
                
            # Check for parser or rule/model
            if "Ps" in str(file_path):
                metadata["content_type"] = "parser"
            elif "RM" in str(file_path):
                metadata["content_type"] = "rule_model"
            else:
                metadata["content_type"] = "data_source_overview"
                
        elif "UseCases" in str(file_path):
            metadata["doc_type"] = "use_case"
            
            # Extract use case name from filename
            if file_path.name.startswith("uc_") and file_path.name.endswith(".md"):
                use_case_name = file_path.name[3:-3].replace("_", " ")
                metadata["use_case_name"] = use_case_name
        
        # Extract metadata from content patterns
        vendor_match = self.vendor_pattern.search(content)
        if vendor_match:
            metadata["vendor"] = vendor_match.group(1).strip()
            
        product_match = self.product_pattern.search(content)
        if product_match:
            metadata["product"] = product_match.group(1).strip()
            
        usecase_match = self.usecase_pattern.search(content)
        if usecase_match:
            usecases = usecase_match.group(1).strip()
            # Store as comma-separated string instead of list for ChromaDB compatibility
            metadata["use_cases"] = ", ".join(uc.strip() for uc in usecases.split(","))
            
        mitre_match = self.mitre_pattern.search(content)
        if mitre_match:
            mitre_ids = mitre_match.group(1).strip()
            # Store as comma-separated string instead of list for ChromaDB compatibility
            metadata["mitre_attack"] = ", ".join(mid.strip() for mid in mitre_ids.split(","))
        
        return metadata
        
    def load_documents(self, categories: Optional[List[str]] = None) -> List[Document]:
        """Load all documents from specified categories.

        Args:
            categories: List of categories to load (if None, load all)

        Returns:
            List of Document objects with content and metadata
        """
        all_documents = []
        
        # Determine which categories to load
        if categories is None:
            categories = list(self.content_categories.keys())
        
        logger.info(f"Loading documents from categories: {categories}")
        
        for category in categories:
            if category not in self.content_categories:
                logger.warning(f"Unknown category: {category}")
                continue
                
            paths = self.content_categories[category]
            logger.info(f"Loading {len(paths)} documents from category: {category}")
            
            for path in paths:
                if not path.exists():
                    logger.warning(f"File does not exist: {path}")
                    continue
                    
                try:
                    # Load document and add metadata
                    document = self._load_document(path, category)
                    if document:
                        all_documents.append(document)
                except Exception as e:
                    logger.error(f"Error loading {path}: {str(e)}", exc_info=True)
        
        logger.info(f"Loaded {len(all_documents)} documents in total")
        return all_documents

    def _load_document(self, file_path: Path, category: str) -> Optional[Document]:
        """Load a single document and extract metadata.

        Args:
            file_path: Path to the document file
            category: Category of the document

        Returns:
            Document object with content and metadata
        """
        logger.debug(f"Loading document: {file_path}")
        
        try:
            # Use TextLoader to get the content
            loader = TextLoader(str(file_path))
            documents = loader.load()
            
            if not documents:
                logger.warning(f"No content found in {file_path}")
                return None
                
            # We only expect one document per file
            document = documents[0]
            
            # Add basic metadata
            document.metadata.update({
                "source": str(file_path),
                "filename": file_path.name,
                "category": category,
                "file_type": file_path.suffix[1:] if file_path.suffix else "",
            })
            
            # Extract additional metadata based on content and file path
            self._extract_metadata(document, file_path, category)
            
            return document
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            return None

    def _extract_metadata(self, document: Document, file_path: Path, category: str) -> None:
        """Extract metadata from document content and file path.

        Args:
            document: The document to add metadata to
            file_path: Path to the source file
            category: Category of the document
        """
        content = document.page_content
        rel_path = file_path.relative_to(self.content_dir)
        
        # Extract metadata based on file path and category
        if category == "use_case_details":
            # Extract use case name from filename (format: uc_name.md)
            filename = file_path.stem
            if filename.startswith("uc_"):
                use_case_name = filename[3:].replace("_", " ")
                document.metadata["use_case_name"] = use_case_name
                document.metadata["doc_type"] = "use_case_detail"
        
        elif category == "ds_vendor_products":
            # Extract vendor and product from path or content
            parts = list(rel_path.parts)
            if len(parts) >= 3 and parts[0] == "DS":
                document.metadata["vendor"] = parts[1]
                document.metadata["product"] = parts[2]
                document.metadata["doc_type"] = "data_source"
                
                # Try to extract from content as well for verification
                vendor_match = self.vendor_pattern.search(content)
                product_match = self.product_pattern.search(content)
                
                if vendor_match:
                    document.metadata["vendor_name"] = vendor_match.group(1).strip()
                if product_match:
                    document.metadata["product_name"] = product_match.group(1).strip()
        
        elif category == "ds_parsers":
            # Extract parser information
            document.metadata["doc_type"] = "parser"
            
            # Extract vendor and product from path
            parts = list(rel_path.parts)
            if len(parts) >= 5 and parts[0] == "DS" and parts[3] == "Ps":
                document.metadata["vendor"] = parts[1]
                document.metadata["product"] = parts[2]
                document.metadata["parser_name"] = file_path.stem
        
        elif category == "ds_rules_models":
            # Extract rules and models information
            document.metadata["doc_type"] = "rules_models"
            
            # Extract vendor, product, and use case from path and content
            parts = list(rel_path.parts)
            if len(parts) >= 5 and parts[0] == "DS" and parts[3] == "RM":
                document.metadata["vendor"] = parts[1]
                document.metadata["product"] = parts[2]
                
                # Extract use case from filename or content
                filename = file_path.stem
                if filename.startswith("r_m_"):
                    parts = filename.split("_")
                    if len(parts) > 3:
                        use_case = "_".join(parts[3:])
                        document.metadata["use_case"] = use_case.replace("_", " ")
                
                # Try to extract from content
                usecase_match = self.usecase_pattern.search(content)
                if usecase_match:
                    document.metadata["use_case_name"] = usecase_match.group(1).strip()
        
        # Extract MITRE ATT&CK information if present
        mitre_match = self.mitre_pattern.search(content)
        if mitre_match:
            mitre_text = mitre_match.group(1).strip()
            ttps = [ttp.strip() for ttp in re.split(r'<br>|,', mitre_text) if ttp.strip()]
            if ttps:
                # Store as comma-separated string instead of list for ChromaDB compatibility
                document.metadata["mitre_ttps"] = ", ".join(ttps)