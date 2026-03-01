def analyze_trace(raw, evals):
    findings = []
    evidence = []
    suggestions = []

    # ------------------------------------------------------------
    # Safe evaluator mapping
    # ------------------------------------------------------------
    eval_map = {
        e.get("evaluator"): e
        for e in evals
        if e.get("evaluator") is not None
    }

    # ------------------------------------------------------------
    # Extract telemetry signals
    # ------------------------------------------------------------
    retrieval_executed = raw.get("retrieval_executed", False)
    documents_found = raw.get("documents_found", 0)
    retrieval_confidence = raw.get("retrieval_confidence", 0.0)

    spans = raw.get("spans", [])
    llm_span = next((s for s in spans if s.get("type") == "llm"), {})
    completion_tokens = llm_span.get("usage", {}).get("completion_tokens", 0)
    temperature = llm_span.get("metadata", {}).get("temperature", 0)

    context_score = eval_map.get("context_relevance", {}).get("score")
    halluc_score = eval_map.get("hallucination", {}).get("score")
    concise_score = eval_map.get("conciseness", {}).get("score")

    # ------------------------------------------------------------
    # 1️⃣ Retrieval Failure
    # ------------------------------------------------------------
    if retrieval_executed and documents_found == 0:
        findings.append("retrieval_failed")
        evidence.append("documents_found=0")
        suggestions.append("Improve embeddings, chunking, or increase top_k.")

    # ------------------------------------------------------------
    # 2️⃣ Weak Retrieval Quality
    # ------------------------------------------------------------
    if documents_found > 0 and retrieval_confidence < 0.4:
        findings.append("weak_retrieval_quality")
        evidence.append(f"retrieval_confidence={retrieval_confidence}")
        suggestions.append("Use reranker or improve embedding model.")

    # ------------------------------------------------------------
    # 3️⃣ Context Ignored During Generation
    # ------------------------------------------------------------
    if (
        context_score is not None
        and context_score < 0.3
        and documents_found > 0
        and retrieval_confidence >= 0.4
    ):
        findings.append("generation_ignored_context")
        evidence.append(
            f"context_relevance={context_score}, conf={retrieval_confidence}"
        )
        suggestions.append("Strengthen grounding instructions or enforce citations.")

    # ------------------------------------------------------------
    # 4️⃣ Hallucination Issues
    # ------------------------------------------------------------
    if halluc_score is not None and halluc_score < 0.4:
        if documents_found == 0:
            findings.append("hallucination_due_to_no_context")
            evidence.append(f"hallucination={halluc_score}")
            suggestions.append("Force refusal when no documents are retrieved.")
        elif retrieval_confidence >= 0.5:
            findings.append("generation_overreach")
            evidence.append(
                f"hallucination={halluc_score}, conf={retrieval_confidence}"
            )
            suggestions.append("Reduce temperature or enforce stricter grounding.")

    # ------------------------------------------------------------
    # 5️⃣ Over-Verbose Generation
    # ------------------------------------------------------------
    if concise_score is not None and concise_score < 0.4:
        findings.append("over_verbose_answer")
        evidence.append(
            f"conciseness={concise_score}, completion_tokens={completion_tokens}"
        )
        suggestions.append("Add stricter brevity constraints in prompt.")

    # ------------------------------------------------------------
    # 6️⃣ Excessive Token Usage
    # ------------------------------------------------------------
    if completion_tokens > 300:
        findings.append("excessive_generation_length")
        evidence.append(f"completion_tokens={completion_tokens}")
        suggestions.append("Limit max_tokens or enforce concise output.")

    # ------------------------------------------------------------
    # 7️⃣ Intent Mismatch
    # ------------------------------------------------------------
    span_int = next(
        (s for s in spans if s.get("type") == "intent-classification"), None
    )

    if span_int:
        span_intent = span_int.get("metadata", {}).get("intent")
        if span_intent and raw.get("intent") != span_intent:
            findings.append("intent_mismatch")
            evidence.append(
                f"trace.intent={raw.get('intent')} vs span.intent={span_intent}"
            )
            suggestions.append("Investigate classifier consistency.")

    # ------------------------------------------------------------
    # Remove duplicates
    # ------------------------------------------------------------
    findings = list(dict.fromkeys(findings))
    evidence = list(dict.fromkeys(evidence))
    suggestions = list(dict.fromkeys(suggestions))

    # ------------------------------------------------------------
    # Healthy case handling
    # ------------------------------------------------------------
    if not findings:
        findings.append("no_anomaly_detected")
        evidence.append("All evaluator thresholds satisfied")
        suggestions.append("No action required")

    return findings, evidence, suggestions