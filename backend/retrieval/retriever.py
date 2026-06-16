import os
from typing import List, Dict, Any

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
COLLECTION = os.getenv("COLLECTION_NAME", "healthcare_rag")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
TOP_K = 5

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def retrieve(query: str, top_k: int = TOP_K) -> List[Dict[str, Any]]:
    """Embed query and return top-k similar chunks from Qdrant with scores."""
    model = _get_model()
    query_vec = model.encode([query])[0].tolist()

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    results = client.query_points(
        collection_name=COLLECTION,
        query=query_vec,
        limit=top_k,
        with_payload=True,
    ).points

    return [
        {
            "text": r.payload.get("text", ""),
            "patient_id": r.payload.get("patient_id", ""),
            "patient_name": r.payload.get("patient_name", ""),
            "condition_name": r.payload.get("condition_name", ""),
            "chunk_index": r.payload.get("chunk_index", 0),
            "score": round(r.score, 4),
        }
        for r in results
    ]
