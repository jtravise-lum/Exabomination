import chromadb
import time

client = chromadb.HttpClient()
print("Checking collections...")

# List all collections
collections = client.list_collections()
print(f"Found {len(collections)} collections:")
for coll in collections:
    print(f"  - {coll}")

# Try to get exabeam_docs collection
try:
    print("\nChecking exabeam_docs collection...")
    collection = client.get_collection("exabeam_docs")
    count = collection.count()
    print(f"Collection 'exabeam_docs' has {count} documents")
    
    # If documents exist, try to query them
    if count > 0:
        print("\nTrying a test query...")
        results = collection.query(
            query_texts=["Exabeam security"],
            n_results=min(count, 5)
        )
        print(f"Query returned {len(results['documents'][0] if 'documents' in results and results['documents'] else [])} documents")
        
        # Get some sample IDs
        print("\nGetting a few document IDs...")
        docs = collection.get(limit=min(count, 5))
        if 'ids' in docs:
            print(f"Sample IDs: {docs['ids']}")
        
        # Try one more approach - peek
        print("\nTrying to get all collections with peek...")
        all_colls = client._client.list_collections()
        for coll_info in all_colls:
            if hasattr(coll_info, 'name'):
                print(f"Collection: {coll_info.name}, Count: {coll_info.count}")
            else:
                print(f"Collection info: {coll_info}")
except Exception as e:
    print(f"Error getting collection: {e}")

print("\nChecking current time:", time.strftime("%Y-%m-%d %H:%M:%S"))

