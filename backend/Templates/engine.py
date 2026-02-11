import logging
from jinja2 import Template

from shared.cosmos import DB_READ   # <-- shared Cosmos clients
from shared.llm import call_llm     # <-- Azure OpenAI wrapper


# ----------------------------------------------------
# Get Cosmos Containers (READ)
# ----------------------------------------------------
EVALUATORS_CONTAINER = DB_READ.get_container_client("evaluators")
TEMPLATES_CONTAINER = DB_READ.get_container_client("templates")


# ----------------------------------------------------
# Fetch Evaluator Document
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
# Fetch Template Document
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
# Render rubric prompt using Jinja
# ----------------------------------------------------
def render_prompt(template_str: str, variables: dict) -> str:
    try:
        return Template(template_str).render(**variables)
    except Exception as e:
        logging.error(f"[engine] Failed to render template: {e}")
        raise


# ----------------------------------------------------
# Convert LLM output → numeric score safely
# ----------------------------------------------------
def parse_numeric_score(raw: str) -> float:
    try:
        return float(raw.strip())
    except Exception:
        return 0.0


# ----------------------------------------------------
# Main Dynamic Evaluator Execution
# ----------------------------------------------------
def run_evaluator(evaluator_id: str, variables: dict) -> dict:
    """
    evaluator_id = "conciseness-v1" (from Evaluator JSON)
    variables = { input, context, response }
    """

    # 1. Load Evaluator Record
    evaluator_doc = fetch_evaluator(evaluator_id)
    template_id = evaluator_doc["template"]["id"]

    # 2. Load Template Record
    template_doc = fetch_template(template_id)

    # Template schema:
    #  {
    #    "id": "...",
    #    "model": "gpt-4o-mini",
    #    "template": "<rubric prompt>",
    #    "inputs": [ "response" ]
    #  }

    model = template_doc["model"]
    prompt_template = template_doc["template"]

    # 3. Render prompt with variables
    final_prompt = render_prompt(prompt_template, variables)

    # 4. Call Azure OpenAI
    raw_output = call_llm(model=model, prompt=final_prompt)

    # 5. Convert raw → score (float)
    score = parse_numeric_score(raw_output)

    return {
        "evaluator_id": evaluator_id,
        "template_id": template_id,
        "score": score,
        "raw_output": raw_output
    }
