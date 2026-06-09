import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.chatbot.rag_pipeline import build_product_index

if __name__ == "__main__":
    print("Building product semantic search index...")
    vs = build_product_index()
    if vs:
        print("Success! Product index is ready.")
    else:
        print("Failed - check if you have products in the database and OPENAI_API_KEY is set.")
