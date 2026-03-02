"""
Centralized Cosmos DB access layer.

✔ Shared by Azure Functions + FastAPI
✔ Secrets loaded from Azure Key Vault via Managed Identity
✔ Read/Write separation
✔ Backward-compatible container exports
"""

from azure.cosmos import CosmosClient
from shared.secrets import get_secret


# =====================================================
# Configuration
# =====================================================

COSMOS_DB = "llmops-data"

print("DEBUG: Fetching Cosmos DB connection strings...")
COSMOS_CONN_READ = get_secret("COSMOS-CONN-READ")
COSMOS_CONN_WRITE = get_secret("COSMOS-CONN-WRITE")
print("DEBUG: Successfully fetched Cosmos DB connection strings")


# =====================================================
# Clients
# =====================================================

print("DEBUG: Initializing Cosmos Clients...")
_client_read = CosmosClient.from_connection_string(COSMOS_CONN_READ)
_client_write = CosmosClient.from_connection_string(COSMOS_CONN_WRITE)
print("DEBUG: Initialized Cosmos Clients")


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
audit_logs_write = DB_WRITE.get_container_client("audit_logs")


# =====================================================
# 🔥 ROUTER COMPATIBILITY EXPORTS
# =====================================================

# TRACES
traces_container_read = traces_read
traces_container_write = traces_write

# TEMPLATES
templates_container_read = templates_read
templates_container = templates_write  # used for create/update

# METRICS
metrics_container_read = metrics_read
metrics_container = metrics_write

# EVALUATORS
evaluators_container_read = evaluators_read
evaluators_container = evaluators_write

# EVALUATIONS
evaluations_container_read = evaluations_read
evaluations_container = evaluations_write

# AUDIT
audit_container_read = audit_logs_read
audit_container = audit_logs_write

# =====================================================
# RCA RESULTS (NEW)
# =====================================================

rca_results_read = DB_READ.get_container_client("rca_results")
rca_results_write = DB_WRITE.get_container_client("rca_results")

# Export for routers
rca_container_read = rca_results_read
rca_container_write = rca_results_write