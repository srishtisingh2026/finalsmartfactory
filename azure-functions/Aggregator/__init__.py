import os
from datetime import datetime, timezone
from collections import defaultdict

from azure.cosmos import CosmosClient

# 🔐 Key Vault (shared across App Service & Functions)
from shared.secrets import get_secret


def main(mytimer):

    # ==========================================
    # Connect to Cosmos DB (via Key Vault)
    # ==========================================
    COSMOS_CONN_WRITE = get_secret("COSMOS-CONN-WRITE")

    cosmos = CosmosClient.from_connection_string(COSMOS_CONN_WRITE)
    db = cosmos.get_database_client("llmops-data")

    traces_container = db.get_container_client("traces")
    evals_container = db.get_container_client("evaluations")
    metrics_container = db.get_container_client("metrics")

    # ==========================================
    # 1. Load Traces
    # ==========================================
    traces = list(
        traces_container.query_items(
            query="SELECT * FROM c",
            enable_cross_partition_query=True
        )
    )

    if not traces:
        return

    # ==========================================
    # 2. Load Evaluations
    # ==========================================
    evaluations = list(
        evals_container.query_items(
            query="SELECT * FROM c",
            enable_cross_partition_query=True
        )
    )

    # ==========================================
    # 2B. Build eval lookup safely
    # ==========================================
    evals_by_trace = defaultdict(dict)

    for e in evaluations:
        trace_id = e.get("trace_id")
        if not trace_id:
            continue

        # evaluator_name fix 👉 prefer evaluator_id, fallback to evaluator
        evaluator_name = (
            e.get("evaluator_id")
            or e.get("evaluator")
        )

        if not evaluator_name:
            # skip malformed evaluation docs
            continue

        evals_by_trace[trace_id][evaluator_name] = e.get("score")

    # ==========================================
    # 3. Build Sessions
    # ==========================================
    sessions = {}
    for t in sorted(traces, key=lambda x: x.get("timestamp", "")):
        sid = t.get("session_id")
        if not sid:
            continue

        if sid not in sessions:
            sessions[sid] = {
                "session_id": sid,
                "user_id": t.get("user_id"),
                "first_trace_id": t.get("trace_id"),
                "session_start_time": t.get("timestamp"),
            }

    # ==========================================
    # 4. Trace Metrics
    # ==========================================
    total_traces = len(traces)
    total_users = set()

    total_tokens = 0
    total_cost = 0.0
    total_latency = 0

    tokens_by_model = defaultdict(int)
    cost_by_model = defaultdict(float)
    trace_count_by_model = defaultdict(int)

    trace_count_by_name = defaultdict(int)
    cost_by_trace_name = defaultdict(float)
    tokens_by_trace_name = defaultdict(int)

    for t in traces:
        tokens = t.get("tokens", 0)
        cost = t.get("cost", 0.0)
        latency = t.get("latency_ms", 0)

        total_tokens += tokens
        total_cost += cost
        total_latency += latency

        model = t.get("model", "unknown")
        tokens_by_model[model] += tokens
        cost_by_model[model] += cost
        trace_count_by_model[model] += 1

        name = t.get("trace_name", "unknown")
        trace_count_by_name[name] += 1
        cost_by_trace_name[name] += cost
        tokens_by_trace_name[name] += tokens

        if t.get("user_id"):
            total_users.add(t["user_id"])

    # ==========================================
    # 5. Evaluation Summary
    # ==========================================
    eval_score_sum = defaultdict(float)
    eval_count = defaultdict(int)

    for scores in evals_by_trace.values():
        for evaluator_name, score in scores.items():
            if score is not None:
                eval_score_sum[evaluator_name] += score
                eval_count[evaluator_name] += 1

    evaluation_summary = {}
    for evaluator_name in eval_count:
        count = eval_count[evaluator_name]
        if count > 0:
            evaluation_summary[evaluator_name] = {
                "count": count,
                "avg_score": round(eval_score_sum[evaluator_name] / count, 3)
            }

    # ==========================================
    # 6. Final KPI Snapshot
    # ==========================================
    metrics = {
        "id": "metrics_snapshot",
        "partitionKey": "metrics_snapshot",
        "generated_at": datetime.now(timezone.utc).isoformat(),

        "total_traces": total_traces,
        "total_sessions": len(sessions),
        "total_users": len(total_users),

        "avg_traces_per_session": round(
            total_traces / len(sessions), 2
        ) if sessions else 0,

        "avg_latency_ms": round(
            total_latency / total_traces, 2
        ) if total_traces else 0,

        "total_tokens": total_tokens,
        "total_cost": round(total_cost, 6),

        "tokens_by_model": dict(tokens_by_model),
        "cost_by_model": dict(cost_by_model),
        "trace_count_by_model": dict(trace_count_by_model),

        "trace_count_by_name": dict(trace_count_by_name),
        "cost_by_trace_name": dict(cost_by_trace_name),
        "tokens_by_trace_name": dict(tokens_by_trace_name),

        "evaluation_summary": evaluation_summary
    }

    # ==========================================
    # 7. Save Metrics
    # ==========================================
    metrics_container.upsert_item(metrics)
