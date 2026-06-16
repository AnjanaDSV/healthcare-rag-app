# Healthcare RAG App

Retrieval-Augmented Generation over synthetic patient data (Synthea), with a full MLOps stack.

---

## Architecture

```
Synthea CSVs  ──►  dbt (DuckDB)  ──►  Gold clinical_summary CSV
                                              │
                                    chunker.py (512-token chunks)
                                              │
                                    embedder.py (MiniLM-L6-v2)
                                              │
                                         Qdrant  ◄──  retriever.py  ◄──  User query
                                                              │
                                                       generator.py
                                                    (Claude claude-sonnet-4-6)
                                                              │
                                                       evaluator.py (RAGAS)
                                                              │
                                                     MLflow tracking
                                                              │
                                                    Next.js frontend
```

---

## Tech Stack

| Layer           | Technology                                    |
|-----------------|-----------------------------------------------|
| Backend API     | FastAPI + Python 3.11+                        |
| Vector DB       | Qdrant (Docker)                               |
| Embeddings      | `sentence-transformers/all-MiniLM-L6-v2`      |
| LLM             | Claude claude-sonnet-4-6 (Anthropic)                 |
| Data transforms | dbt-duckdb                                    |
| Experiment tracking | MLflow                                    |
| Evaluation      | RAGAS (faithfulness, relevancy, precision)    |
| Frontend        | Next.js 14                                    |
| Source data     | Synthea synthetic patients                    |

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop (for Qdrant)
- Anthropic API key

---

## Setup

### 1. Clone and install

```bash
cd healthcare-rag-app
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Start Qdrant + MLflow

```bash
docker-compose up -d
# Qdrant UI:  http://localhost:6333/dashboard
# MLflow UI:  http://localhost:5001
```

---

## Data Pipeline

### Step 1 — Copy Synthea CSVs

Copy `patients.csv` and `conditions.csv` from your Synthea output into `data/raw/`:

```
data/raw/patients.csv
data/raw/conditions.csv
```

If you have the `hipaa-phi-masking-engine` project, copy from `ingestion/samples/`.

### Step 2 — Run dbt transforms

```bash
cd dbt_transforms
dbt run
dbt test
# Export gold layer to CSV for ingestion
dbt run-operation export_gold   # or use DuckDB CLI (see below)
```

Export clinical_summary to CSV manually via DuckDB if needed:

```bash
python - <<'EOF'
import duckdb
con = duckdb.connect("data/healthcare.duckdb")
con.execute("COPY main.clinical_summary TO 'data/gold_clinical_summary.csv' (HEADER, DELIMITER ',')")
print("Exported.")
EOF
```

### Step 3 — Run ingestion pipeline (chunks → embeddings → Qdrant)

```bash
# Option A: via API endpoint
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"gold_csv_path": "data/gold_clinical_summary.csv"}'

# Option B: run backend then use the frontend button
```

---

## Running the App

### Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3001
```

---

## API Endpoints

| Method | Endpoint       | Description                              |
|--------|----------------|------------------------------------------|
| GET    | /health        | Service health check                     |
| POST   | /ingest        | Chunk, embed, and store gold CSV in Qdrant |
| POST   | /query         | Ask a clinical question; returns answer + RAGAS scores |
| GET    | /experiments   | List MLflow experiment history           |

### Example query

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What conditions does patient John Smith have?", "top_k": 5}'
```

---

## RAGAS Evaluation Results

RAGAS evaluates each query automatically and logs to MLflow.

| Metric             | Description                                          |
|--------------------|------------------------------------------------------|
| faithfulness       | Is the answer grounded in retrieved context?         |
| answer_relevancy   | Does the answer address the question?                |
| context_precision  | Are the retrieved chunks relevant to the question?   |

View results: http://localhost:5001 → Experiments → `ragas_evaluation`

---

## Project Structure

```
healthcare-rag-app/
├── backend/
│   ├── main.py                    # FastAPI app
│   ├── ingestion/
│   │   ├── chunker.py             # 512-token chunking with 50-token overlap
│   │   └── embedder.py            # MiniLM embeddings + Qdrant storage
│   ├── retrieval/
│   │   └── retriever.py           # Qdrant semantic search
│   ├── generation/
│   │   └── generator.py           # Claude API generation
│   └── evaluation/
│       └── evaluator.py           # RAGAS + MLflow logging
├── dbt_transforms/
│   ├── models/
│   │   ├── bronze/src_synthea.yml # Source definitions
│   │   ├── silver/                # Cleaned staging models
│   │   └── gold/clinical_summary.sql  # Narrative text for embedding
├── frontend/
│   └── pages/index.js             # Next.js UI (olive/dark theme)
├── data/raw/                      # Synthea CSVs go here
├── mlflow_runs/                   # MLflow artifact storage
├── docker-compose.yml             # Qdrant + MLflow containers
├── requirements.txt
└── .env.example
```

---

## Notes

- Patient data is **fully synthetic** (Synthea). No real PHI is used.
- To swap in your masked data from `hipaa-phi-masking-engine`, copy the masked CSVs into `data/raw/` and rerun the dbt pipeline.
- RAGAS uses LLM judges internally; set `ANTHROPIC_API_KEY` before running evaluation.
