import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path

# =====================================================
# Load environment variables
# =====================================================

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH)

AZURE_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/") + "/"
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

if not AZURE_KEY:
    raise RuntimeError("❌ Missing AZURE_OPENAI_KEY in environment")

# =====================================================
# Azure OpenAI Chat Completions Call
# =====================================================

def call_azure_llm(prompt: str) -> str:
    url = (
        f"{AZURE_ENDPOINT}"
        f"openai/deployments/{AZURE_DEPLOYMENT}/chat/completions"
        f"?api-version={AZURE_API_VERSION}"
    )

    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_KEY
    }

    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a strict RAG evaluator. "
                    "Evaluate how relevant the retrieved context is to the question. "
                    "Return ONLY valid JSON."
                )
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )
    response.raise_for_status()

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise ValueError("No choices returned from Azure OpenAI")

    return choices[0]["message"]["content"]

# =====================================================
# Prompt Template
# =====================================================

MAX_CONTEXT_CHARS = 4000

def build_prompt(question: str, context: str) -> str:
    question = (question or "").strip()
    context = (context or "")[:MAX_CONTEXT_CHARS]

    return f"""
Evaluate the Context Relevance of the retrieved RAG context.

Definition:
Context Relevance = how well the retrieved context helps answer the question.

Scoring:
0.0 = completely irrelevant
0.5 = partially relevant
1.0 = fully relevant and sufficient

Question:
{question}

Retrieved Context:
{context}

Return ONLY valid JSON:
{{
  "score": <float between 0 and 1>,
  "explanation": "<short explanation>"
}}
""".strip()

# =====================================================
# ✅ REQUIRED BY EVALUATOR REGISTRY
# =====================================================

def context_relevance_llm(trace: dict) -> dict:
    """
    Per-trace context relevance evaluator.
    Called by EvaluatorRunner inside Azure Functions.
    """

    prompt = build_prompt(
        trace.get("question", ""),
        trace.get("context", "")
    )

    try:
        llm_output = call_azure_llm(prompt)

        cleaned = (
            llm_output.replace("```json", "")
            .replace("```", "")
            .strip()
        )

        result = json.loads(cleaned)

        return {
            "score": float(result["score"]),
            "explanation": result.get("explanation", "")
        }

    except Exception as e:
        return {
            "score": None,
            "explanation": f"Context relevance evaluation failed: {str(e)}"
        }
