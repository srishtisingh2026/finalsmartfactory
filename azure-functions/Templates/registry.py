from Templates.engine import run_evaluator

# ----------------------------------------------------
# REGISTRY OF EVALUATOR FUNCTIONS (DYNAMIC)
# ----------------------------------------------------
# Each function now receives:
#   - evaluator_id (e.g., "conciseness-v1")
#   - vars (normalized trace)
#
# registry_key = f"{score_name}_llm"
# Example: "conciseness_llm"
# ----------------------------------------------------

EVALUATORS = {
    "conciseness_llm": lambda evaluator_id, vars: run_evaluator(evaluator_id, vars),

    "hallucination_llm": lambda evaluator_id, vars: run_evaluator(evaluator_id, vars),

    "context_relevance_llm": lambda evaluator_id, vars: run_evaluator(evaluator_id, vars),
}
