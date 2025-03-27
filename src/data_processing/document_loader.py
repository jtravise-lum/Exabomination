"""Document loader module for processing various document formats."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    UnstructuredMarkdownLoader,
)
from langchain.schema import Document

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".docx": Docx2txtLoader,
    ".md": UnstructuredMarkdownLoader,
}


class DocumentLoader:
    """Loader for multiple document formats with metadata extraction."""

    def __init__(self):
        """Initialize the document loader."""
        pass

    def load_document(self, file_path: Union[str, Path]) -> List[Document]:
        """Load a document from a file path and extract its content.

        Args:
            file_path: Path to the document file

        Returns:
            List of Document objects with content and metadata

        Raises:
            ValueError: If file format is not supported
        """
        file_path = Path(file_path) if isinstance(file_path, str) else file_path

        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} does not exist")

        extension = file_path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file format: {extension}. Supported formats: {list(SUPPORTED_EXTENSIONS.keys())}"
            )

        loader_cls = SUPPORTED_EXTENSIONS[extension]
        loader = loader_cls(str(file_path))

        try:
            documents = loader.load()
            logger.info(f"Loaded {len(documents)} document parts from {file_path}")

            # Add additional metadata
            for doc in documents:
                self._add_metadata(doc, file_path)

            return documents
        except Exception as e:
            logger.error(f"Error loading document {file_path}: {str(e)}")
            raise

    def load_directory(
        self, directory_path: Union[str, Path], recursive: bool = True
    ) -> List[Document]:
        """Load all supported documents from a directory.

        Args:
            directory_path: Path to the directory
            recursive: Whether to search recursively

        Returns:
            List of Document objects
        """
        directory_path = (
            Path(directory_path) if isinstance(directory_path, str) else directory_path
        )

        if not directory_path.exists() or not directory_path.is_dir():
            raise NotADirectoryError(f"{directory_path} is not a valid directory")

        documents = []
        pattern = "**/*" if recursive else "*"

        for ext in SUPPORTED_EXTENSIONS:
            for file_path in directory_path.glob(f"{pattern}{ext}"):
                try:
                    docs = self.load_document(file_path)
                    documents.extend(docs)
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {str(e)}")

        logger.info(
            f"Loaded total of {len(documents)} document parts from {directory_path}"
        )
        return documents

    def _add_metadata(self, document: Document, file_path: Path) -> None:
        """Add additional metadata to the document.

        Args:
            document: The document to add metadata to
            file_path: Path to the source file
        """
        # Ensure metadata exists
        if not hasattr(document, "metadata") or document.metadata is None:
            document.metadata = {}

        # Add file information
        document.metadata.update(
            {
                "source": str(file_path),
                "filename": file_path.name,
                "file_type": file_path.suffix[1:],  # Remove the dot
                "file_size": file_path.stat().st_size,
                "last_modified": file_path.stat().st_mtime,
            }
        )
