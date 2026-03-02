import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Clock, Database, DollarSign, ChevronDown, ChevronRight, AlertTriangle, CheckCircle } from "lucide-react";
import { api, type Trace, type RCAResult } from "../api/client";

export default function TraceDetails() {
    const { traceId } = useParams<{ traceId: string }>();
    const navigate = useNavigate();

    const [trace, setTrace] = useState<Trace | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [activeTab, setActiveTab] = useState<"input" | "output" | "metadata">("input");
    const [rca, setRca] = useState<RCAResult | null>(null);

    // Keep track of which waterfall spans are vertically expanded
    const [expandedSpans, setExpandedSpans] = useState<Record<string, boolean>>({});

    useEffect(() => {
        if (!traceId) return;
        setLoading(true);

        // Fetch trace data
        api.get(`/traces/${traceId}`)
            .then((res) => setTrace(res.data))
            .catch((err) => setError(err.message || "Failed to load trace"))
            .finally(() => setLoading(false));

        // Fetch RCA (may not exist - 404 is expected for traces without RCA)
        api.get(`/rca/${traceId}`)
            .then((res) => setRca(res.data))
            .catch(() => setRca(null));
    }, [traceId]);

    const toggleSpan = (spanId: string) => {
        setExpandedSpans(prev => ({ ...prev, [spanId]: !prev[spanId] }));
    };

    if (loading) {
        return <div className="p-8 text-gray-400">Loading trace details...</div>;
    }

    if (error || !trace) {
        return (
            <div className="p-8 text-red-400">
                <h2 className="text-xl font-bold mb-2">Error Loading Trace</h2>
                <p>{error}</p>
                <button
                    onClick={() => navigate("/traces")}
                    className="mt-4 px-4 py-2 bg-gray-800 rounded-lg text-white hover:bg-gray-700"
                >
                    Back to Traces
                </button>
            </div>
        );
    }

    const scores = trace.scores || {};
    const spans = trace.spans || [];

    return (
        <div className="space-y-6 text-white pb-12">

            {/* 1. Header Area */}
            <div className="flex items-center gap-4 border-b border-[#1e2330] pb-4">
                <button
                    onClick={() => navigate("/traces")}
                    className="p-2 hover:bg-[#1a1f2b] rounded-full transition-colors"
                >
                    <ArrowLeft size={20} className="text-gray-400 hover:text-white" />
                </button>
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">Trace Detail</h1>
                    <p className="text-sm font-mono text-gray-500">{trace.trace_id}</p>
                </div>
            </div>

            {/* 2. Top-Level Metric Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {/* Card: Name */}
                <div className="bg-[#151921] border border-gray-800 rounded-xl p-5 flex flex-col justify-center">
                    <p className="text-xs text-gray-500 mb-2">Name</p>
                    <div>
                        <span className="px-3 py-1 bg-[#1a2332] border border-gray-700 rounded-full text-sm font-medium text-gray-300">
                            {trace.trace_name}
                        </span>
                    </div>
                </div>

                {/* Card: Latency */}
                <div className="bg-[#151921] border border-gray-800 rounded-xl p-5 flex flex-col justify-center">
                    <p className="text-xs text-gray-500 mb-1">Latency</p>
                    <p className="text-xl font-bold">{trace.latency_ms}ms</p>
                </div>

                {/* Card: Tokens */}
                <div className="bg-[#151921] border border-gray-800 rounded-xl p-5 flex flex-col justify-center">
                    <p className="text-xs text-gray-500 mb-1">Tokens</p>
                    <p className="text-xl font-bold">{(trace.total_tokens ?? trace.tokens ?? 0).toLocaleString()}</p>
                    <p className="text-[10px] text-gray-500 mt-1">
                        {trace.prompt_tokens ?? trace.tokens_in ?? 0} in / {trace.completion_tokens ?? trace.tokens_out ?? 0} out
                    </p>
                </div>

                {/* Card: Cost */}
                <div className="bg-[#151921] border border-gray-800 rounded-xl p-5 flex flex-col justify-center">
                    <p className="text-xs text-gray-500 mb-1">Cost</p>
                    <p className="text-xl font-bold">${Number(trace.total_cost_usd ?? trace.cost ?? 0).toFixed(6)}</p>
                </div>
            </div>

            {/* 3. Evaluation Scores Container */}
            <div className="bg-[#151921] border border-gray-800 rounded-xl p-6">
                <h3 className="font-bold mb-4 text-base">Evaluation Scores</h3>
                {Object.keys(scores).length > 0 ? (
                    <div className="flex gap-2 flex-wrap">
                        {Object.entries(scores).map(([k, v]) => (
                            <span
                                key={k}
                                className={`px-3 py-1.5 rounded-full text-xs font-semibold border ${v < 0.3
                                    ? "bg-[#3a1d16] border-[#ffb29b]/20 text-[#ffb29b]"
                                    : v < 0.6
                                        ? "bg-[#2f1e0a] border-[#fcd34d]/20 text-[#fcd34d]"
                                        : "bg-[#0d2a1f] border-[#6ee7b7]/20 text-[#6ee7b7]"
                                    }`}
                            >
                                {k} {Number(v).toFixed(3)}
                            </span>
                        ))}
                    </div>
                ) : (
                    <p className="text-sm text-gray-500 italic">No evaluation scores linked to this trace.</p>
                )}
            </div>

            {/* 4. Root Cause Analysis (Conditional) */}
            <div className="bg-[#151921] border border-gray-800 rounded-xl p-6">
                <h3 className="font-bold mb-4 text-base flex items-center gap-2">
                    {rca
                        ? rca.findings.includes("no_anomaly_detected")
                            ? <CheckCircle size={18} className="text-[#6ee7b7]" />
                            : <AlertTriangle size={18} className="text-amber-500" />
                        : <AlertTriangle size={18} className="text-amber-500" />
                    }
                    Root Cause Analysis
                </h3>

                {!rca ? (
                    <div className="text-sm text-gray-500 italic">
                        No RCA found for this trace.
                    </div>
                ) : (
                    <>
                        {/* Findings */}
                        <div className="mb-4">
                            <p className="text-xs text-gray-500 mb-2">Findings</p>
                            <div className="flex flex-wrap gap-2">
                                {rca.findings.map((finding) => (
                                    <span
                                        key={finding}
                                        className={`px-3 py-1.5 rounded-full text-xs font-semibold border ${finding === "no_anomaly_detected"
                                            ? "bg-[#0d2a1f] border-[#6ee7b7]/20 text-[#6ee7b7]"
                                            : "bg-[#3a1d16] border-[#ffb29b]/20 text-[#ffb29b]"
                                            }`}
                                    >
                                        {finding.replace(/_/g, " ")}
                                    </span>
                                ))}
                            </div>
                        </div>

                        {/* Evidence */}
                        <div className="mb-4">
                            <p className="text-xs text-gray-500 mb-2">Evidence</p>
                            <div className="bg-[#0d1015] p-3 rounded-lg border border-gray-800 font-mono text-xs text-gray-400">
                                {rca.evidence.map((e, i) => (
                                    <div key={i}>{e}</div>
                                ))}
                            </div>
                        </div>

                        {/* Suggestions */}
                        <div>
                            <p className="text-xs text-gray-500 mb-2">Suggestions</p>
                            <ul className="list-disc list-inside text-sm text-gray-300 space-y-1">
                                {rca.suggestions.map((s, i) => (
                                    <li key={i}>{s}</li>
                                ))}
                            </ul>
                        </div>
                    </>
                )}
            </div>

            {/* 5. Span Waterfall */}
            <div className="bg-[#151921] border border-gray-800 rounded-xl overflow-hidden">
                <div className="p-4 border-b border-gray-800">
                    <h3 className="font-bold text-base">Span Waterfall</h3>
                </div>

                <div className="p-4 bg-[#11141d]">
                    {spans.length > 0 ? (
                        <div className="flex flex-col">
                            {spans.map((span: any) => {
                                const isExpanded = expandedSpans[span.span_id];

                                // Render specific pill color based on type
                                let pillClass = "bg-gray-800 text-gray-300 border-gray-700";
                                if (span.type === "intent-classification" || span.type === "vector-search") pillClass = "bg-blue-900/40 text-blue-400 border-blue-900/60";
                                else if (span.type === "retrieval" || span.type === "embedding" || span.type === "PromptTemplate") pillClass = "bg-teal-900/40 text-teal-400 border-teal-900/60";
                                else if (span.type === "llm" || span.type === "generation" || span.type === "generate-response" || span.type === "gemini_chat_completion") pillClass = "bg-orange-900/40 text-orange-400 border-orange-900/60";
                                else if (span.type === "chain") pillClass = "bg-pink-900/40 text-pink-400 border-pink-900/60";

                                return (
                                    <div key={span.span_id} className="group border-l-[1px] border-b-[1px] border-[#1e2330] last:border-b-0 relative ml-2 pl-4 py-2 hover:bg-[#151921] transition-colors rounded-tr-lg rounded-br-lg my-1">

                                        {/* A tiny line connecting from parent to this distinct level could be drawn here, visually represented by the left border */}
                                        <div
                                            className="flex flex-col md:flex-row justify-between items-start md:items-center cursor-pointer p-2"
                                            onClick={() => toggleSpan(span.span_id)}
                                        >
                                            {/* Left side: Pill + Name */}
                                            <div className="flex items-center gap-3">
                                                {isExpanded ? <ChevronDown size={14} className="text-gray-500" /> : <ChevronRight size={14} className="text-gray-500" />}
                                                <span className={`text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${pillClass}`}>
                                                    {span.type}
                                                </span>
                                                <div>
                                                    <span className="text-sm font-medium text-gray-300 font-mono">
                                                        {span.name}
                                                    </span>
                                                    {(span.type === 'llm' || span.type === 'gemini_chat_completion') && trace.model && (
                                                        <p className="text-[10px] text-gray-500 mt-1">Model: {trace.model}</p>
                                                    )}
                                                </div>
                                            </div>

                                            {/* Right side: Minor stats */}
                                            <div className="flex items-center gap-4 mt-2 md:mt-0 text-[11px] text-gray-500 font-mono">
                                                <span className="flex items-center gap-1"><Clock size={11} className="text-gray-600" /> {span.latency_ms}ms</span>

                                                {span.total_tokens ? (
                                                    <span className="flex items-center gap-1"><Database size={11} className="text-gray-600" /> {span.total_tokens}</span>
                                                ) : null}

                                                {/* If llm, attempt to estimate cost visually (stubbed with trace total for demo) */}
                                                {span.type === "llm" && (
                                                    <span className="flex items-center gap-1 border-l border-gray-800 pl-4"><DollarSign size={11} className="text-gray-600" /> ${Number(trace.total_cost_usd ?? trace.cost ?? 0).toFixed(6)}</span>
                                                )}
                                            </div>
                                        </div>

                                        {/* Expanded JSON Inspector per span */}
                                        {isExpanded && (
                                            <div className="ml-8 mt-2 mb-4 bg-[#0d1015] p-3 rounded-lg border border-gray-800 text-xs overflow-x-auto text-gray-400 font-mono">
                                                <pre>{JSON.stringify(span, null, 2)}</pre>
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <p className="text-sm text-gray-500 italic p-2 text-center">No nested spans recorded for this trace.</p>
                    )}
                </div>
            </div>

            {/* 5. Tabbed Data Explorer */}
            <div className="pt-4">
                <div className="flex gap-1 mb-2">
                    {[
                        { id: "input", label: "Input" },
                        { id: "output", label: "Output" },
                        { id: "metadata", label: "Metadata" },
                    ].map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id as any)}
                            className={`px-4 py-2 rounded-t-lg text-xs font-semibold transition-colors ${activeTab === tab.id
                                ? "bg-[#161a23] text-white border-t border-l border-r border-[#1e2330]"
                                : "bg-[#0e1117] text-gray-500 hover:text-gray-300"
                                }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* Tab Content Window */}
                <div className="bg-[#161a23] border border-[#1e2330] rounded-b-lg rounded-tr-lg p-4 font-mono text-sm overflow-x-auto min-h-[120px]">
                    {activeTab === "input" && (
                        <pre className="text-gray-300 whitespace-pre-wrap">{trace.input || "{}"}</pre>
                    )}
                    {activeTab === "output" && (
                        <pre className="text-gray-300 whitespace-pre-wrap">{trace.output || "No output generated"}</pre>
                    )}
                    {activeTab === "metadata" && (
                        <pre className="text-gray-300 whitespace-pre-wrap">
                            {JSON.stringify({
                                session: trace.session_id,
                                user: trace.user_id,
                                model: trace.model,
                                provider: trace.provider,
                                environment: trace.environment,
                            }, null, 2)}
                        </pre>
                    )}
                </div>
            </div>
        </div>
    );
}
