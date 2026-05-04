import os
import json
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# --------------------------------------------------
# Load .env & local.settings.json
# --------------------------------------------------
# Path discovery: /azure-functions/shared/secrets.py
ROOT_DIR = Path(__file__).resolve().parents[1] 

def load_local_settings():
    """
    Manually load local.settings.json into environment variables 
    if running in a context where the Azure Functions host is not handling it.
    """
    settings_path = ROOT_DIR / "local.settings.json"
    if settings_path.exists():
        try:
            with open(settings_path, "r") as f:
                data = json.load(f)
                values = data.get("Values", {})
                for k, v in values.items():
                    if k not in os.environ:
                        os.environ[k] = str(v)
            print(f"DEBUG: Loaded secrets from {settings_path}")
        except Exception as e:
            print(f"WARNING: Failed to parse {settings_path}: {e}")

# 1. Load from local.settings.json first (priority for local dev)
load_local_settings()

# 2. Load from .env files for additional flexibility
ENV_PATHS = [
    ROOT_DIR / ".env",
    ROOT_DIR.parent / ".env",
    ROOT_DIR.parent / "backend" / ".env",
]
for p in ENV_PATHS:
    if p.exists():
        load_dotenv(p)
        print(f"DEBUG: Loaded secrets from {p}")

# --------------------------------------------------
# Key Vault Configuration
# --------------------------------------------------
KEY_VAULT_URI = os.getenv("KEY_VAULT_URI")
if not KEY_VAULT_URI or KEY_VAULT_URI == "http://localhost":
    print("WARNING: KEY_VAULT_URI not set or invalid, using environment fallback only")
    _client = None
else:
    try:
        _credential = DefaultAzureCredential()
        _client = SecretClient(vault_url=KEY_VAULT_URI, credential=_credential)
        print(f"DEBUG: Initialized Key Vault client for {KEY_VAULT_URI}")
    except Exception as e:
        print(f"WARNING: Failed to init Key Vault client: {e}")
        _client = None

# --------------------------------------------------
# Secret Fetcher
# --------------------------------------------------
# Map code-facing secret names to possible environment names
SECRET_MAP = {
    "COSMOS-CONN-READ": ["COSMOS_READ_ONLY_KEY_NAME", "COSMOS_CONN_READ"],
    "COSMOS-CONN-WRITE": ["COSMOS_READ_WRITE_KEY_NAME", "COSMOS_CONN_WRITE"],
    "COSMOS_CONN_TRIGGER": ["COSMOS_READ_ONLY_KEY_NAME", "COSMOS_READ_WRITE_KEY_NAME", "COSMOS_CONN_READ"],
}

def get_secret(name: str) -> str:
    # 1. Try Environment Variables first
    mapped_names = SECRET_MAP.get(name, [name, name.replace("-", "_")])
    for env_name in mapped_names:
        val = os.getenv(env_name)
        if val:
            print(f"DEBUG: Using local environment variable for '{name}'")
            return val

    # 2. Key Vault fallback
    if _client:
        print(f"DEBUG: Fetching secret '{name}' from Key Vault...")
        try:
            val = _client.get_secret(name).value
            print(f"DEBUG: Successfully fetched secret '{name}'")
            return val
        except Exception as e:
            print(f"WARNING: Key Vault failed for '{name}': {str(e)}")
    
    # 3. Final failure
    raise RuntimeError(
        f"Secret '{name}' not found in environment, local.settings.json, or Key Vault. "
        "Please ensure it is set as an environment variable or in local.settings.json."
    )
