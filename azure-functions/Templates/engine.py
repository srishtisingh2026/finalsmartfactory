import logging
import re
from typing import Optional
from jinja2 import Template

from shared.cosmos import DB_READ
from shared.llm import call_llm


# ----------------------------------------------------
# Cosmos Containers
# ----------------------------------------------------
EVALUATORS_CONTAINER = DB_READ.get_container_client("evaluators")
TEMPLATES_CONTAINER = DB_READ.get_container_client("templates")


# ----------------------------------------------------
# Fetch Evaluator
# ----------------------------------------------------
def fetch_evaluator(evaluator_id: str):
    try:
        return EVALUATORS_CONTAINER.read_item(
            item=evaluator_id,
            partition_key=evaluator_id
        )
    except Exception as e:
        logging.error(f"[engine] Failed to load evaluator {evaluator_id}: {e}")
        raise


# ----------------------------------------------------
# Fetch Template
# ----------------------------------------------------
def fetch_template(template_id: str):
    try:
        return TEMPLATES_CONTAINER.read_item(
            item=template_id,
            partition_key=template_id
        )
    except Exception as e:
        logging.error(f"[engine] Failed to load template {template_id}: {e}")
        raise


# ----------------------------------------------------
# Render Prompt
# ----------------------------------------------------
def render_prompt(template_str: str, variables: dict) -> str:
    try:
        return Template(template_str).render(**variables)
    except Exception as e:
        logging.error(f"[engine] Failed to render template: {e}")
        raise


# ----------------------------------------------------
# Extract Numeric Score
# ----------------------------------------------------
def parse_numeric_score(raw: Optional[str]) -> Optional[float]:
    try:
        if not raw:
            return None

        # 1️⃣ Try "Score: X"
        match = re.search(r"score[:\s]+(\d+(?:\.\d+)?)", raw, re.IGNORECASE)
        if match:
            return float(match.group(1))

        # 2️⃣ Fallback: first number found
        matches = re.findall(r"\d+(?:\.\d+)?", raw)
        if matches:
            return float(matches[0])

        return None

    except Exception:
        return None


# ----------------------------------------------------
# Main Evaluator Execution (UPDATED)
# ----------------------------------------------------
def run_evaluator(
    evaluator_id: str,
    variables: dict,
    deployment: Optional[str] = None  # 🔥 NEW
) -> dict:
    """
    Fully dynamic evaluator runner.

    If deployment is provided:
        → It overrides template model.
    Otherwise:
        → Template model is used.
    """

    logging.info(f"[engine] Starting run_evaluator for {evaluator_id}")

    # 1️⃣ Load evaluator
    evaluator_doc = fetch_evaluator(evaluator_id)
    template_id = evaluator_doc["template"]["id"]

    # Optional model override from evaluator config
    model_override = evaluator_doc.get("template", {}).get("model")

    # 2️⃣ Load template
    template_doc = fetch_template(template_id)

    template_model = template_doc.get("model")
    prompt_template = template_doc["template"]
    required_inputs = template_doc.get("inputs", [])

    # 🔥 Determine final model (deployment wins)
    model = deployment or model_override or template_model

    logging.info(f"[engine] Using model/deployment: {model}")

    # 3️⃣ Build template variables
    template_variables = {}

    for key in required_inputs:
        if key in variables and variables.get(key) is not None:
            template_variables[key] = variables[key]
        elif "_raw" in variables and key in variables["_raw"]:
            template_variables[key] = variables["_raw"][key]
        else:
            raise ValueError(f"Missing required template inputs: [{key}]")

    # 4️⃣ Render prompt
    final_prompt = render_prompt(prompt_template, template_variables)

    # 5️⃣ Call LLM (deployment-aware)
    raw_output = call_llm(
        model=model,  # 🔥 This is deployment name now
        prompt=final_prompt
    )

    if not raw_output:
        return {
            "evaluator_id": evaluator_id,
            "template_id": template_id,
            "model_used": model,
            "score": None,
            "classification": "failed",
            "raw_output": "Empty response"
        }

    # 6️⃣ Parse score
    score = parse_numeric_score(raw_output)

    classification = "completed" if score is not None else "failed"

    return {
        "evaluator_id": evaluator_id,
        "template_id": template_id,
        "model_used": model,
        "score": score,
        "classification": classification,
        "raw_output": raw_output
    }