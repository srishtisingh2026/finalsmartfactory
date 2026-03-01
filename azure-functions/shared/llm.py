import logging
import time
from typing import Optional

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
    api_version="2024-10-21"  # Keep aligned with deployment
)


# ----------------------------------------------------
# Generic LLM Call (Deployment-Aware + Retry Safe)
# ----------------------------------------------------

def call_llm(
    model: str,  # 🔥 This is deployment name (e.g., "gpt-4o", "gpt-4o-mini")
    prompt: str,
    max_tokens: int = 200,
    temperature: float = 0.0,
    timeout: int = 30,
    max_retries: int = 2
) -> Optional[str]:
    """
    Calls Azure OpenAI safely using deployment name.

    Designed for evaluator usage (deterministic numeric output).

    Returns:
        - Clean string output
        - None if call fails
    """

    attempt = 0

    while attempt <= max_retries:
        try:
            start_time = time.time()

            response = client.chat.completions.create(
                model=model,  # 🔥 Deployment name
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a deterministic scoring engine. Always return strict JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                timeout=timeout
            )

            latency_ms = int((time.time() - start_time) * 1000)

            content = response.choices[0].message.content

            if not content:
                logging.error(f"[llm:{model}] Empty response")
                return None

            logging.info(
                f"[llm:{model}] Success | "
                f"Latency={latency_ms}ms | "
                f"PromptTokens={response.usage.prompt_tokens} | "
                f"CompletionTokens={response.usage.completion_tokens}"
            )

            return content.strip()

        except Exception as e:
            logging.warning(
                f"[llm:{model}] Attempt {attempt + 1} failed: {e}"
            )

            attempt += 1

            # Exponential backoff
            if attempt <= max_retries:
                sleep_time = 2 ** attempt
                logging.info(f"[llm:{model}] Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
            else:
                logging.exception(f"[llm:{model}] All retries failed.")
                return None