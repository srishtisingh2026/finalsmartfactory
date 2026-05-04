from typing import Optional, Dict, Any
import logging
import time
import os
import google.generativeai as genai
from openai import AzureOpenAI
from shared.secrets import get_secret


# ----------------------------------------------------
# LLM Provider Configuration
# ----------------------------------------------------

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "azure").lower()

# Check if we should use Gemini (either explicitly or if Azure secrets are missing)
if LLM_PROVIDER == "gemini" or not os.getenv("AZURE_OPENAI_KEY"):
    GEMINI_API_KEY = get_secret("GOOGLE_API_KEY")
    if GEMINI_API_KEY and not GEMINI_API_KEY.startswith("dummy-"):
        genai.configure(api_key=GEMINI_API_KEY, transport='rest')
        LLM_PROVIDER = "gemini"
        client = None
        print("DEBUG: Initialized Gemini Provider")
    else:
        print("WARNING: Gemini key not found, attempting Azure OpenAI")
        LLM_PROVIDER = "azure"

if LLM_PROVIDER == "azure":
    try:
        AZURE_OPENAI_ENDPOINT = get_secret("AZURE-OPENAI-ENDPOINT")
        AZURE_OPENAI_KEY = get_secret("AZURE-OPENAI-KEY")

        client = AzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version="2024-10-21"
        )
        print("DEBUG: Initialized Azure OpenAI Provider")
    except Exception as e:
        print(f"ERROR: Failed to initialize Azure OpenAI: {e}")
        client = None

# ----------------------------------------------------
# Dedicated Evaluator Configuration
# ----------------------------------------------------
try:
    evaluator_client = AzureOpenAI(
        api_key="3nELgOuRfta8Cw3KuBIBQJaEZjMhkiQKkzNbOw2KnmAKbtBTFqIPJQQJ99CDACHYHv6XJ3w3AAABACOGdpFw",
        azure_endpoint="https://openai-devops-gpt-4o-mini.openai.azure.com/",
        api_version="2025-01-01-preview"
    )
    print("DEBUG: Initialized Dedicated Evaluator Endpoint")
except Exception as e:
    evaluator_client = None

# ----------------------------------------------------
# Generic LLM Call (Deployment-Aware + Retry Safe)
# ----------------------------------------------------

def call_llm(
    model: str,
    prompt: str,
    max_tokens: int = 200,
    temperature: float = 0.0,
    timeout: int = 30,
    max_retries: int = 2
) -> Optional[Dict[str, Any]]:

    attempt = 0

    while attempt <= max_retries:
        try:
            start_time = time.time()

            # Attempt dedicated evaluator endpoint first
            if attempt == 0 and evaluator_client and "gpt-4o-mini" in model.lower():
                try:
                    logging.info("[llm:evaluator] Attempting dedicated evaluator endpoint...")
                    resp = evaluator_client.chat.completions.create(
                        model="gpt-4o-mini",
                        temperature=temperature,
                        max_tokens=max_tokens,
                        messages=[
                            {"role": "system", "content": "You are a deterministic scoring engine. Always return strict JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        timeout=timeout
                    )
                    content = resp.choices[0].message.content
                    if content:
                        prompt_toks = resp.usage.prompt_tokens
                        comp_toks = resp.usage.completion_tokens
                        lat_ms = int((time.time() - start_time) * 1000)
                        logging.info(f"[llm:{model}] Success (evaluator) | Latency={lat_ms}ms")
                        return {
                            "text": content.strip(),
                            "usage": {"prompt_tokens": prompt_toks, "completion_tokens": comp_toks},
                            "latency_ms": lat_ms
                        }
                except Exception as eval_err:
                    logging.warning(f"[llm:evaluator] Failed: {eval_err}. Falling back to default setup...")
                    start_time = time.time() # Reset timer for the fallback

            if LLM_PROVIDER == "gemini":
                # Specific Alias Mapping for UI-friendly names
                MODEL_MAP = {
                    "Gemma 3 1B": "models/gemma-3-1b-it",
                    "Gemma 3 4B": "models/gemma-3-4b-it",
                    "Gemma 3 12B": "models/gemma-3-12b-it",
                    "Gemma 3 27B": "models/gemma-3-27b-it"
                }

                # Determine the specific Gemini model name
                # We prioritize the incoming model name, only mapping known OpenAI Aliases or Gemma Aliases
                if model in MODEL_MAP:
                    gemini_model_name = MODEL_MAP[model]
                elif model.startswith("models/"):
                    gemini_model_name = model
                elif "gpt-4o-mini" in model.lower():
                    gemini_model_name = "models/gemini-2.5-flash"
                elif "gpt-4o" in model.lower():
                    gemini_model_name = "models/gemini-2.5-pro"
                else:
                    # Fallback for other potential names
                    model_cleaned = model.replace(' ', '-').lower()
                    gemini_model_name = f"models/{model_cleaned}"
                    # Ensure it has the -it suffix for Gemma-like names if not already present
                    if "gemma-3" in gemini_model_name and not gemini_model_name.endswith("-it"):
                         gemini_model_name += "-it"
                
                try:
                    logging.info(f"[llm:gemini] Calling {gemini_model_name} (REST transport)")
                    genai_model = genai.GenerativeModel(gemini_model_name)
                    response = genai_model.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=temperature,
                            max_output_tokens=max_tokens,
                        )
                    )
                except Exception as e:
                    # Reraise to be caught by the retry loop (handling 429s etc)
                    raise e
                
                content = ""
                if response.candidates:
                    candidate = response.candidates[0]
                    if candidate.content and candidate.content.parts:
                        content = candidate.text
                    else:
                        logging.warning(f"[llm:gemini] No text in candidate 0. Finish reason: {candidate.finish_reason}")
                        content = f"Failure: {candidate.finish_reason}"
                else:
                    logging.error(f"[llm:gemini] No candidates in response. Likely blocked by safety filters.")
                    content = "Error: Blocked by safety filters"
                
                prompt_tokens = response.usage_metadata.prompt_token_count
                completion_tokens = response.usage_metadata.candidates_token_count
                
            else:
                response = client.chat.completions.create(
                    model=model,
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
                content = response.choices[0].message.content
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens

            latency_ms = int((time.time() - start_time) * 1000)

            if not content:
                logging.error(f"[llm:{model}] Empty response")
                return None

            logging.info(
                f"[llm:{model}] Success ({LLM_PROVIDER}) | "
                f"Latency={latency_ms}ms | "
                f"PromptTokens={prompt_tokens} | "
                f"CompletionTokens={completion_tokens}"
            )

            return {
                "text": content.strip(),
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens
                },
                "latency_ms": latency_ms
            }

        except Exception as e:
            err_str = str(e).lower()
            is_quota = "429" in err_str or "quota" in err_str or "limit" in err_str
            
            logging.warning(
                f"[llm:{model}] Attempt {attempt + 1} failed: {e}"
            )

            attempt += 1

            if attempt <= max_retries:
                # If we hit a rate limit, we need a MUCH longer sleep (Free tier is strict)
                sleep_time = 60 if is_quota else (2 ** attempt)
                logging.info(f"[llm:{model}] {'Quota reached. ' if is_quota else ''}Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
            else:
                logging.exception(f"[llm:{model}] All retries failed.")
                return None