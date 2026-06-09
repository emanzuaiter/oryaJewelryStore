import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.chatbot.rag_pipeline import query_rag

if __name__ == "__main__":
    q = "test" # Use English to avoid encoding issues
    print(f"Querying: {q}")
    try:
        result = query_rag(q)
        print(f"Success! Found context length: {len(result)}")
    except Exception as e:
        print(f"Failed: {e}")
