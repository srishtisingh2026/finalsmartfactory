import os
import json
import requests

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
        "api-key": AZURE_KEY,
    }

    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a strict hallucination evaluator. "
                    "Hallucination means information NOT supported by the provided context. "
                    "You must produce a fine-grained numeric judgment. "
                    "Return ONLY valid JSON."
                )
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
# Prompt Template (CONTINUOUS SCORING)
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

Scoring instructions (IMPORTANT):
- Return a FLOAT between 0.0 and 1.0
- Use fine-grained values (e.g., 0.12, 0.47, 0.83)
- Avoid round numbers unless the case is extremely clear
- 0.0 = no hallucination
- 1.0 = completely hallucinated
- Higher score = more hallucination

Question:
{question}

Context:
{context}

Answer:
{answer}

Return ONLY valid JSON:
{{
  "score": <float>,
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
        trace.get("answer", ""),
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

        # Invert so higher = better (less hallucination)
        final_score = round(1.0 - raw_score, 4)

        return {
            "score": final_score,
            "explanation": result.get("explanation", ""),
        }

    except Exception as e:
        return {
            "score": None,
            "explanation": f"Hallucination evaluation failed: {str(e)}",
        }
