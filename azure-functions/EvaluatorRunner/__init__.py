import logging
import random
import time
from datetime import datetime, timezone

from azure.functions import DocumentList
from azure.cosmos import exceptions

from Templates.registry import EVALUATORS
from shared.audit import audit_log
from shared.cosmos import evaluators_read, evaluations_write


# --------------------------------------------------
# Normalize trace for evaluator templates
# --------------------------------------------------
def normalize_trace(trace: dict) -> dict:
    return {
        "input": trace.get("input") or trace.get("question", ""),
        "context": trace.get("context", ""),
        "response": trace.get("output") or trace.get("answer", ""),
        "_raw": trace
    }


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
    # Load active evaluators
    # --------------------------------------------------
    try:
        evaluators = list(
            evaluators_read.query_items(
                query="SELECT * FROM c WHERE c.status = 'active'",
                enable_cross_partition_query=True,
            )
        )
    except Exception:
        logging.exception("[EvaluatorRunner] Failed to load evaluators")
        return

    if not evaluators:
        logging.warning("[EvaluatorRunner] No active evaluators found")
        return

    # --------------------------------------------------
    # Process each evaluator
    # --------------------------------------------------
    for ev in evaluators:
        evaluator_name = ev.get("score_name")          # e.g. "conciseness"
        evaluator_id = ev.get("id")                    # e.g. "conciseness-v1"
        template_id = ev.get("template", {}).get("id") # e.g. "conciseness_llm"

        if not evaluator_name or not evaluator_id or not template_id:
            logging.warning(f"[EvaluatorRunner] Invalid evaluator config: {ev}")
            continue

        registry_key = f"{evaluator_name}_llm"
        evaluator_fn = EVALUATORS.get(registry_key)

        if not evaluator_fn:
            logging.warning(f"[EvaluatorRunner] No evaluator registered for '{registry_key}'")
            continue

        logging.info(
            f"[EvaluatorRunner] Running evaluator '{evaluator_id}' using template '{registry_key}'"
        )

        executed_count = 0
        exec_cfg = ev.get("execution", {})

        # --------------------------------------------------
        # Iterate traces
        # --------------------------------------------------
        for trace in documents:
            trace_id = trace.get("trace_id") or trace.get("id")
            if not trace_id:
                continue

            # Sampling
            sampling_rate = exec_cfg.get("sampling_rate", 1.0)
            if random.random() > sampling_rate:
                continue

            # Optional delay
            delay_ms = exec_cfg.get("delay_ms", 0)
            if delay_ms > 0:
                time.sleep(delay_ms / 1000)

            eval_id = f"{trace_id}:{evaluator_id}"

            # --------------------------------------------------
            # Idempotency
            # --------------------------------------------------
            try:
                evaluations_write.read_item(eval_id, partition_key=trace_id)
                continue
            except exceptions.CosmosResourceNotFoundError:
                pass
            except Exception:
                logging.exception("[EvaluatorRunner] Idempotency check failed")
                continue

            # --------------------------------------------------
            # Run evaluator
            # --------------------------------------------------
            start_time = time.time()

            try:
                normalized = normalize_trace(trace)
                result = evaluator_fn(evaluator_id, normalized)

                score = result.get("score")
                raw_output = result.get("raw_output")

                # ✔ Round score to 2 decimals (no trailing zeros)
                if isinstance(score, (int, float)):
                    score = round(float(score), 2)

                status = "completed"
            except Exception as e:
                logging.exception(
                    f"[EvaluatorRunner] Evaluator '{evaluator_id}' failed for trace {trace_id}"
                )
                score = None
                raw_output = str(e)
                status = "failed"

            duration_ms = int((time.time() - start_time) * 1000)

            # --------------------------------------------------
            # Save record to Cosmos
            # --------------------------------------------------
            doc = {
                "id": eval_id,
                "trace_id": trace_id,
                "evaluator": evaluator_name,
                "evaluator_id": evaluator_id,
                "template_id": template_id,
                "score": score,
                "raw_output": raw_output,
                "status": status,
                "duration_ms": duration_ms,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            try:
                evaluations_write.upsert_item(doc)
                executed_count += 1
            except Exception:
                logging.exception("[EvaluatorRunner] Failed to persist evaluation")

        # --------------------------------------------------
        # Audit Log
        # --------------------------------------------------
        audit_log(
            action="Evaluator Run Completed",
            type="evaluator",
            user="system",
            details=f"Ran evaluator '{evaluator_id}' on {executed_count}/{trace_count} traces",
        )

        logging.info(
            f"[EvaluatorRunner] Completed evaluator '{evaluator_id}' "
            f"({executed_count}/{trace_count})"
        )
