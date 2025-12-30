
import os
import sys
from pymilvus import connections, utility, Collection, FieldSchema, CollectionSchema, DataType
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env
if os.path.exists('.env'):
    load_dotenv('.env')

HOST = os.getenv("MILVUS_HOST", "localhost")
PORT = os.getenv("MILVUS_PORT", "19530")
COLLECTION_NAME = os.getenv("MILVUS_COLLECTION", "vanna_memory")
DIMENSION = 384  # Default for Vanna MilvusAgentMemory (all-MiniLM-L6-v2)

print(f"Connecting to Milvus at {HOST}:{PORT}...")

try:
    connections.connect(host=HOST, port=PORT)
    print("Connected successfully.")
    
    if utility.has_collection(COLLECTION_NAME):
        print(f"Collection '{COLLECTION_NAME}' already exists.")
        col = Collection(COLLECTION_NAME)
        print(f"Schema: {col.schema}")
        print(f"Count: {col.num_entities}")
    else:
        print(f"Collection '{COLLECTION_NAME}' NOT FOUND. Creating it...")
        
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIMENSION),
            FieldSchema(name="question", dtype=DataType.VARCHAR, max_length=2000),
            FieldSchema(name="tool_name", dtype=DataType.VARCHAR, max_length=200),
            FieldSchema(name="args_json", dtype=DataType.VARCHAR, max_length=5000),
            FieldSchema(name="timestamp", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="success", dtype=DataType.BOOL),
            FieldSchema(name="metadata_json", dtype=DataType.VARCHAR, max_length=5000),
        ]

        schema = CollectionSchema(fields=fields, description="Tool usage memories")
        collection = Collection(name=COLLECTION_NAME, schema=schema)

        # Create index for vector field
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "IP",
            "params": {"nlist": 128},
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        
        print(f"Successfully created collection '{COLLECTION_NAME}' with dim={DIMENSION}")

        # Verify load
        collection.load()
        print("Collection loaded.")
        
except Exception as e:
    print(f"Error initializing Milvus: {e}")
