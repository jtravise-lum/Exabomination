import os
import sys
import chromadb

def main():
    try:
        print("Connecting to ChromaDB server...")
        client = chromadb.HttpClient(host="localhost", port=8000)
        
        print("\nGetting collections:")
        collections = client.list_collections()
        print(f"Server has {len(collections)} collections")
        
        # Try to get exabeam_docs collection specifically
        try:
            collection = client.get_collection("exabeam_docs")
            count = collection.count()
            print(f"Found 'exabeam_docs' collection with {count} documents")
            
            if count > 0:
                print("\nQuerying collection...")
                results = collection.query(
                    query_texts=["Exabeam security use cases"],
                    n_results=3
                )
                
                print(f"Query returned {len(results['documents'][0])} documents")
                
                # Print a snippet of first document if available
                if results['documents'][0]:
                    doc = results['documents'][0][0]
                    print(f"First document sample: {doc[:100]}..." if doc else "Empty document")
                    
                # Get metadata
                if results['metadatas'][0]:
                    meta = results['metadatas'][0][0]
                    print(f"First document metadata keys: {list(meta.keys())}")
            else:
                print("Collection exists but contains no documents\!")
                
        except Exception as e:
            print(f"Error accessing 'exabeam_docs' collection: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
