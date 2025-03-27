"""Vector database integration for storing and retrieving document embeddings."""

import logging
import os
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple

from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from langchain.vectorstores.base import VectorStore
from chromadb import Client as ChromaClient
from chromadb.config import Settings

from src.config import CHROMA_DB_PATH, CHROMA_SERVER_HOST, CHROMA_SERVER_PORT
from src.data_processing.embeddings import MultiModalEmbeddingProvider, EmbeddingProvider

logger = logging.getLogger(__name__)


class CustomEmbeddingFunction:
    """Custom embedding function that works with the multi-modal embedding provider."""
    
    def __init__(self, embedding_provider: MultiModalEmbeddingProvider):
        """Initialize with a multi-modal embedding provider.
        
        Args:
            embedding_provider: The embedding provider to use
        """
        self.embedding_provider = embedding_provider
        
    def embed_documents(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> List[List[float]]:
        """Embed documents with appropriate model based on metadata.
        
        Args:
            texts: List of texts to embed
            metadatas: Optional list of metadata dictionaries
            
        Returns:
            List of embedding vectors
        """
        # Create document objects from texts and metadata
        documents = []
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            documents.append(Document(page_content=text, metadata=metadata))
        
        # Get embeddings with the most appropriate model for each document
        embedding_results = self.embedding_provider.embed_documents(documents)
        
        # Extract just the embedding vectors
        return [embedding for embedding, _ in embedding_results]
        
    def embed_query(self, text: str) -> List[float]:
        """Embed a query using the default text model.
        
        Args:
            text: Query text to embed
            
        Returns:
            Embedding vector
        """
        return self.embedding_provider.embed_query(text, query_type="text")


class VectorDatabase:
    """Interface for interacting with the vector database."""

    def __init__(
        self,
        embedding_provider: Union[EmbeddingProvider, MultiModalEmbeddingProvider],
        db_path: str = CHROMA_DB_PATH,
        collection_name: str = "exabeam_docs",
        use_server: bool = True,
        server_host: str = CHROMA_SERVER_HOST,
        server_port: int = CHROMA_SERVER_PORT,
    ):
        """Initialize the vector database.

        Args:
            embedding_provider: The embedding provider to use
            db_path: Path to the database for persistent storage
            collection_name: Name of the collection
            use_server: Whether to use ChromaDB server mode (vs. local mode)
            server_host: ChromaDB server host when in server mode
            server_port: ChromaDB server port when in server mode
        """
        self.embedding_provider = embedding_provider
        self.db_path = db_path
        self.collection_name = collection_name
        self.use_server = use_server
        self.server_host = server_host
        self.server_port = server_port
        self.vectorstore = None

        # Create a custom embedding function that works with our multi-modal provider
        self.embedding_function = CustomEmbeddingFunction(embedding_provider)

        # Ensure the database directory exists when using persistent storage
        if not use_server:
            os.makedirs(db_path, exist_ok=True)

        # Initialize or load the database
        self._init_vectorstore()

    def _init_vectorstore(self) -> None:
        """Initialize or load the vector store."""
        try:
            if self.use_server:
                logger.info(f"Connecting to ChromaDB server at {self.server_host}:{self.server_port}")
                
                # Use the HttpClient directly for better control over server connection
                from chromadb import HttpClient
                client = HttpClient(
                    host=self.server_host,
                    port=self.server_port
                )
                
                # Check if collection exists - ChromaDB v0.6.0 changes
                logger.info("Listing all collections")
                try:
                    collections = client.list_collections()
                    logger.info(f"Found collections: {collections}")
                    collection_exists = self.collection_name in collections
                    
                    if collection_exists:
                        logger.info(f"Found existing collection: {self.collection_name}")
                except Exception as e:
                    logger.warning(f"Error listing collections: {str(e)}")
                    # Try to get the collection directly as a fallback
                    try:
                        client.get_collection(name=self.collection_name)
                        collection_exists = True
                        logger.info(f"Collection {self.collection_name} exists (verified by direct access)")
                    except Exception as get_err:
                        logger.info(f"Collection {self.collection_name} does not exist: {str(get_err)}")
                        collection_exists = False
                
                if not collection_exists:
                    logger.info(f"Creating new collection: {self.collection_name}")
                    try:
                        # Create the collection with direct client
                        client.create_collection(name=self.collection_name)
                        logger.info(f"Collection created successfully: {self.collection_name}")
                        
                        # Give the server more time to process this request
                        import time
                        time.sleep(5.0)  # Increased wait time
                        
                    except Exception as create_err:
                        logger.warning(f"Collection creation failed: {str(create_err)}")
                        # Check if error is because collection already exists
                        if "already exists" in str(create_err).lower():
                            logger.info("Collection already exists, continuing")
                            collection_exists = True
                        else:
                            # Something else went wrong
                            raise
                
                # Now connect using direct ChromaDB client for better persistence control
                self._direct_client = client
                
                # Handle collection retrieval with robust retry logic
                max_retries = 5  # Increased retries
                retry_delay = 2.0  # Increased initial delay
                
                for retry in range(max_retries):
                    try:
                        logger.info(f"Attempting to get collection {self.collection_name} (attempt {retry+1}/{max_retries})")
                        # If collection wasn't found to exist already, try creating it again on subsequent attempts
                        if retry > 0 and not collection_exists:
                            try:
                                logger.info(f"Attempting to create collection again on retry {retry+1}")
                                client.create_collection(name=self.collection_name)
                                logger.info(f"Collection created on retry {retry+1}")
                            except Exception as retry_create_err:
                                logger.warning(f"Retry creation attempt failed: {str(retry_create_err)}")
                        
                        self._direct_collection = client.get_collection(name=self.collection_name)
                        logger.info(f"Successfully connected to collection {self.collection_name}")
                        break
                    except Exception as e:
                        logger.warning(f"Error getting collection (attempt {retry+1}/{max_retries}): {str(e)}")
                        if retry < max_retries - 1:
                            logger.info(f"Retrying in {retry_delay} seconds...")
                            import time
                            time.sleep(retry_delay)
                            retry_delay *= 1.5  # More gradual backoff
                        else:
                            logger.error(f"Failed to get collection after {max_retries} attempts")
                            raise
                
                # Still set up the LangChain wrapper for compatibility with other code
                self.vectorstore = Chroma(
                    collection_name=self.collection_name,
                    embedding_function=self.embedding_function,
                    client=client
                )
            else:
                logger.info(f"Initializing local ChromaDB at {self.db_path}")
                self.vectorstore = Chroma(
                    collection_name=self.collection_name,
                    embedding_function=self.embedding_function,
                    persist_directory=self.db_path,
                )
                self._direct_client = None
                self._direct_collection = None
            
            # Verify collection exists and count documents
            try:
                # Use direct collection for count when available
                if self._direct_collection:
                    count = self._direct_collection.count()
                else:
                    count = self.vectorstore._collection.count()
                logger.info(f"Vector database initialized with {count} documents")
            except Exception as count_err:
                logger.error(f"Error counting documents: {str(count_err)}")
                
        except Exception as e:
            logger.error(f"Error initializing vector database: {str(e)}")
            raise

    def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to the vector database.

        Args:
            documents: List of documents to add

        Returns:
            List of document IDs
        """
        if not documents:
            logger.warning("Attempting to add empty document list")
            return []

        logger.info(f"Adding {len(documents)} documents to vector database")
        
        try:
            # Generate IDs if not present
            ids = []
            for doc in documents:
                if "id" not in doc.metadata:
                    doc.metadata["id"] = str(uuid.uuid4())
                ids.append(doc.metadata["id"])
            
            # Add documents using the most appropriate method
            texts = [doc.page_content for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            embeddings = self.embedding_function.embed_documents(texts, metadatas)
            
            # Use direct ChromaDB client for server mode to ensure persistence
            if self.use_server and self._direct_collection:
                logger.info("Using direct ChromaDB client for adding documents")
                self._direct_collection.add(
                    documents=texts,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids
                )
                # ChromaDB v0.6.0 removed the _api.flush() method
                try:
                    # Try to use flush method if available
                    if hasattr(self._direct_client, '_api') and hasattr(self._direct_client._api, 'flush'):
                        logger.info("Explicitly flushing changes with _api.flush()")
                        self._direct_client._api.flush()
                    else:
                        logger.info("Flush method not available in this ChromaDB version - skipping")
                except Exception as flush_err:
                    logger.warning(f"Error flushing changes (non-critical): {str(flush_err)}")
            else:
                # Use LangChain's Chroma wrapper for local mode
                self.vectorstore._collection.add(
                    documents=texts,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids
                )
                # Persist if using local mode
                if not self.use_server:
                    self.vectorstore.persist()
            
            # Force verification of document addition to ensure persistence
            try:
                # Verify at least one document was added by trying to retrieve it
                verify_id = ids[0]
                
                # Use most direct method to verify
                if self.use_server and self._direct_collection:
                    verify_result = self._direct_collection.get(ids=[verify_id], include=["documents"])
                else:
                    verify_result = self.vectorstore._collection.get(ids=[verify_id], include=["documents"])
                
                if not verify_result["documents"]:
                    # If empty, try with a completely fresh client connection
                    logger.warning("Document not found on verification, attempting to reconnect...")

                    # Create a new client to check persistence
                    from chromadb import Client as ChromaClient
                    from chromadb.config import Settings
                    
                    verify_client = ChromaClient(
                        Settings(
                            chroma_server_host=self.server_host,
                            chroma_server_http_port=self.server_port
                        )
                    )
                    verify_collection = verify_client.get_collection(name=self.collection_name)
                    verify_result = verify_collection.get(ids=[verify_id], include=["documents"])
                    
                    if not verify_result["documents"]:
                        logger.error("Document still not found after reconnection - persistence failure detected")
                        
                        # Last resort: try adding documents directly with the fresh client
                        logger.warning("Attempting direct add via fresh client connection as last resort")
                        verify_collection.add(
                            documents=texts,
                            embeddings=embeddings,
                            metadatas=metadatas,
                            ids=ids
                        )
                        logger.info("Direct add attempt completed")
                    else:
                        logger.info("Document verified after reconnection - persistence confirmed")
                else:
                    logger.info("Document addition verified successfully")
                    
                # Verify the total count in the collection
                if self.use_server and self._direct_collection:
                    count = self._direct_collection.count()
                else:
                    count = self.vectorstore._collection.count()
                logger.info(f"Collection now contains {count} documents")
                
            except Exception as verify_err:
                logger.warning(f"Error during verification: {str(verify_err)}")
                
            logger.info(f"Added {len(ids)} documents to vector database")
            return ids
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {str(e)}")
            raise

    def similarity_search(
        self, query: str, k: int = 5, filter: Optional[Dict[str, Any]] = None,
        query_type: str = "text"
    ) -> List[Document]:
        """Search for similar documents.

        Args:
            query: The query string
            k: Number of results to return
            filter: Optional metadata filters
            query_type: Type of query ("text" or "code")

        Returns:
            List of similar documents
        """
        logger.info(f"Searching for documents similar to: {query[:50]}...")
        try:
            # Get the embedding for the query
            query_embedding = self.embedding_provider.embed_query(query, query_type=query_type)
            
            # Perform the search
            results = self.vectorstore.similarity_search_by_vector(
                query_embedding, k=k, filter=filter
            )
            
            logger.info(f"Found {len(results)} results for query")
            return results
        except Exception as e:
            logger.error(f"Error searching vector database: {str(e)}")
            raise

    def similarity_search_with_score(
        self, query: str, k: int = 5, filter: Optional[Dict[str, Any]] = None,
        query_type: str = "text"
    ) -> List[Tuple[Document, float]]:
        """Search for similar documents and return scores.

        Args:
            query: The query string
            k: Number of results to return
            filter: Optional metadata filters
            query_type: Type of query ("text" or "code")

        Returns:
            List of (document, score) tuples
        """
        logger.info(f"Searching with scores for documents similar to: {query[:50]}...")
        try:
            # Get the embedding for the query
            query_embedding = self.embedding_provider.embed_query(query, query_type=query_type)
            
            # Perform the search
            results = self.vectorstore.similarity_search_by_vector_with_relevance_scores(
                query_embedding, k=k, filter=filter
            )
            
            logger.info(f"Found {len(results)} scored results for query")
            return results
        except Exception as e:
            logger.error(f"Error searching vector database with scores: {str(e)}")
            raise

    def delete_collection(self) -> None:
        """Delete the entire collection from the database."""
        logger.warning(f"Deleting collection {self.collection_name}")
        try:
            if self.use_server:
                # Get the client directly to delete the collection
                client = ChromaClient(
                    Settings(
                        chroma_server_host=self.server_host,
                        chroma_server_http_port=self.server_port
                    )
                )
                
                # Check if collection exists before trying to delete
                collections = client.list_collections()
                collection_exists = False
                for coll_info in collections:
                    # Handle different versions of ChromaDB API
                    if hasattr(coll_info, 'name'):
                        coll_name = coll_info.name
                    elif isinstance(coll_info, dict) and 'name' in coll_info:
                        coll_name = coll_info['name']
                    else:
                        # If it's just a string or other object, convert to string
                        coll_name = str(coll_info)
                        
                    if coll_name == self.collection_name:
                        collection_exists = True
                        break
                
                if collection_exists:
                    # Delete collection directly with the client
                    client.delete_collection(self.collection_name)
                    logger.info(f"Collection {self.collection_name} deleted directly via client")
                else:
                    logger.warning(f"Collection {self.collection_name} not found, nothing to delete")
            else:
                # Use LangChain's delete_collection for local mode
                self.vectorstore.delete_collection()
                logger.info(f"Collection {self.collection_name} deleted via LangChain")
            
            # Reinitialize vectorstore
            self._init_vectorstore()
            logger.info("Vector store reinitialized")
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            raise


def get_vector_store() -> VectorDatabase:
    """Get or create a vector store instance.
    
    Returns:
        Initialized VectorDatabase instance
    """
    from src.data_processing.embeddings import MultiModalEmbeddingProvider
    
    # Initialize the embedding provider
    embedding_provider = MultiModalEmbeddingProvider()
    
    # Create vector database with default settings
    vector_db = VectorDatabase(
        embedding_provider=embedding_provider,
        # Use settings from config
        db_path=CHROMA_DB_PATH,
        collection_name="exabeam_docs",
        use_server=True,
        server_host=CHROMA_SERVER_HOST,
        server_port=CHROMA_SERVER_PORT
    )
    
    return vector_db
