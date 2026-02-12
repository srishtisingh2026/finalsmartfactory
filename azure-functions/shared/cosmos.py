"""
Centralized Cosmos DB access layer.

✔ Shared by Azure Functions + FastAPI (App Service)
✔ Secrets loaded from Azure Key Vault via Managed Identity
✔ Read/Write separation
✔ No env vars or duplication
"""

from azure.cosmos import CosmosClient
from shared.secrets import get_secret


# =====================================================
# Cosmos Configuration
# =====================================================

COSMOS_DB = "llmops-data"  # static db name

print("DEBUG: Fetching Cosmos DB connection strings...")
COSMOS_CONN_READ = get_secret("COSMOS-CONN-READ")
COSMOS_CONN_WRITE = get_secret("COSMOS-CONN-WRITE")
print("DEBUG: Successfully fetched Cosmos DB connection strings")


# =====================================================
# Cosmos Clients
# =====================================================

print("DEBUG: Initializing Cosmos Clients...")
_client_read = CosmosClient.from_connection_string(COSMOS_CONN_READ)
_client_write = CosmosClient.from_connection_string(COSMOS_CONN_WRITE)
print("DEBUG: Initialized Cosmos Clients")


# =====================================================
# Database Clients
# =====================================================

DB_READ = _client_read.get_database_client(COSMOS_DB)
DB_WRITE = _client_write.get_database_client(COSMOS_DB)


# =====================================================
# READ Containers
# =====================================================

traces_read = DB_READ.get_container_client("traces")
evaluations_read = DB_READ.get_container_client("evaluations")
metrics_read = DB_READ.get_container_client("metrics")
templates_read = DB_READ.get_container_client("templates")
evaluators_read = DB_READ.get_container_client("evaluators")
audit_logs_read = DB_READ.get_container_client("audit_logs")


# =====================================================
# WRITE Containers
# =====================================================

traces_write = DB_WRITE.get_container_client("traces")
evaluations_write = DB_WRITE.get_container_client("evaluations")
metrics_write = DB_WRITE.get_container_client("metrics")
templates_write = DB_WRITE.get_container_client("templates")
evaluators_write = DB_WRITE.get_container_client("evaluators")
audit_logs_write = DB_WRITE.get_container_client("audit_logs")  # <-- FIX ADDED


# Alias for audit module compatibility
audit_container = audit_logs_write
