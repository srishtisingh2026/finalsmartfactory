# backend/evaluators/registry.py

from .hallucination_v2 import hallucination_llm
from .context_relevance_v2 import context_relevance_llm
from .conciseness_v2 import conciseness_llm

EVALUATORS = {
    "hallucination_llm": hallucination_llm,
    "context_relevance_llm": context_relevance_llm,
    "conciseness_llm": conciseness_llm,
}
