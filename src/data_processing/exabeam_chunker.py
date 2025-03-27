"""Document chunking strategies for Exabeam Content-Library-CIM2 repository."""

import logging
import re
from typing import Dict, List, Any, Optional, Callable, Union

from langchain.schema import Document
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)

logger = logging.getLogger(__name__)


class ExabeamChunker:
    """Advanced document chunking for Exabeam Content-Library-CIM2 documents."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        keep_separator: bool = True,
    ):
        """Initialize the Exabeam document chunker.

        Args:
            chunk_size: The size of each text chunk
            chunk_overlap: The amount of overlap between chunks
            keep_separator: Whether to keep the separator in the chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.keep_separator = keep_separator
        
        # Default text splitter for general content
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
        )
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks.

        Args:
            documents: List of documents to split

        Returns:
            List of chunked documents
        """
        logger.info(f"Splitting {len(documents)} documents into chunks using Exabeam chunker")
        
        all_chunks = []
        for doc in documents:
            # Apply different chunking strategies based on document type
            chunks = self._split_document_by_type(doc)
            all_chunks.extend(chunks)
            
        # Add chunk IDs
        for i, chunk in enumerate(all_chunks):
            chunk.metadata["chunk_id"] = i
            
        logger.info(f"Created {len(all_chunks)} chunks")
        return all_chunks
    
    def _split_document_by_type(self, document: Document) -> List[Document]:
        """Apply document-specific chunking strategy.
        
        Args:
            document: Document to split
            
        Returns:
            List of document chunks
        """
        doc_type = document.metadata.get("doc_type", "unknown")
        content_type = document.metadata.get("content_type", "unknown")
        
        # Specialized chunking for different document types
        if doc_type == "data_source" and content_type == "parser":
            # For parsers, try to keep the document intact if possible
            if len(document.page_content) <= self.chunk_size * 1.5:
                return [document]
            else:
                return self.text_splitter.split_documents([document])
                
        elif doc_type == "use_case":
            # For use cases, split by sections
            return self._split_by_sections(document)
            
        else:
            # Default fallback - use recursive text splitter
            return self.text_splitter.split_documents([document])
    
    def _split_by_sections(self, document: Document) -> List[Document]:
        """Split document by markdown sections.
        
        Args:
            document: Document to split
            
        Returns:
            List of document chunks
        """
        text = document.page_content
        metadata = document.metadata.copy()
        
        # Simple section splitting by markdown headers
        section_pattern = r"(^|\n)#{1,3}\s+.+?(?=\n#{1,3}\s+|\Z)"
        sections = re.findall(section_pattern, text, re.DOTALL)
        
        if len(sections) <= 1:
            # If no sections found, fall back to default chunking
            return self.text_splitter.split_documents([document])
        
        # Create document for each section
        chunks = []
        for i, section in enumerate(sections):
            if len(section.strip()) == 0:
                continue
                
            # Create a new metadata dict for this section
            section_metadata = metadata.copy()
            section_metadata["section_id"] = i
            
            # Extract section title
            title_match = re.match(r"(^|\n)(#{1,3})\s+(.+?)($|\n)", section)
            if title_match:
                section_metadata["section_title"] = title_match.group(3).strip()
                section_metadata["section_level"] = len(title_match.group(2))
            
            # Create document for this section
            chunks.append(Document(
                page_content=section.strip(),
                metadata=section_metadata
            ))
        
        # If section chunks are still large, split them further
        if any(len(chunk.page_content) > self.chunk_size for chunk in chunks):
            return self.text_splitter.split_documents(chunks)
        
        return chunks