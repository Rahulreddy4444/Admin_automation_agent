from typing import List, Dict, Any
from app.rag.chroma_client import get_knowledge_collection
from app.rag.knowledge_base import ensure_knowledge_base_seeded

def query_knowledge_base(query: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieves the most semantically relevant documents from the ChromaDB knowledge base.
    """
    ensure_knowledge_base_seeded()
    collection = get_knowledge_collection()
    
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    formatted = []
    if results and "documents" in results and results["documents"]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
        distances = results["distances"][0] if "distances" in results and results["distances"] else [0.0] * len(docs)
        
        for doc, meta, dist in zip(docs, metas, distances):
            formatted.append({
                "content": doc,
                "metadata": meta,
                "similarity_score": round(1.0 - float(dist), 4) if dist is not None else 1.0
            })
    return formatted
