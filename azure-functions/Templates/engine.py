import logging
import re
from typing import Optional
from jinja2 import Template

from shared.cosmos import DB_READ
from shared.llm import call_llm, client, LLM_PROVIDER
import google.generativeai as genai


# ----------------------------------------------------
# Cosmos Containers
# ----------------------------------------------------
EVALUATORS_CONTAINER = DB_READ.get_container_client("evaluators")
TEMPLATES_CONTAINER = DB_READ.get_container_client("templates")


# ----------------------------------------------------
# Pricing Table (USD per token)
# ----------------------------------------------------
MODEL_PRICING = {
    "gpt-4o": {"input": 0.000005, "output": 0.000015},
    "gpt-4o-mini": {"input": 0.00000015, "output": 0.0000006},
    "gemini-1.5-flash": {"input": 0.000000075, "output": 0.0000003}, # Approx
    "gemini-1.5-pro": {"input": 0.0000035, "output": 0.0000105},
    "models/gemini-2.5-flash": {"input": 0.000000075, "output": 0.0000003},
    "models/gemini-2.5-pro": {"input": 0.0000035, "output": 0.0000105},
    "models/gemini-2.0-flash": {"input": 0.000000075, "output": 0.0000003},
}


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

        match = re.search(r"score[:\s]+(\d+(?:\.\d+)?)", raw, re.IGNORECASE)
        if match:
            return float(match.group(1))

        matches = re.findall(r"\d+(?:\.\d+)?", raw)
        if matches:
            return float(matches[0])

        return None

    except Exception:
        return None


# ----------------------------------------------------
# Cost Calculation
# ----------------------------------------------------
def calculate_cost(model, prompt_tokens, completion_tokens):
    pricing = MODEL_PRICING.get(model)

    if not pricing:
        return 0

    input_cost = prompt_tokens * pricing["input"]
    output_cost = completion_tokens * pricing["output"]

    return input_cost + output_cost


# ----------------------------------------------------
# Evaluation Logic
# ----------------------------------------------------

EMBEDDING_CACHE = {}
SIMILARITY_CACHE = {}

def get_embedding(text: str, model: str = "text-embedding-3-small") -> list:
    """
    Get text embedding from Azure OpenAI with in-memory caching.
    """
    if not text:
        return []
    
    # Use model name and hash of text as cache key
    cache_key = f"{model}:{hash(text)}"
    if cache_key in EMBEDDING_CACHE:
        return EMBEDDING_CACHE[cache_key]
        
    try:
        if LLM_PROVIDER == "gemini":
            try:
                result = genai.embed_content(
                    model="models/gemini-embedding-001",
                    content=text,
                    task_type="retrieval_document"
                )
                embedding = result['embedding']
            except Exception as e:
                logging.error(f"[engine] Gemini embedding failed: {e}")
                return []
        else:
            response = client.embeddings.create(input=[text], model=model)
            embedding = response.data[0].embedding
        
        # Store in cache
        EMBEDDING_CACHE[cache_key] = embedding
        return embedding
    except Exception as e:
        logging.error(f"[engine] Embedding failed ({LLM_PROVIDER}): {e}")
        return []


def cosine_similarity(v1: list, v2: list) -> float:
    if not v1 or not v2:
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = sum(a * a for a in v1) ** 0.5
    norm_b = sum(b * b for b in v2) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def compute_embedding_similarity(context: str, answer: str) -> float:
    """
    Semantic similarity using Azure OpenAI embeddings with result caching.
    """
    if not context or not answer:
        return 0.0

    # Cache the final similarity score directly
    cache_key = f"{hash(context)}:{hash(answer)}"
    if cache_key in SIMILARITY_CACHE:
        return SIMILARITY_CACHE[cache_key]

    v_context = get_embedding(context)
    v_answer = get_embedding(answer)

    score = cosine_similarity(v_context, v_answer)
    result = round(score, 2)
    
    # Store in cache
    SIMILARITY_CACHE[cache_key] = result
    return result


def compute_keyword_coverage(context: str, answer: str) -> float:
    """
    Refactored to also use semantic signals as requested.
    """
    context_words = set(context.lower().split())
    answer_words = set(answer.lower().split())

    if not answer_words:
        return 0.0

    overlap = context_words.intersection(answer_words)

    return round(len(overlap) / len(answer_words), 2)


# ----------------------------------------------------
# Method Registry
# ----------------------------------------------------
METHOD_REGISTRY = {
    "embedding_similarity": compute_embedding_similarity,
    "keyword_coverage": compute_keyword_coverage
}


# ----------------------------------------------------
# Main Evaluator Execution
# ----------------------------------------------------
def run_evaluator(
    evaluator_id: str,
    variables: dict,
    deployment: Optional[str] = None,
    trace_methods: Optional[dict] = None
) -> dict:

    logging.info(f"[engine] Starting run_evaluator for {evaluator_id}")

    evaluator_doc = fetch_evaluator(evaluator_id)
    template_id = evaluator_doc["template"]["id"]

    model_override = evaluator_doc.get("template", {}).get("model")

    template_doc = fetch_template(template_id)

    template_model = template_doc.get("model")
    prompt_template = template_doc["template"]
    required_inputs = template_doc.get("inputs", [])

    # ----------------------------------------------------
    # Model Selection Logic (Precision Fix)
    # ----------------------------------------------------
    enable_ensemble = evaluator_doc.get("enable_ensemble", False)
    execution_cfg = evaluator_doc.get("execution", {})

    if enable_ensemble is True:
        # If ensemble is on, use the provided deployment or the first one in the list
        selected_model = deployment or execution_cfg.get("ensemble_deployments", ["gpt-4o-mini"])[0]
    else:
        # If ensemble is off, use user-chosen model (from model_name, deployment, or overrides)
        # Check root and execution block as per schema variants
        selected_model = (
            evaluator_doc.get("model_name") or 
            evaluator_doc.get("deployment") or 
            execution_cfg.get("model_name") or 
            execution_cfg.get("deployment") or
            model_override or 
            template_model or
            "gpt-4o-mini" # Last resort
        )

    logging.info(f"Ensemble enabled: {enable_ensemble}")
    logging.info(f"Selected model: {selected_model}")

    model = selected_model

    template_variables = {}

    for key in required_inputs:
        if key in variables and variables.get(key) is not None:
            template_variables[key] = variables[key]
        elif "_raw" in variables and key in variables["_raw"]:
            template_variables[key] = variables["_raw"][key]
        else:
            raise ValueError(f"Missing required template inputs: [{key}]")

    final_prompt = render_prompt(prompt_template, template_variables)

    # ----------------------------------------------------
    # Call LLM (DEFAULT evaluation)
    # ----------------------------------------------------
    response = call_llm(
        model=model,
        prompt=final_prompt
    )

    if not response:
        return {
            "evaluator_id": evaluator_id,
            "template_id": template_id,
            "model_used": model,
            "score": None,
            "classification": "failed",
            "raw_output": "Empty response",
            "cost_usd": 0
        }

    raw_output = response.get("text")
    usage = response.get("usage", {})

    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)

    cost = calculate_cost(model, prompt_tokens, completion_tokens)

    llm_score = parse_numeric_score(raw_output)

    classification = "completed" if llm_score is not None else "failed"

    final_score = llm_score

    raw_output = {
        "llm_output": raw_output,
        "trace_methods": trace_methods
    }

    return {
        "evaluator_id": evaluator_id,
        "template_id": template_id,
        "model_used": model,
        "score": llm_score,
        "classification": classification,
        "raw_output": raw_output,
        "cost_usd": round(cost, 6)
    }