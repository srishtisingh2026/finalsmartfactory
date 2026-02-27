from .schema import CostInfo

MODEL_PRICING = {
    "llama-3.1-8b-instant": {
        "input_per_1k": 0.00005,
        "output_per_1k": 0.00008,
    },
    "llama-3.3-70b-versatile": {
        "input_per_1k": 0.00059,
        "output_per_1k": 0.00079,
    },
    "openai/gpt-oss-120b": {
        "input_per_1k": 0.00015,
        "output_per_1k": 0.00060,
    },
    "gemini-2.5-flash-lite": {
        "input_per_1k": 0.0001,
        "output_per_1k": 0.0004,
    }
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int):

    model_key = str(model).lower().replace("models/", "")

    pricing = MODEL_PRICING.get(
        model_key,
        {"input_per_1k": 0, "output_per_1k": 0}
    )

    input_cost = (prompt_tokens / 1000) * pricing["input_per_1k"]
    output_cost = (completion_tokens / 1000) * pricing["output_per_1k"]

    return CostInfo(
        input_cost_usd=round(input_cost, 6),
        output_cost_usd=round(output_cost, 6),
        total_cost_usd=round(input_cost + output_cost, 6),
    )

def calculate_span_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:

    model_key = str(model).lower().replace("models/", "")

    pricing = MODEL_PRICING.get(
        model_key,
        {"input_per_1k": 0, "output_per_1k": 0}
    )

    input_cost = (prompt_tokens / 1000) * pricing["input_per_1k"]
    output_cost = (completion_tokens / 1000) * pricing["output_per_1k"]

    return round(input_cost + output_cost, 6)