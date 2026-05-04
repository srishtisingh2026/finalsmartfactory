import os
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# --------------------------------------------------
# Load .env from backend directory
# --------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]  # points to backend/
ENV_PATH = ROOT_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
    print(f"DEBUG: Loaded .env from {ENV_PATH}")
else:
    # Also try repo root as fallback
    REPO_ROOT = Path(__file__).resolve().parents[2]
    ENV_PATH_REPO = REPO_ROOT / ".env"
    if ENV_PATH_REPO.exists():
        load_dotenv(ENV_PATH_REPO)
        print(f"DEBUG: Loaded .env from {ENV_PATH_REPO}")
    else:
        print(f"WARNING: .env file not found at {ENV_PATH} or {ENV_PATH_REPO}")

# --------------------------------------------------
# Get Key Vault URI from environment (.env or App Service)
# --------------------------------------------------
KEY_VAULT_URI = os.getenv("KEY_VAULT_URI") or os.getenv("KEY-VAULT-URI")

if not KEY_VAULT_URI:
    print("WARNING: KEY_VAULT_URI not set in environment or .env file. Falling back to local credentials only.")
    KEY_VAULT_URI = "http://localhost" # dummy to satisfy SecretClient

print(f"DEBUG: Using Key Vault URI: {KEY_VAULT_URI}")

# --------------------------------------------------
# Init Azure Credentials
# --------------------------------------------------
_credential = DefaultAzureCredential()
_client = SecretClient(vault_url=KEY_VAULT_URI, credential=_credential)

# --------------------------------------------------
# Secret Fetcher
# --------------------------------------------------

# Map code-facing secret names to possible .env names
SECRET_MAP = {
    "COSMOS-CONN-READ": ["COSMOS_READ_ONLY_KEY_NAME", "COSMOS_CONN_READ"],
    "COSMOS-CONN-WRITE": ["COSMOS_READ_WRITE_KEY_NAME", "COSMOS_CONN_WRITE"],
}

def get_secret(name: str) -> str:
    # 1. Try Environment Variables first (mapped names)
    mapped_names = SECRET_MAP.get(name, [name.replace("-", "_")])
    for env_name in mapped_names:
        val = os.getenv(env_name)
        if val:
            print(f"DEBUG: Using local environment variable for '{name}' (as '{env_name}')")
            return val

    # 2. Key Vault fallback
    print(f"DEBUG: Fetching secret '{name}' from Key Vault...")
    try:
        val = _client.get_secret(name).value
        print(f"DEBUG: Successfully fetched secret '{name}'")
        return val
    except Exception as e:
        print(f"ERROR: Failed to fetch secret '{name}' from Key Vault: {str(e)}")
        
        # If Key Vault fails, we've already checked env vars. 
        # But for robustness, we return whatever was last checked or raise
        raise RuntimeError(f"Secret '{name}' not found in environment or Key Vault")
