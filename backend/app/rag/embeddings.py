from typing import List
from chromadb.utils import embedding_functions

def get_embedding_function():
    """
    Returns an embedding function for ChromaDB.
    Uses SentenceTransformer default 'all-MiniLM-L6-v2' or fallback default.
    """
    try:
        return embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
    except Exception as e:
        print(f"SentenceTransformer not available ({e}), using default embedding function.")
        return embedding_functions.DefaultEmbeddingFunction()
