import os
from typing import List, Dict, Any

import mlflow
from dotenv import load_dotenv

load_dotenv()

MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "mlflow_runs/")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
JUDGE_MODEL = os.getenv("RAGAS_JUDGE_MODEL", "claude-sonnet-4-6")
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def _build_ragas_dataset(query: str, answer: str, chunks: List[Dict[str, Any]]):
    """Build a HuggingFace dataset compatible with RAGAS evaluate()."""
    from datasets import Dataset

    contexts = [c["text"] for c in chunks]
    return Dataset.from_dict(
        {
            "question": [query],
            "answer": [answer],
            "contexts": [contexts],
            "ground_truth": [answer],   # self-referential; replace with gold labels when available
        }
    )


def evaluate(
    query: str,
    answer: str,
    chunks: List[Dict[str, Any]],
) -> Dict[str, float]:
    """Run RAGAS evaluation and log scores to MLflow. Returns score dict."""
    from anthropic import Anthropic
    from langchain_community.embeddings import HuggingFaceEmbeddings as LCHuggingFaceEmbeddings
    from ragas import evaluate as ragas_evaluate
    from ragas.embeddings.base import LangchainEmbeddingsWrapper
    from ragas.llms import llm_factory
    from ragas.metrics import faithfulness, answer_relevancy, context_precision

    judge_llm = llm_factory(
        JUDGE_MODEL,
        provider="anthropic",
        client=Anthropic(api_key=ANTHROPIC_API_KEY),
        max_tokens=4096,
    )
    # Anthropic rejects requests that set both temperature and top_p; ragas's
    # InstructorLLM defaults to sending both for every provider.
    judge_llm.model_args.pop("top_p", None)
    judge_llm.model_args["temperature"] = 0.0
    # answer_relevancy still calls the legacy embed_query() interface, which the
    # modern ragas.embeddings.HuggingFaceEmbeddings (embed_text-only) doesn't implement.
    judge_embeddings = LangchainEmbeddingsWrapper(
        LCHuggingFaceEmbeddings(model_name=EMBED_MODEL)
    )

    dataset = _build_ragas_dataset(query, answer, chunks)
    result = ragas_evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision],
        llm=judge_llm,
        embeddings=judge_embeddings,
    )

    def _mean(metric: str) -> float:
        values = result[metric]
        return sum(values) / len(values)

    scores = {
        "faithfulness": round(_mean("faithfulness"), 4),
        "answer_relevancy": round(_mean("answer_relevancy"), 4),
        "context_precision": round(_mean("context_precision"), 4),
    }

    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment("healthcare_rag")
    with mlflow.start_run(run_name="ragas_evaluation"):
        mlflow.log_param("query", query[:200])
        for metric, val in scores.items():
            mlflow.log_metric(metric, val)

    return scores
