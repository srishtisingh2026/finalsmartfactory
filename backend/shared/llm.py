import logging
from openai import AzureOpenAI
from shared.secrets import get_secret

# ----------------------------------------------------
# Azure OpenAI Credentials (from Key Vault)
# ----------------------------------------------------

AZURE_OPENAI_ENDPOINT = get_secret("AZURE-OPENAI-ENDPOINT")
AZURE_OPENAI_KEY = get_secret("AZURE-OPENAI-KEY")

client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version="2024-10-21"   # Keep updated with deployment version
)

# ----------------------------------------------------
# Generic LLM call used by evaluator engine
# ----------------------------------------------------

def call_llm(model: str, prompt: str) -> str:
    """
    Calls Azure OpenAI with deterministic settings.
    Ensures robust error handling and clean output.
    """

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}],
            timeout=30  # safeguard timeout
        )

        # New SDK: message is an object, not a dict
        content = response.choices[0].message.content

        if not content:
            logging.error("[llm] Empty response from model")
            return "0"

        return content.strip()

    except Exception as e:
        logging.exception(f"[llm] Azure OpenAI call failed: {e}")
        # Evaluators must never crash → return safe value
        return "0"
