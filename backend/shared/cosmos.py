"""
Centralized Cosmos DB access layer.

✔ Used by Azure Functions
✔ Used by App Service (FastAPI)
✔ Secrets loaded from Azure Key Vault via Managed Identity
✔ Read / Write separation supported
✔ No env vars, no .env, no duplication
"""

from azure.cosmos import CosmosClient
from shared.secrets import get_secret


# =====================================================
# Cosmos Configuration
# =====================================================

COSMOS_DB = "llmops-data"  # not secret, keep static

COSMOS_CONN_READ = get_secret("COSMOS-CONN-READ")
COSMOS_CONN_WRITE = get_secret("COSMOS-CONN-WRITE")


# =====================================================
# Cosmos Clients
# =====================================================

_client_read = CosmosClient.from_connection_string(
    COSMOS_CONN_READ
)

_client_write = CosmosClient.from_connection_string(
    COSMOS_CONN_WRITE
)


# =====================================================
# Database Clients
# =====================================================

_db_read = _client_read.get_database_client(COSMOS_DB)
_db_write = _client_write.get_database_client(COSMOS_DB)


# =====================================================
# Container Clients (READ)
# =====================================================

traces_container_read = _db_read.get_container_client("traces")
evaluations_container_read = _db_read.get_container_client("evaluations")
metrics_container_read = _db_read.get_container_client("metrics")
templates_container_read = _db_read.get_container_client("templates")
evaluators_container_read = _db_read.get_container_client("evaluators")
audit_container_read = _db_read.get_container_client("audit_logs")


# =====================================================
# Container Clients (WRITE)
# =====================================================

traces_container = _db_write.get_container_client("traces")
evaluations_container = _db_write.get_container_client("evaluations")
metrics_container = _db_write.get_container_client("metrics")
templates_container = _db_write.get_container_client("templates")
evaluators_container = _db_write.get_container_client("evaluators")
audit_container = _db_write.get_container_client("audit_logs")
