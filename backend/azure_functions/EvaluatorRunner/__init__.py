import os
import logging
import time
from datetime import datetime, timezone

from azure.functions import DocumentList
from azure.cosmos import CosmosClient, exceptions

from evaluators.registry import EVALUATORS
from utils.audit import audit_log


# --------------------------------------------------
# Validate environment variables
# --------------------------------------------------
COSMOS_CONN_READ = os.getenv("COSMOS_CONN_READ")
COSMOS_CONN_WRITE = os.getenv("COSMOS_CONN_WRITE")

if not COSMOS_CONN_READ:
    raise RuntimeError("❌ Missing environment variable: COSMOS_CONN_READ")

if not COSMOS_CONN_WRITE:
    raise RuntimeError("❌ Missing environment variable: COSMOS_CONN_WRITE")


# --------------------------------------------------
# Cosmos Clients
# --------------------------------------------------
COSMOS_READ = CosmosClient.from_connection_string(COSMOS_CONN_READ)
COSMOS_WRITE = CosmosClient.from_connection_string(COSMOS_CONN_WRITE)

DB_READ = COSMOS_READ.get_database_client("llmops-data")
DB_WRITE = COSMOS_WRITE.get_database_client("llmops-data")

EVALUATORS_CONTAINER = DB_READ.get_container_client("evaluators")
EVALS_CONTAINER = DB_WRITE.get_container_client("evaluations")


# --------------------------------------------------
# Azure Function Entry
# --------------------------------------------------
def main(documents: DocumentList):
    logging.error("🔥 EvaluatorRunner TRIGGERED 🔥")

    if not documents:
        logging.warning("[EvaluatorRunner] No documents received")
        return

    trace_count = len(documents)
    logging.info(f"[EvaluatorRunner] Processing {trace_count} traces")

    # --------------------------------------------------
    # Load enabled evaluators
    # --------------------------------------------------
    try:
        evaluators = list(
            EVALUATORS_CONTAINER.query_items(
                query="SELECT * FROM c WHERE c.status = 'active'",
                enable_cross_partition_query=True,
            )
        )
    except Exception:
        logging.exception("[EvaluatorRunner] Failed to load evaluators")
        return

    if not evaluators:
        logging.warning("[EvaluatorRunner] No enabled evaluators found")
        return

    # --------------------------------------------------
    # Process evaluators
    # --------------------------------------------------
    for ev in evaluators:
        evaluator_name = ev.get("score_name")
        execution_cfg = ev.get("execution", {})

        if not evaluator_name:
            continue

        logging.info(f"[EvaluatorRunner] Starting evaluator '{evaluator_name}'")

        evaluated = 0

        for trace in documents:
            trace_id = trace.get("trace_id") or trace.get("id")
            if not trace_id:
                continue

            # -----------------------------
            # Deterministic Sampling
            # -----------------------------
            sampling_rate = execution_cfg.get("sampling_rate", 1.0)
            if not isinstance(sampling_rate, (int, float)):
                sampling_rate = 1.0

            sampling_rate = max(0.0, min(1.0, sampling_rate))

            # stable hash → reproducible sampling
            hash_val = hash(f"{trace_id}:{evaluator_name}") % 1000
            if (hash_val / 1000.0) > sampling_rate:
                continue

            # -----------------------------
            # Optional delay
            # -----------------------------
            delay_ms = execution_cfg.get("delay_ms", 0)
            if delay_ms > 0:
                time.sleep(delay_ms / 1000)

            # -----------------------------
            # Evaluator function
            # -----------------------------
            template_id = ev.get("template", {}).get("id")
            evaluator_fn = EVALUATORS.get(template_id)

            if not evaluator_fn:
                logging.warning(
                    f"[EvaluatorRunner] No evaluator registered for template {template_id}"
                )
                continue

            eval_id = f"{trace_id}:{evaluator_name}"

            # -----------------------------
            # Idempotency
            # -----------------------------
            try:
                EVALS_CONTAINER.read_item(
                    item=eval_id,
                    partition_key=trace_id
                )
                continue
            except exceptions.CosmosResourceNotFoundError:
                pass
            except Exception:
                logging.exception("[EvaluatorRunner] Idempotency check failed")
                continue

            # -----------------------------
            # Run evaluator
            # -----------------------------
            start_time = time.time()
            try:
                result = evaluator_fn(trace)
                status = "completed"
            except Exception as e:
                logging.exception(
                    f"[EvaluatorRunner] Evaluator {evaluator_name} failed for trace {trace_id}"
                )
                result = {"score": None, "explanation": str(e)}
                status = "failed"

            duration_ms = int((time.time() - start_time) * 1000)

            # -----------------------------
            # Persist evaluation
            # -----------------------------
            doc = {
                "id": eval_id,
                "trace_id": trace_id,
                "evaluator_name": evaluator_name,
                "score": result.get("score"),
                "explanation": result.get("explanation", ""),
                "status": status,
                "duration_ms": duration_ms,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            try:
                EVALS_CONTAINER.upsert_item(doc)
                evaluated += 1
            except Exception:
                logging.exception("[EvaluatorRunner] Failed to persist evaluation")

        # --------------------------------------------------
        # ✅ AUDIT: Evaluator Run Completed (ONCE)
        # --------------------------------------------------
        audit_log(
            action="Evaluator Run Completed",
            type="evaluator",
            user="system",
            details=(
                f"Ran evaluator '{evaluator_name}' "
                f"on {evaluated} traces (out of {trace_count})"
            ),
        )

        logging.info(
            f"[EvaluatorRunner] Completed evaluator '{evaluator_name}' "
            f"({evaluated}/{trace_count} traces)"
        )
