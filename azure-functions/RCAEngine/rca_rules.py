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
    # Extract telemetry signals early (needed for skip reasoning)
    # ------------------------------------------------------------

    retrieval_executed = raw.get("retrieval_executed", False)
    documents_found = raw.get("documents_found", 0)

    retrieval_confidence = raw.get("retrieval_confidence")

    if retrieval_confidence is None:
        retrieval_confidence = (
            raw.get("rag_data", {})
            .get("retrieval_scores", {})
            .get("avg_score", 0.0)
        )

    spans = raw.get("spans", [])

    llm_span = next(
        (s for s in spans if s.get("type") == "llm"),
        {}
    )

    completion_tokens = (
        llm_span.get("usage", {}).get("completion_tokens")
        or raw.get("usage", {}).get("completion_tokens", 0)
    )

    temperature = llm_span.get("metadata", {}).get("temperature", 0)

    output = raw.get("output")

    # Add telemetry evidence (helps explain RCA)
    evidence.append(f"documents_found={documents_found}")
    evidence.append(f"retrieval_confidence={retrieval_confidence}")

    # ------------------------------------------------------------
    # Track evaluator states dynamically
    # ------------------------------------------------------------

    completed_evaluators = []
    skipped_evaluators = []
    failed_evaluators = []

    for e in evals:

        name = e.get("evaluator")
        status = e.get("status")

        if not name:
            continue

        if status == "completed":
            completed_evaluators.append(name)

        elif status == "skipped":

            skipped_evaluators.append(name)

            evidence.append(f"{name}_evaluator_skipped")

            # ----------------------------------------
            # Dynamically infer skip reason
            # ----------------------------------------

            reason = "dependency_condition_not_met"

            if documents_found == 0:
                reason = "no_retrieved_documents"

            elif not retrieval_executed:
                reason = "retrieval_not_executed"

            elif not output:
                reason = "no_model_output"

            evidence.append(f"{name}_skip_reason={reason}")

        elif status == "failed":

            failed_evaluators.append(name)

            evidence.append(f"{name}_evaluator_failed")

    # ------------------------------------------------------------
    # Extract evaluator scores
    # ------------------------------------------------------------

    def get_score(name):

        ev = eval_map.get(name)

        if not ev:
            return None

        if ev.get("status") != "completed":
            return None

        return ev.get("score")

    context_score = get_score("context_relevance")
    halluc_score = get_score("hallucination")
    concise_score = get_score("conciseness")

    # ------------------------------------------------------------
    # 1 Retrieval Failure
    # ------------------------------------------------------------

    if retrieval_executed and documents_found == 0:

        findings.append("retrieval_failed")

        evidence.append("documents_found=0")

        suggestions.append(
            "Improve embeddings, chunking, or increase top_k."
        )

    # ------------------------------------------------------------
    # 2 Weak Retrieval (Cosine)
    # ------------------------------------------------------------

    if documents_found > 0 and retrieval_confidence < 0.5:

        findings.append("weak_retrieval_quality")

        evidence.append(
            f"cosine_similarity={retrieval_confidence}"
        )

        suggestions.append(
            "Improve embeddings, chunking strategy, or increase retrieval_k."
        )

    # ------------------------------------------------------------
    # 3 Moderate Retrieval
    # ------------------------------------------------------------

    if 0.5 <= retrieval_confidence < 0.65:

        findings.append("moderate_retrieval_confidence")

        evidence.append(
            f"cosine_similarity={retrieval_confidence}"
        )

        suggestions.append(
            "Consider reranking retrieved chunks or improving chunk semantic quality."
        )

    # ------------------------------------------------------------
    # 4 Context Ignored During Generation
    # ------------------------------------------------------------

    if (
        context_score is not None
        and context_score < 0.3
        and documents_found > 0
        and retrieval_confidence >= 0.65
    ):

        findings.append("generation_ignored_context")

        evidence.append(
            f"context_relevance={context_score}, cosine={retrieval_confidence}"
        )

        suggestions.append(
            "Strengthen grounding instructions or enforce citations."
        )

    # ------------------------------------------------------------
    # 5 Hallucination Issues
    # ------------------------------------------------------------

    if halluc_score is not None and halluc_score < 0.4:

        if documents_found == 0:

            findings.append("hallucination_due_to_no_context")

            evidence.append(
                f"hallucination_score={halluc_score}"
            )

            suggestions.append(
                "Force refusal when no documents are retrieved."
            )

        elif retrieval_confidence < 0.55:

            findings.append("hallucination_due_to_weak_retrieval")

            evidence.append(
                f"hallucination={halluc_score}, cosine={retrieval_confidence}"
            )

            suggestions.append(
                "Improve retrieval relevance or apply reranking."
            )

        else:

            findings.append("generation_overreach")

            evidence.append(
                f"hallucination={halluc_score}, cosine={retrieval_confidence}"
            )

            suggestions.append(
                "Reduce temperature or enforce stricter grounding."
            )

    # ------------------------------------------------------------
    # 6 Over-Verbose Generation
    # ------------------------------------------------------------

    if concise_score is not None and concise_score < 0.4:

        findings.append("over_verbose_answer")

        evidence.append(
            f"conciseness={concise_score}, completion_tokens={completion_tokens}"
        )

        suggestions.append(
            "Add stricter brevity constraints in prompt."
        )

    # ------------------------------------------------------------
    # 7 Excessive Token Usage
    # ------------------------------------------------------------

    if completion_tokens > 300:

        findings.append("excessive_generation_length")

        evidence.append(
            f"completion_tokens={completion_tokens}"
        )

        suggestions.append(
            "Limit max_tokens or enforce concise output."
        )

    # ------------------------------------------------------------
    # 8 Intent Mismatch
    # ------------------------------------------------------------

    span_int = next(
        (s for s in spans if s.get("type") == "intent-classification"),
        None
    )

    if span_int:

        span_intent = span_int.get("metadata", {}).get("intent")

        if span_intent and raw.get("intent") != span_intent:

            findings.append("intent_mismatch")

            evidence.append(
                f"trace.intent={raw.get('intent')} vs span.intent={span_intent}"
            )

            suggestions.append(
                "Investigate classifier consistency."
            )

    # ------------------------------------------------------------
    # RCA completeness detection
    # ------------------------------------------------------------

    if skipped_evaluators and completed_evaluators:

        findings.append("rca_partial_analysis")

        evidence.append(
            f"skipped_evaluators={','.join(skipped_evaluators)}"
        )

        suggestions.append(
            "Some RCA checks were skipped because required evaluators did not run."
        )

    elif skipped_evaluators and not completed_evaluators:

        findings.append("rca_not_applicable")

        evidence.append(
            f"all_evaluators_skipped={','.join(skipped_evaluators)}"
        )

        suggestions.append(
            "RCA could not run because all evaluators were skipped."
        )

    # ------------------------------------------------------------
    # Remove duplicates
    # ------------------------------------------------------------

    findings = list(dict.fromkeys(findings))
    evidence = list(dict.fromkeys(evidence))
    suggestions = list(dict.fromkeys(suggestions))

    # ------------------------------------------------------------
    # Healthy case
    # ------------------------------------------------------------

    if not findings:

        findings.append("no_anomaly_detected")

        evidence.append(
            "All evaluator thresholds satisfied"
        )

        suggestions.append(
            "No action required"
        )

    return findings, evidence, suggestions