import logging
import random
import time
from datetime import datetime, timezone

from azure.functions import DocumentList
from azure.cosmos import exceptions

from shared.audit import audit_log
from shared.cosmos import evaluators_read, evaluations_write
from Templates.engine import run_evaluator


# --------------------------------------------------
# Normalize trace for evaluator templates
# --------------------------------------------------
def normalize_trace(trace: dict) -> dict:
    retrieved = trace.get("retrieved_context", [])
    context_text = "\n\n".join(retrieved) if isinstance(retrieved, list) else ""

    return {
        "input": trace.get("input_text", ""),
        "context": context_text,
        "response": trace.get("output_text", ""),
        "_raw": trace,
    }


# --------------------------------------------------
# Azure Function Entry
# --------------------------------------------------
def main(documents: DocumentList):
    logging.info("🔥 EvaluatorRunner TRIGGERED 🔥")

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
        evaluator_id = ev.get("id")
        evaluator_name = ev.get("score_name")
        template_id = ev.get("template", {}).get("id")
        exec_cfg = ev.get("execution", {})

        if not evaluator_id or not template_id:
            logging.warning(f"[EvaluatorRunner] Invalid evaluator config: {ev}")
            continue

        logging.info(f"[EvaluatorRunner] Running evaluator '{evaluator_id}'")

        executed_count = 0

        # 🔥 NEW: deployment-based ensemble
        deployments = exec_cfg.get(
            "ensemble_deployments",
            ["gpt-4o-mini"]  # fallback default
        )

        variance_threshold = exec_cfg.get("variance_threshold", 0.10)

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
            # Idempotency Check
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
            # Run ENSEMBLE (deployment-based)
            # --------------------------------------------------
            start_time = time.time()

            scores = {}
            classifications = {}
            raw_outputs = {}

            try:
                normalized = normalize_trace(trace)

                for deployment in deployments:
                    result = run_evaluator(
                        evaluator_id,
                        normalized,
                        deployment=deployment
                    )

                    score = result.get("score")
                    classification = result.get("classification")
                    raw_output = result.get("raw_output")

                    if isinstance(score, (int, float)):
                        scores[deployment] = round(float(score), 2)

                    if classification:
                        classifications[deployment] = classification

                    raw_outputs[deployment] = raw_output

                # -------------------------------
                # Aggregate score
                # -------------------------------
                score_values = list(scores.values())
                final_score = None
                variance = None

                if score_values:
                    final_score = round(
                        sum(score_values) / len(score_values), 2
                    )

                    if len(score_values) > 1:
                        mean = final_score
                        variance = round(
                            sum((s - mean) ** 2 for s in score_values)
                            / len(score_values),
                            4,
                        )

                # -------------------------------
                # Aggregate classification
                # -------------------------------
                class_values = list(classifications.values())

                if not class_values:
                    final_classification = None
                    agreement = None

                elif len(set(class_values)) == 1:
                    final_classification = class_values[0]
                    agreement = 1.0

                else:
                    final_classification = "disagreement"
                    agreement = round(
                        max(
                            class_values.count(c)
                            for c in set(class_values)
                        )
                        / len(class_values),
                        2,
                    )

                # -------------------------------
                # Stability check
                # -------------------------------
                unstable = (
                    variance is not None
                    and variance > variance_threshold
                )

                status = "unstable" if unstable else "completed"

            except Exception as e:
                logging.exception(
                    f"[EvaluatorRunner] Evaluator '{evaluator_id}' failed for trace {trace_id}"
                )
                final_score = None
                variance = None
                agreement = None
                final_classification = "failed"
                raw_outputs = {"error": str(e)}
                unstable = False
                status = "failed"

            duration_ms = int((time.time() - start_time) * 1000)

            # --------------------------------------------------
            # Save evaluation record
            # --------------------------------------------------
            doc = {
                "id": eval_id,
                "trace_id": trace_id,
                "evaluator": evaluator_name,
                "evaluator_id": evaluator_id,
                "template_id": template_id,

                # 🔥 Deployment ensemble fields
                "deployments_used": deployments,
                "individual_scores": scores,
                "individual_classifications": classifications,
                "ensemble_score": final_score,
                "variance": variance,
                "agreement": agreement,
                "unstable": unstable,

                # Backward compatibility
                "score": final_score,
                "classification": final_classification,
                "raw_output": raw_outputs,

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