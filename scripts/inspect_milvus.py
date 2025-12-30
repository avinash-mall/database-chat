
import os
import sys
import inspect
from dotenv import load_dotenv

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from vanna.integrations.milvus import MilvusAgentMemory
    print("Successfully imported MilvusAgentMemory")
    
    # Try to print source of _get_collection
    if '_get_collection' in dir(MilvusAgentMemory):
        print("\nSource of _get_collection:")
        print(inspect.getsource(MilvusAgentMemory._get_collection))
    else:
        print("_get_collection not found")
        
    # Try to print source of save_text_memory
    if 'save_text_memory' in dir(MilvusAgentMemory):
        print("\nSource of save_text_memory:")
        print(inspect.getsource(MilvusAgentMemory.save_text_memory))
        
except ImportError as e:
    print(f"Error importing MilvusAgentMemory: {e}")
except Exception as e:
    print(f"Error inspecting: {e}")
