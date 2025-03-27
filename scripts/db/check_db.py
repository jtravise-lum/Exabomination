import chromadb

client = chromadb.HttpClient()
print("Collections:")
for coll in client.list_collections():
    print(f" - {coll}")

