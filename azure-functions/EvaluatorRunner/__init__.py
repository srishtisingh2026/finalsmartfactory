import logging
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import random
import time
from datetime import datetime, timezone

from azure.functions import DocumentList
from azure.cosmos import exceptions

from shared.audit import audit_log
from shared.cosmos import evaluators_read, evaluations_write
from Templates.engine import run_evaluator, METHOD_REGISTRY


# --------------------------------------------------
# Normalize trace for evaluator templates
# --------------------------------------------------
def normalize_trace(trace: dict) -> dict:

    retrieved = trace.get("retrieved_context", []) or []

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
        exec_cfg = ev.get("execution", {}) or {}

        if not evaluator_id or not template_id:
            logging.warning(f"[EvaluatorRunner] Invalid evaluator config: {ev}")
            continue

        logging.info(f"[EvaluatorRunner] Running evaluator '{evaluator_id}'")

        executed_count = 0

        # Handle ensemble toggle
        enable_ensemble = ev.get("enable_ensemble", False)
        
        all_deployments = exec_cfg.get(
            "ensemble_deployments",
            ["gpt-4o-mini"]
        )
        
        # If ensemble is disabled, only use the first model to save quota
        deployments = all_deployments if enable_ensemble else [all_deployments[0]]

        variance_threshold = exec_cfg.get("variance_threshold", 0.10)

        requires_context = exec_cfg.get("requires_context", False)

        sampling_rate = exec_cfg.get("sampling_rate", 1.0)

        delay_ms = exec_cfg.get("delay_ms", 0)

        # --------------------------------------------------
        # Iterate traces
        # --------------------------------------------------

        for trace in documents:

            trace_id = trace.get("trace_id") or trace.get("id")

            if not trace_id:
                continue

            retrieval = trace.get("retrieval", {}) or {}
            retrieved_context = trace.get("retrieved_context", []) or []

            eval_id = f"{trace_id}:{evaluator_id}"

            # --------------------------------------------------
            # Dynamic context requirement check
            # --------------------------------------------------

            if requires_context:

                retrieval_executed = retrieval.get("executed", False)

                if not retrieval_executed or not retrieved_context:

                    logging.info(
                        f"[EvaluatorRunner] Skipping '{evaluator_name}' for trace {trace_id} "
                        f"(requires_context=true but no retrieval context)"
                    )

                    skip_doc = {
                        "id": eval_id,
                        "trace_id": trace_id,

                        "evaluator": evaluator_name,
                        "evaluator_id": evaluator_id,
                        "template_id": template_id,

                        "status": "skipped",
                        "reason": "no_retrieval_context",

                        "score": None,
                        "classification": None,

                        "evaluation_cost_usd": 0,

                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    try:
                        evaluations_write.upsert_item(skip_doc)
                        executed_count += 1
                    except Exception:
                        logging.exception("[EvaluatorRunner] Failed to persist skipped evaluation")

                    continue

            # --------------------------------------------------
            # Sampling
            # --------------------------------------------------

            if random.random() > sampling_rate:
                continue

            # --------------------------------------------------
            # Optional delay
            # --------------------------------------------------

            if delay_ms > 0:
                time.sleep(delay_ms / 1000)

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
            # Run ENSEMBLE
            # --------------------------------------------------

            start_time = time.time()

            scores = {}
            classifications = {}
            raw_outputs = {}

            total_eval_cost = 0.0

            llm_ensemble_score = None
            metric_score = None
            metric_calculation = "Not calculated"
            variance = None
            agreement = None

            try:

                normalized = normalize_trace(trace)
                # ---------------------------------------------
                # Run trace-level evaluation methods (once)
                # ---------------------------------------------
                # Dynamic Field Selection (Comparison Map)
                # ---------------------------------------------
                cmap = exec_cfg.get("comparison_map", {"source": "context", "target": "response"})
                src_key = cmap.get("source", "context")
                tgt_key = cmap.get("target", "response")

                val1 = normalized.get(src_key, "")
                val2 = normalized.get(tgt_key, "")

                # ---------------------------------------------
                # Run trace-level evaluation methods (once)
                # ---------------------------------------------
                method_scores = {}

                methods = exec_cfg.get("methods", [])

                for m in methods:
                    method_type = m.get("type")
                    fn = METHOD_REGISTRY.get(method_type)
                    if not fn:
                        logging.warning(f"[EvaluatorRunner] Unsupported method: {method_type}")
                        continue
                    method_scores[method_type] = fn(val1, val2)

                # -------------------------------
                # Aggregate Metric Score (Weighted)
                # -------------------------------
                weighted_metric_sum = 0.0
                total_method_weight = 0.0
                logic_parts = []

                for m in methods:
                    m_type = m.get("type")
                    m_weight = m.get("weight", 0)
                    m_score = method_scores.get(m_type)

                    if m_score is not None:
                        # If no weight provided in JSON, default to 1.0 for simple averaging
                        actual_w = m_weight if m_weight > 0 else 1.0
                        
                        weighted_metric_sum += m_score * actual_w
                        total_method_weight += actual_w
                        
                        logic_parts.append(f"({actual_w} * {m_score})")

                metric_calculation = "No metrics"
                if total_method_weight > 0:
                    metric_score = round(weighted_metric_sum / total_method_weight, 2)
                    metric_calculation = f"Weighted Sum ({src_key} vs {tgt_key}): ({' + '.join(logic_parts)}) / {total_method_weight} = {metric_score}"
                else:
                    metric_score = None

                for deployment in deployments:

                    result = run_evaluator(
                        evaluator_id,
                        normalized,
                        deployment=deployment,
                        trace_methods=method_scores
                    )

                    score = result.get("score")
                    classification = result.get("classification")
                    raw_output = result.get("raw_output")
                    cost = result.get("cost_usd", 0)

                    if isinstance(score, (int, float)):
                        scores[deployment] = round(float(score), 2)

                    if classification:
                        classifications[deployment] = classification

                    raw_outputs[deployment] = raw_output

                    total_eval_cost += cost

                # -------------------------------
                # Aggregate LLM score
                # -------------------------------

                score_values = list(scores.values())

                llm_ensemble_score = None
                variance = None

                if score_values:

                    llm_ensemble_score = round(
                        sum(score_values) / len(score_values),
                        2
                    )

                    if len(score_values) > 1:

                        mean = llm_ensemble_score

                        variance = round(
                            sum((s - mean) ** 2 for s in score_values)
                            / len(score_values),
                            4,
                        )

                # -------------------------------
                # Hybrid Aggregation (Dynamic Weights)
                # -------------------------------
                
                # Read metric_weight from config, fallback to 0.5
                metric_weight = exec_cfg.get("metric_weight", 0.5)
                
                # Defensive check: ensure within [0, 1]
                if not isinstance(metric_weight, (int, float)) or not (0 <= metric_weight <= 1):
                    metric_weight = 0.5
                
                # Derive llm_weight
                llm_weight = round(1.0 - metric_weight, 2)

                # Default to 1.0 if no LLM score available to avoid penalizing grounding
                safe_llm_score = llm_ensemble_score if llm_ensemble_score is not None else 1.0
                
                if metric_score is None:
                    final_score = safe_llm_score
                else:
                    final_score = round(
                        (metric_weight * metric_score) +
                        (llm_weight * safe_llm_score),
                        2
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
                reason = None

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
                reason = str(e)

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

                "deployments_used": deployments,
                "individual_scores": scores,
                "individual_classifications": classifications,

                "llm_ensemble_score": llm_ensemble_score,
                "metric_score": metric_score,
                "metric_calculation": metric_calculation,
                
                "variance": variance,
                "agreement": agreement,
                "unstable": unstable,

                "score": final_score,
                "classification": final_classification,
                "raw_output": raw_outputs,

                "status": status,
                "reason": reason,

                "evaluation_cost_usd": round(total_eval_cost, 6),

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