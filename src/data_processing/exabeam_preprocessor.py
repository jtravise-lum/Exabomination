"""Document cleaner and preprocessing for Exabeam Content-Library-CIM2 repository."""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

from langchain.schema import Document

logger = logging.getLogger(__name__)


class ExabeamPreprocessor:
    """Cleans and preprocesses Exabeam Content-Library-CIM2 documents."""

    def __init__(self):
        """Initialize the Exabeam preprocessor."""
        # Patterns to clean up markdown content
        self.table_row_pattern = re.compile(r"\|\s*([^|]*)\s*\|")
        self.html_tag_pattern = re.compile(r"<[^>]*>")
        self.code_block_pattern = re.compile(r"```.*?```", re.DOTALL)
        self.link_pattern = re.compile(r"\[(.*?)\]\((.*?)\)")
        self.heading_pattern = re.compile(r"^#+\s+(.*?)$", re.MULTILINE)
        self.multi_newline_pattern = re.compile(r"\n{3,}")
        
        # Patterns to identify sections to exclude (like parser code)
        self.parser_content_pattern = re.compile(r"#### Parser Content.*?```.*?```", re.DOTALL)
        
        # Map of document types to specific cleaning functions
        self.cleaning_functions = {
            "use_case_detail": self._clean_use_case,
            "data_source": self._clean_data_source,
            "parser": self._clean_parser,
            "rules_models": self._clean_rules_models,
            # Add more document types as needed
        }

    def preprocess_documents(self, documents: List[Document]) -> List[Document]:
        """Preprocess a list of documents for improved extraction and chunking.

        Args:
            documents: List of documents to preprocess

        Returns:
            List of preprocessed documents
        """
        preprocessed_docs = []
        
        for document in documents:
            try:
                # Apply general markdown cleaning
                cleaned_content = self._clean_markdown(document.page_content)
                
                # Apply document type-specific cleaning
                doc_type = document.metadata.get("doc_type")
                if doc_type and doc_type in self.cleaning_functions:
                    cleaned_content = self.cleaning_functions[doc_type](cleaned_content)
                
                # Create a new document with cleaned content and original metadata
                cleaned_doc = Document(
                    page_content=cleaned_content,
                    metadata=document.metadata.copy()
                )
                
                # Only include if there's still meaningful content
                if cleaned_content.strip():
                    preprocessed_docs.append(cleaned_doc)
                else:
                    logger.warning(f"Skipping document with empty content after preprocessing: {document.metadata.get('source', 'unknown')}")
            except Exception as e:
                logger.error(f"Error preprocessing document {document.metadata.get('source', 'unknown')}: {str(e)}")
                # Include the original document if preprocessing fails
                preprocessed_docs.append(document)
        
        logger.info(f"Preprocessed {len(preprocessed_docs)} documents")
        return preprocessed_docs

    def _clean_markdown(self, content: str) -> str:
        """Clean general markdown syntax for better extraction.

        Args:
            content: Document content to clean

        Returns:
            Cleaned content
        """
        # Replace links with just the link text
        content = self.link_pattern.sub(r"\1", content)
        
        # Replace HTML tags (but preserve content between them)
        content = self.html_tag_pattern.sub("", content)
        
        # Extract and format headings for better context
        content = self.heading_pattern.sub(r"\n\1:", content)
        
        # Normalize whitespace
        content = content.replace("\t", " ")
        content = self.multi_newline_pattern.sub("\n\n", content)
        
        return content.strip()

    def _clean_use_case(self, content: str) -> str:
        """Clean use case documents specifically.

        Args:
            content: Document content to clean

        Returns:
            Cleaned content
        """
        # For use cases, extract the table headers and data
        # but format them in a more readable way
        lines = content.split("\n")
        result_lines = []
        
        in_table = False
        table_data = []
        
        for line in lines:
            # Detect table rows
            if "|" in line:
                in_table = True
                # Extract data from table cells
                matches = self.table_row_pattern.findall(line)
                if matches:
                    table_data.append([cell.strip() for cell in matches])
            elif in_table and line.strip() == "":
                # End of table, process the collected data
                if len(table_data) >= 2:  # Header row and separator row
                    headers = table_data[0]
                    for row in table_data[2:]:  # Skip header and separator
                        for i, cell in enumerate(row):
                            if i < len(headers) and cell.strip():
                                # Format as "Header: Cell content"
                                result_lines.append(f"{headers[i]}: {cell}")
                        result_lines.append("")  # Empty line between rows
                table_data = []
                in_table = False
            elif not in_table:
                result_lines.append(line)
        
        return "\n".join(result_lines)

    def _clean_data_source(self, content: str) -> str:
        """Clean data source documents specifically.

        Args:
            content: Document content to clean

        Returns:
            Cleaned content
        """
        # Remove parser content blocks
        content = self.parser_content_pattern.sub("", content)
        
        # For data sources, clean tables similar to use cases
        return self._clean_use_case(content)

    def _clean_parser(self, content: str) -> str:
        """Clean parser documents specifically.

        Args:
            content: Document content to clean

        Returns:
            Cleaned content
        """
        # For parsers, extract code blocks and summarize them
        # Remove detailed parser code while keeping the parser name and purpose
        code_blocks = self.code_block_pattern.findall(content)
        
        # Replace code blocks with a summary
        for code_block in code_blocks:
            summary = f"[Parser code: {len(code_block.splitlines())} lines]"
            content = content.replace(code_block, summary)
        
        return content

    def _clean_rules_models(self, content: str) -> str:
        """Clean rules and models documents specifically.

        Args:
            content: Document content to clean

        Returns:
            Cleaned content
        """
        # For rules and models, focus on the relationship between
        # event types, rules, and models
        lines = content.split("\n")
        result_lines = []
        
        # Handle the tabular data similar to use cases
        return self._clean_use_case(content)