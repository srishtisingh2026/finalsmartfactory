import os
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# --------------------------------------------------
# Load .env from project root
# --------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[2]  # go up one level to backend/
ENV_PATH = ROOT_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
    print(f"DEBUG: Loaded .env from {ENV_PATH}")
else:
    print(f"WARNING: .env file not found at {ENV_PATH}")

# --------------------------------------------------
# Get Key Vault URI from environment (.env or App Service)
# --------------------------------------------------
KEY_VAULT_URI = os.getenv("KEY_VAULT_URI") or os.getenv("KEY-VAULT-URI")

if not KEY_VAULT_URI:
    raise RuntimeError("KEY_VAULT_URI not set in environment or .env file")

print(f"DEBUG: Using Key Vault URI: {KEY_VAULT_URI}")

# --------------------------------------------------
# Init Azure Credentials
# --------------------------------------------------
_credential = DefaultAzureCredential()
_client = SecretClient(vault_url=KEY_VAULT_URI, credential=_credential)

# --------------------------------------------------
# Secret Fetcher
# --------------------------------------------------
def get_secret(name: str) -> str:
    print(f"DEBUG: Fetching secret '{name}' from Key Vault...")
    try:
        val = _client.get_secret(name).value
        print(f"DEBUG: Successfully fetched secret '{name}'")
        return val
    except Exception as e:
        print(f"ERROR: Failed to fetch secret '{name}': {str(e)}")
        raise
