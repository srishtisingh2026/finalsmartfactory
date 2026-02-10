import os
import json
import requests
from datetime import datetime, timezone
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
    raise RuntimeError("❌ Missing AZURE_OPENAI_KEY in .env")

# =====================================================
# Azure OpenAI Chat Completion
# =====================================================

def call_azure_llm(prompt: str) -> str:
    url = (
        f"{AZURE_ENDPOINT}"
        f"openai/deployments/{AZURE_DEPLOYMENT}/chat/completions"
        f"?api-version={AZURE_API_VERSION}"
    )

    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_KEY,
    }

    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a conciseness evaluator. "
                    "Judge if the answer is verbose, padded, repetitive, "
                    "or unnecessarily long. "
                    "Return ONLY valid JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30,  # ✅ prevent hanging evaluators
    )
    response.raise_for_status()

    data = response.json()

    choices = data.get("choices", [])
    if not choices:
        raise ValueError("No choices returned from Azure OpenAI")

    return choices[0]["message"]["content"]

# =====================================================
# Prompt Builder
# =====================================================

MAX_CONTEXT_CHARS = 3000
MAX_ANSWER_CHARS = 2000

def build_prompt(question: str, context: str, answer: str) -> str:
    question = (question or "").strip()
    context = (context or "")[:MAX_CONTEXT_CHARS]
    answer = (answer or "")[:MAX_ANSWER_CHARS]

    return f"""
Evaluate the conciseness of the AI answer.

Definition:
Conciseness = how short, clear, and to-the-point the answer is.

Question:
{question}

Context:
{context}

Answer:
{answer}

Return ONLY valid JSON:
{{
  "score": <float between 0 and 1>,
  "explanation": "<short reason>"
}}

Scoring Guide:
0.0 = extremely concise
0.5 = reasonably concise
1.0 = very verbose / padded
""".strip()

# =====================================================
# ✅ REQUIRED BY EVALUATOR REGISTRY
# =====================================================

def conciseness_llm(trace: dict) -> dict:
    """
    Per-trace conciseness evaluator.
    Called by EvaluatorRunner (Cosmos DB backed).
    """

    prompt = build_prompt(
        trace.get("question", ""),
        trace.get("context", ""),
        trace.get("answer", ""),
    )

    started_at = datetime.now(timezone.utc)

    try:
        llm_output = call_azure_llm(prompt)

        cleaned = (
            llm_output.replace("```json", "")
            .replace("```", "")
            .strip()
        )

        result = json.loads(cleaned)

        # -------------------------------------------------
        # IMPORTANT: invert score so higher = better
        # -------------------------------------------------
        raw_score = float(result["score"])
        final_score = round(1.0 - raw_score, 4)

        return {
            "score": final_score,
            "explanation": result.get("explanation", ""),
            "evaluated_at": started_at.isoformat(),
            "status": "success",
        }

    except Exception as e:
        return {
            "score": None,
            "explanation": f"Conciseness evaluation failed: {str(e)}",
            "evaluated_at": started_at.isoformat(),
            "status": "error",
        }
