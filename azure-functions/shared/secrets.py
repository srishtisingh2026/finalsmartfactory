import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

KEY_VAULT_URI = os.getenv("KEY_VAULT_URI")
if not KEY_VAULT_URI:
    raise RuntimeError("KEY_VAULT_URI not set")

_credential = DefaultAzureCredential()
_client = SecretClient(
    vault_url=KEY_VAULT_URI,
    credential=_credential
)

def get_secret(name: str) -> str:
    print(f"DEBUG: Fetching secret '{name}' from Key Vault...")
    try:
        val = _client.get_secret(name).value
        print(f"DEBUG: Successfully fetched secret '{name}'")
        return val
    except Exception as e:
        print(f"ERROR: Failed to fetch secret '{name}': {str(e)}")
        raise
