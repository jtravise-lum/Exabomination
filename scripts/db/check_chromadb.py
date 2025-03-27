import os
import sys
from pathlib import Path

# Add project root to path - works regardless of where the script is called from
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../.."))
sys.path.insert(0, project_root)

import chromadb
from chromadb.config import Settings

def main():
    print("Connecting to ChromaDB server...")
    client = chromadb.HttpClient(host="localhost", port=8000)
    
    print("\nGetting server info:")
    heartbeat = client.heartbeat()
    print(f"Server heartbeat: {heartbeat}")
    
    print("\nListing collections:")
    # In ChromaDB v0.6.0, list_collections returns a list of strings
    collection_names = client.list_collections()
    
    if not collection_names:
        print("No collections found!")
        
        # Try creating a collection to test server writes
        print("\nAttempting to create a test collection...")
        try:
            test_collection = client.create_collection(name="test_collection")
            print("Test collection created successfully!")
            
            # Get count
            count = test_collection.count()
            print(f"Test collection document count: {count}")
        except Exception as e:
            print(f"Error creating test collection: {e}")
    else:
        print(f"Found {len(collection_names)} collections:")
        
        # For each collection name in the list
        for collection_item in collection_names:
            # In v0.6.0, each item is a dict with a 'name' key
            if hasattr(collection_item, 'name'):
                coll_name = collection_item.name
            elif isinstance(collection_item, dict) and 'name' in collection_item:
                coll_name = collection_item['name']
            else:
                # If it's just a string (older version API)
                coll_name = str(collection_item)
                
            print(f"- Collection: {coll_name}")
            
            try:
                # Get the collection to inspect it
                collection = client.get_collection(name=coll_name)
                
                # Get collection stats
                count = collection.count()
                print(f"  - Documents: {count}")
                
                if count > 0:
                    print("  - Retrieving sample documents...")
                    
                    # Try to get some documents
                    results = collection.get(limit=5)
                    print(f"  - Sample metadata (from {len(results['metadatas'] if 'metadatas' in results else [])} results):")
                    
                    if 'metadatas' in results and results['metadatas']:
                        for i, meta in enumerate(results['metadatas']):
                            if meta:
                                print(f"    Doc {i+1}: {list(meta.keys())[:5]}")
                    
                    # Try a query
                    print("\n  - Executing a sample query:")
                    query_results = collection.query(
                        query_texts=["Exabeam security use cases"], 
                        n_results=5
                    )
                    
                    if 'documents' in query_results and query_results['documents']:
                        print(f"    Retrieved {len(query_results['documents'][0])} documents")
                        if query_results['documents'][0]:
                            sample = query_results['documents'][0][0][:100] + "..." if query_results['documents'][0][0] else "Empty result"
                            print(f"    First result sample: {sample}")
                else:
                    print("  - Collection is empty")
                
            except Exception as e:
                print(f"  - Error examining collection: {e}")
    
    # Check for our specific collection
    collection_name = "exabeam_docs"
    print(f"\nTrying to get specific collection '{collection_name}'...")
    try:
        collection = client.get_collection(name=collection_name)
        print(f"Found collection: {collection_name}")
        
        # Get document count
        count = collection.count()
        print(f"Document count: {count}")
        
        if count > 0:
            # Check if we can query it
            print("Executing a test query...")
            results = collection.query(
                query_texts=["Exabeam security"],
                n_results=2
            )
            
            print(f"Query returned {len(results['documents'][0])} documents")
            
            # Try to get raw documents
            print("Getting raw documents...")
            docs = collection.get(limit=2)
            if 'documents' in docs and docs['documents']:
                print(f"Retrieved {len(docs['documents'])} raw documents")
            else:
                print("No raw documents retrieved")
        
    except Exception as e:
        print(f"Error accessing collection: {e}")
        print("\nLet's check the Docker volume for files...")

if __name__ == "__main__":
    main()
