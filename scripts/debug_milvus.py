
import os
import sys
from pymilvus import connections, utility, Collection
from dotenv import load_dotenv

# Add parent directory to path to import config if needed, but we'll read env directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env
if os.path.exists('.env'):
    load_dotenv('.env')

HOST = os.getenv("MILVUS_HOST", "localhost")
PORT = os.getenv("MILVUS_PORT", "19530")
COLLECTION_NAME = os.getenv("MILVUS_COLLECTION", "vanna_memory")

print(f"Connecting to Milvus at {HOST}:{PORT}...")

try:
    connections.connect(host=HOST, port=PORT)
    print("Connected successfully.")
    
    collections = utility.list_collections()
    print(f"Existing collections: {collections}")
    
    if COLLECTION_NAME in collections:
        print(f"Collection '{COLLECTION_NAME}' FOUND.")
        col = Collection(COLLECTION_NAME)
        print(f"Schema: {col.schema}")
        print(f"Count: {col.num_entities}")
    else:
        print(f"Collection '{COLLECTION_NAME}' NOT FOUND.")
        print("This is likely the cause of the errors. The collection needs to be initialized.")
        
except Exception as e:
    print(f"Error connecting to Milvus: {e}")
