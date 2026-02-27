from .schema import CostInfo
from datetime import datetime
from typing import Any, Dict
import re

# ============================================================
# PROVIDER DETECTION
# ============================================================

def detect_provider(raw: Dict[str, Any]) -> str:
    """
    Detect provider based on explicit provider field
    or model name pattern.
    """

    # If provider explicitly present
    if raw.get("provider"):
        return str(raw.get("provider")).lower()

    model = str(raw.get("model", "")).lower()

    if "gemini" in model:
        return "google"
    if "gpt" in model or "openai" in model:
        return "openai"
    if "llama" in model:
        return "groq"

    return "unknown"


# ============================================================
# TIMESTAMP NORMALIZATION
# ============================================================

def normalize_timestamp(value) -> int:
    """
    Convert timestamp to epoch milliseconds.
    Supports:
    - int (already epoch)
    - float
    - ISO string
    """

    if value is None:
        return 0

    # Already int
    if isinstance(value, int):
        return value

    # Float
    if isinstance(value, float):
        return int(value)

    # ISO format string
    if isinstance(value, str):
        try:
            return int(datetime.fromisoformat(value).timestamp() * 1000)
        except Exception:
            return 0

    return 0



# ============================================================
# SAFE TEXT EXTRACTION
# ============================================================

def safe_extract_text(value):
    """
    Extract text safely from nested provider payloads.
    """

    if value is None:
        return None

    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        for key in ["query", "answer", "response", "content", "text"]:
            if key in value and isinstance(value[key], str):
                return value[key]

        return str(value)

    return str(value)


# ============================================================
# INPUT EXTRACTION
# ============================================================

def extract_input(raw: Dict[str, Any]):

    return safe_extract_text(
        raw.get("input")
        or raw.get("question")
        or raw.get("request", {}).get("input")
    )


# ============================================================
# OUTPUT EXTRACTION
# ============================================================

def extract_output(raw: Dict[str, Any]):

    output = raw.get("output")

    if output:
        extracted = safe_extract_text(output)
        if extracted:
            return extracted

    # Provider raw fallback (OpenAI-style)
    provider_raw = raw.get("provider_raw", {})
    choices = provider_raw.get("choices", [])

    if choices:
        return safe_extract_text(
            choices[0].get("message", {}).get("content")
        )

    return None


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text: str) -> str:

    if not text:
        return ""

    text = text.replace("\\n", " ")
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()