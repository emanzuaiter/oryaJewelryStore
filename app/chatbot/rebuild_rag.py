import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.chatbot.rag_pipeline import build_vector_store

if __name__ == "__main__":
    print("Rebuilding vector store...")
    vs = build_vector_store()
    if vs:
        print("Success!")
    else:
        print("Failed - no documents found or other error.")
