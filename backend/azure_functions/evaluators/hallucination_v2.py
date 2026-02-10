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
    raise RuntimeError("❌ Missing AZURE_OPENAI_KEY")

if not AZURE_ENDPOINT.startswith("https://"):
    raise RuntimeError("❌ AZURE_OPENAI_ENDPOINT looks incorrect")

# =====================================================
# Azure OpenAI Chat API Call
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
                    "You are a strict hallucination evaluator. "
                    "Hallucination means information NOT supported by the provided context. "
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
MAX_ANSWER_CHARS = 2000

def build_prompt(question: str, context: str, answer: str) -> str:
    question = (question or "").strip()
    context = (context or "")[:MAX_CONTEXT_CHARS]
    answer = (answer or "")[:MAX_ANSWER_CHARS]

    return f"""
Evaluate the hallucination of the following answer.

Definition:
Hallucination = information NOT supported by the context.

Scoring:
0.0 = no hallucination
0.5 = partially hallucinated
1.0 = heavily hallucinated

Question:
{question}

Context:
{context}

Answer:
{answer}

Return ONLY valid JSON:
{{
  "score": <float between 0 and 1>,
  "explanation": "<short explanation>"
}}
""".strip()

# =====================================================
# ✅ REQUIRED BY EVALUATOR REGISTRY
# =====================================================

def hallucination_llm(trace: dict) -> dict:
    """
    Per-trace hallucination evaluator.
    Called by EvaluatorRunner inside Azure Functions.
    """

    prompt = build_prompt(
        trace.get("question", ""),
        trace.get("context", ""),
        trace.get("answer", "")
    )

    try:
        llm_output = call_azure_llm(prompt)

        cleaned = (
            llm_output.replace("```json", "")
            .replace("```", "")
            .strip()
        )

        result = json.loads(cleaned)

        raw_score = float(result["score"])

        # IMPORTANT: invert so higher = better (consistent platform-wide)
        final_score = round(1.0 - raw_score, 4)

        return {
            "score": final_score,
            "explanation": result.get("explanation", "")
        }

    except Exception as e:
        return {
            "score": None,
            "explanation": f"Hallucination evaluation failed: {str(e)}"
        }
