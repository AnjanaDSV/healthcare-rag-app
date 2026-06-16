import os
import uuid
import mlflow
from pathlib import Path
from typing import List, Dict, Any

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv

load_dotenv()

EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
COLLECTION = os.getenv("COLLECTION_NAME", "healthcare_rag")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# Resolve MLflow URI to absolute path anchored at project root (backend/ingestion/../../)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_raw_uri = os.getenv("MLFLOW_TRACKING_URI", "mlflow_runs/")
MLFLOW_URI = (
    _raw_uri
    if _raw_uri.startswith(("sqlite:", "http:", "https:", "file:"))
    else str(_PROJECT_ROOT / _raw_uri)
)

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def _get_qdrant() -> QdrantClient:
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def _ensure_collection(client: QdrantClient, vector_size: int) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def embed_and_store(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Embed chunks, store in Qdrant, and log experiment to MLflow."""
    model = _get_model()
    texts = [c["text"] for c in chunks]

    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment("healthcare_rag")
    with mlflow.start_run(run_name="ingestion"):
        mlflow.log_param("embed_model", EMBED_MODEL)
        mlflow.log_param("collection", COLLECTION)
        mlflow.log_param("total_chunks", len(chunks))

        embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
        vector_size = embeddings.shape[1]

        client = _get_qdrant()
        _ensure_collection(client, vector_size)

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embeddings[i].tolist(),
                payload={
                    "text": chunks[i]["text"],
                    "patient_id": chunks[i]["patient_id"],
                    "patient_name": chunks[i]["patient_name"],
                    "condition_name": chunks[i]["condition_name"],
                    "chunk_index": chunks[i]["chunk_index"],
                },
            )
            for i in range(len(chunks))
        ]
        client.upsert(collection_name=COLLECTION, points=points)

        mlflow.log_metric("vector_size", vector_size)
        run_id = mlflow.active_run().info.run_id

    return {
        "status": "success",
        "chunks_stored": len(chunks),
        "collection": COLLECTION,
        "embed_model": EMBED_MODEL,
        "mlflow_run_id": run_id,
    }
