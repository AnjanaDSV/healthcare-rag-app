import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from ingestion.chunker import load_and_chunk
from ingestion.embedder import embed_and_store
from retrieval.retriever import retrieve
from generation.generator import generate
from evaluation.evaluator import evaluate

app = FastAPI(
    title="Healthcare RAG API",
    description="Retrieval-Augmented Generation over synthetic patient data",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOLD_CSV_DEFAULT = Path(__file__).parent.parent / "data" / "gold_clinical_summary.csv"


class IngestRequest(BaseModel):
    gold_csv_path: str = str(GOLD_CSV_DEFAULT)


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    run_evaluation: bool = True


@app.get("/health")
def health():
    return {"status": "ok", "service": "healthcare-rag-api"}


@app.post("/ingest")
def ingest(req: IngestRequest):
    csv_path = req.gold_csv_path
    if not Path(csv_path).exists():
        raise HTTPException(
            status_code=400,
            detail=f"Gold CSV not found at: {csv_path}. "
                   "Run dbt transforms first, then export the clinical_summary model to CSV.",
        )
    chunks = load_and_chunk(csv_path)
    if not chunks:
        raise HTTPException(status_code=400, detail="No chunks produced from the CSV.")
    result = embed_and_store(chunks)
    return result


@app.post("/query")
def query(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    chunks = retrieve(req.question, top_k=req.top_k)
    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="No relevant context found. Have you run /ingest yet?",
        )

    gen_result = generate(req.question, chunks)
    answer = gen_result["answer"]

    ragas_scores = None
    if req.run_evaluation:
        try:
            ragas_scores = evaluate(req.question, answer, chunks)
        except Exception as exc:
            ragas_scores = {"error": str(exc)}

    return {
        "question": req.question,
        "answer": answer,
        "sources": gen_result["sources"],
        "ragas_scores": ragas_scores,
        "usage": {
            "input_tokens": gen_result["input_tokens"],
            "output_tokens": gen_result["output_tokens"],
        },
    }


@app.get("/experiments")
def experiments():
    import mlflow

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "mlflow_runs/"))
    client = mlflow.tracking.MlflowClient()
    exps = client.search_experiments()
    runs = []
    for exp in exps:
        for run in client.search_runs(experiment_ids=[exp.experiment_id], max_results=20):
            runs.append(
                {
                    "run_id": run.info.run_id,
                    "run_name": run.info.run_name,
                    "status": run.info.status,
                    "start_time": run.info.start_time,
                    "params": run.data.params,
                    "metrics": run.data.metrics,
                }
            )
    return {"experiments": runs}
