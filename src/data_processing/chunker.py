"""Text chunking module for processing documents into vector database."""

import logging
from typing import List, Dict, Any, Optional

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from src.config import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)


class DocumentChunker:
    """Processes documents into chunks suitable for embedding and retrieval."""

    def __init__(
        self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP
    ):
        """Initialize the document chunker.

        Args:
            chunk_size: The size of each text chunk
            chunk_overlap: The amount of overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks.

        Args:
            documents: List of documents to split

        Returns:
            List of chunked documents
        """
        logger.info(f"Splitting {len(documents)} documents into chunks")
        chunked_documents = self.text_splitter.split_documents(documents)
        logger.info(f"Created {len(chunked_documents)} chunks")

        # Add chunk metadata
        for i, doc in enumerate(chunked_documents):
            doc.metadata["chunk_id"] = i

        return chunked_documents

    def split_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Split a text string into chunks.

        Args:
            text: The text to split
            metadata: Optional metadata to add to each chunk

        Returns:
            List of chunked documents
        """
        metadata = metadata or {}
        texts = self.text_splitter.split_text(text)
        
        documents = [
            Document(page_content=t, metadata={
                **metadata,
                "chunk_id": i
            })
            for i, t in enumerate(texts)
        ]
        
        logger.info(f"Split text into {len(documents)} chunks")
        return documents
