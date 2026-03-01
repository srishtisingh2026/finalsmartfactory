import logging
import azure.functions as func
from azure.cosmos import CosmosClient
import os
from typing import Set
from .rca_rules import analyze_trace

logger = logging.getLogger("rca_engine")

COSMOS = os.environ["COSMOS_CONN_WRITE"]
client = CosmosClient.from_connection_string(COSMOS)

DB = client.get_database_client("llmops-data")
RAW = DB.get_container_client("raw_traces")
EVALS = DB.get_container_client("evaluations")
RCA = DB.get_container_client("rca_results")
EVALUATORS = DB.get_container_client("evaluators")  # registry


# ============================================================
# DYNAMIC REQUIRED EVALUATORS (BASED ON YOUR SCHEMA)
# ============================================================

def get_required_evaluators() -> Set[str]:
    """
    Load required evaluators dynamically.
    All evaluators with status='active'
    are required before RCA runs.
    """

    query = """
        SELECT c.score_name
        FROM c
        WHERE c.status = "active"
    """

    items = list(EVALUATORS.query_items(
        query=query,
        enable_cross_partition_query=True
    ))

    required = {item["score_name"] for item in items}

    logger.info(f"[RCA CONFIG] Active evaluators required: {required}")
    return required


# ============================================================
# MAIN FUNCTION
# ============================================================

def main(docs: func.DocumentList):

    if not docs:
        return

    required = get_required_evaluators()

    for doc in docs:

        eval_doc = doc.to_dict()
        trace_id = eval_doc.get("trace_id")

        if not trace_id:
            logger.warning("[RCA SKIP] Missing trace_id")
            continue

        logger.info(f"[RCA CHECK] Processing trace {trace_id}")

        # --------------------------------------------------------
        # Load evaluator results for this trace
        # --------------------------------------------------------

        query = """
            SELECT * FROM c
            WHERE c.trace_id = @trace_id
        """

        eval_items = list(EVALS.query_items(
            query=query,
            parameters=[{"name": "@trace_id", "value": trace_id}],
            enable_cross_partition_query=True
        ))

        present = {e.get("evaluator") for e in eval_items}

        # --------------------------------------------------------
        # Wait if not all active evaluators completed
        # --------------------------------------------------------

        if not required.issubset(present):
            logger.info(
                f"[RCA WAIT] {trace_id} "
                f"Required={required}, Present={present}"
            )
            continue

        # --------------------------------------------------------
        # Prevent duplicate RCA generation
        # --------------------------------------------------------

        existing = list(RCA.query_items(
            query="SELECT * FROM c WHERE c.trace_id = @trace_id",
            parameters=[{"name": "@trace_id", "value": trace_id}],
            enable_cross_partition_query=True
        ))

        if existing:
            logger.info(f"[RCA SKIP] RCA already exists for {trace_id}")
            continue

        # --------------------------------------------------------
        # Load raw trace
        # --------------------------------------------------------

        raw_items = list(RAW.query_items(
            query="SELECT * FROM c WHERE c.trace_id = @trace_id",
            parameters=[{"name": "@trace_id", "value": trace_id}],
            enable_cross_partition_query=True
        ))

        if not raw_items:
            logger.error(f"[RCA ERROR] Raw trace missing: {trace_id}")
            continue

        raw_trace = raw_items[0]

        # --------------------------------------------------------
        # Run RCA logic
        # --------------------------------------------------------

        findings, evidence, suggestions = analyze_trace(raw_trace, eval_items)

        # --------------------------------------------------------
        # Write RCA result
        # --------------------------------------------------------

        rca_doc = {
            "id": f"{trace_id}:rca",
            "trace_id": trace_id,
            "findings": findings,
            "evidence": evidence,
            "suggestions": suggestions,
            "status": "completed",
            "evaluators_used": list(required)
        }

        RCA.upsert_item(rca_doc)

        logger.info(f"[RCA DONE] RCA generated for {trace_id}")