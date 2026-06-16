import os
from typing import List, Dict, Any

import anthropic
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are an expert clinical assistant with deep knowledge of healthcare data.
You help clinicians and analysts answer questions about patient records accurately and concisely.
Always ground your answers in the provided context. If the context does not contain enough
information to answer, say so clearly. Never hallucinate clinical details."""


def generate(query: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Call Claude with retrieved context and return the answer."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    context_block = "\n\n".join(
        f"[Source {i+1} | Patient: {c['patient_name']} | Score: {c['score']}]\n{c['text']}"
        for i, c in enumerate(chunks)
    )

    user_message = f"""Clinical question: {query}

---
Retrieved context:
{context_block}
---

Please answer the clinical question based solely on the context above."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    answer = response.content[0].text
    return {
        "answer": answer,
        "model": MODEL,
        "sources": chunks,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
