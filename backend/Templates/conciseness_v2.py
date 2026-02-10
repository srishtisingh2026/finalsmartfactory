import os
import json
import requests
from datetime import datetime, timezone

# 🔐 Key Vault (shared across App Service & Functions)
from shared.secrets import get_secret


# =====================================================
# Azure OpenAI configuration (from Key Vault)
# =====================================================

AZURE_KEY = get_secret("AZURE-OPENAI-KEY")
AZURE_ENDPOINT = get_secret("AZURE-OPENAI-ENDPOINT").rstrip("/") + "/"
AZURE_DEPLOYMENT = get_secret("AZURE-OPENAI-DEPLOYMENT")
AZURE_API_VERSION = get_secret("AZURE-OPENAI-API-VERSION")

if not AZURE_ENDPOINT.startswith("https://"):
    raise RuntimeError("❌ AZURE_OPENAI_ENDPOINT looks incorrect")


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
                    "Judge verbosity with fine-grained numeric precision. "
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
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise ValueError("No choices returned from Azure OpenAI")

    return choices[0]["message"]["content"]


# =====================================================
# Prompt Builder (CONTINUOUS SCORING)
# =====================================================

MAX_CONTEXT_CHARS = 3000
MAX_ANSWER_CHARS = 2000

def build_prompt(question: str, context: str, answer: str) -> str:
    question = (question or "").strip()
    context = (context or "")[:MAX_CONTEXT_CHARS]
    answer = (answer or "")[:MAX_ANSWER_CHARS]

    return f"""
Evaluate the CONCISENESS of the AI answer.

Definition:
Conciseness measures how short, clear, and to-the-point the answer is.

Scoring instructions (IMPORTANT):
- Return a FLOAT between 0.0 and 1.0
- Use fine-grained values (e.g., 0.21, 0.48, 0.73, 0.92)
- Avoid round numbers unless the case is extremely clear
- Higher score = more concise
- 0.0 = extremely verbose / padded
- 1.0 = extremely concise

Question:
{question}

Context:
{context}

Answer:
{answer}

Return ONLY valid JSON:
{{
  "score": <float>,
  "explanation": "<short reason>"
}}
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

        # Higher score = better (already correct)
        final_score = round(float(result["score"]), 4)

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
