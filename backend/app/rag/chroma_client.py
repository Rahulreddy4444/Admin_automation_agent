import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings
from app.rag.embeddings import get_embedding_function

_chroma_client = None

def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(settings.CHROMADB_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMADB_DIR,
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True)
        )
    return _chroma_client

def get_knowledge_collection():
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    collection = client.get_or_create_collection(
        name="training_knowledge_base",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )
    return collection
