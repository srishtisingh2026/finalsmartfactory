import os
from datetime import datetime, timezone
from collections import defaultdict

from azure.cosmos import CosmosClient
from shared.secrets import get_secret


def main(mytimer):

    # ==========================================
    # Connect to Cosmos DB
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
    # 3. Build Evaluation Lookup
    # ==========================================
    evals_by_trace = defaultdict(dict)

    for e in evaluations:
        trace_id = e.get("trace_id")
        if not trace_id:
            continue

        evaluator_name = e.get("evaluator_id") or e.get("evaluator")
        if not evaluator_name:
            continue

        evals_by_trace[trace_id][evaluator_name] = e.get("score")

    # ==========================================
    # 4. Session Aggregation
    # ==========================================
    sessions = {}

    for t in sorted(traces, key=lambda x: x.get("request", {}).get("timestamp", 0)):

        session_obj = t.get("session", {})
        sid = session_obj.get("session_id")

        if not sid:
            continue

        if sid not in sessions:
            sessions[sid] = {
                "session_id": sid,
                "user_id": session_obj.get("user_id"),
                "first_trace_id": t.get("trace_id"),
                "session_start_time": t.get("request", {}).get("timestamp"),
            }

    # ==========================================
    # 5. Trace Metrics
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

        usage = t.get("usage", {})
        cost_obj = t.get("cost", {})
        performance = t.get("performance", {})
        model_info = t.get("model_info", {})
        session_obj = t.get("session", {})

        tokens = usage.get("total_tokens", 0)
        cost = cost_obj.get("total_cost_usd", 0.0)
        latency = performance.get("latency_ms", 0)

        total_tokens += tokens
        total_cost += cost
        total_latency += latency

        model = model_info.get("model", "unknown")
        tokens_by_model[model] += tokens
        cost_by_model[model] += cost
        trace_count_by_model[model] += 1

        trace_name = t.get("trace_name", "unknown")
        trace_count_by_name[trace_name] += 1
        cost_by_trace_name[trace_name] += cost
        tokens_by_trace_name[trace_name] += tokens

        user_id = session_obj.get("user_id")
        if user_id:
            total_users.add(user_id)

    # ==========================================
    # 6. Evaluation Summary
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
    # 7. Final KPI Snapshot
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
    # 8. Save Metrics
    # ==========================================
    metrics_container.upsert_item(metrics)