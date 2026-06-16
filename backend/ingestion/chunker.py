import pandas as pd
from pathlib import Path
from typing import List, Dict, Any


CHUNK_SIZE = 512       # tokens (approximated as words here for simplicity)
CHUNK_OVERLAP = 50


def _word_chunks(text: str, size: int, overlap: int) -> List[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += size - overlap
    return chunks


def load_and_chunk(gold_csv_path: str) -> List[Dict[str, Any]]:
    """Load gold-layer clinical_summary CSV and return chunked documents with metadata."""
    df = pd.read_csv(gold_csv_path)
    required = {"patient_id", "clinical_note_text"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Gold CSV missing columns: {missing}")

    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        note_text = str(row["clinical_note_text"])
        chunks = _word_chunks(note_text, CHUNK_SIZE, CHUNK_OVERLAP)
        for idx, chunk in enumerate(chunks):
            records.append(
                {
                    "text": chunk,
                    "patient_id": str(row["patient_id"]),
                    "patient_name": str(row.get("patient_name", "")),
                    "condition_name": str(row.get("condition_name", "")),
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                }
            )
    return records
