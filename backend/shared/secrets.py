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
    return _client.get_secret(name).value
