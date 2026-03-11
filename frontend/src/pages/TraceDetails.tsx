import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
    ArrowLeft,
    Clock,
    Database,
    ChevronDown,
    ChevronRight,
    AlertTriangle,
    CheckCircle,
} from "lucide-react";

import { api, type Trace, type RCAResult } from "../api/client";

interface SpanNode {
    span_id: string;
    parent_span_id: string | null;
    type: string;
    name: string;
    latency_ms: number;
    usage?: {
        total_tokens?: number;
    };
    start_time: number;
    children: SpanNode[];
    model?: string;
}

function buildSpanTree(spans: any[]): SpanNode[] {
    const spanMap: Record<string, SpanNode> = {};
    const roots: SpanNode[] = [];

    // First pass: create all nodes
    spans.forEach((span) => {
        spanMap[span.span_id] = {
            ...span,
            children: [],
        };
    });

    // Second pass: link parents and children
    spans.forEach((span) => {
        if (span.parent_span_id && spanMap[span.parent_span_id]) {
            spanMap[span.parent_span_id].children.push(spanMap[span.span_id]);
        } else {
            roots.push(spanMap[span.span_id]);
        }
    });

    // Sort children by start_time
    Object.values(spanMap).forEach((node) => {
        node.children.sort((a, b) => a.start_time - b.start_time);
    });

    return roots.sort((a, b) => a.start_time - b.start_time);
}

const getBadgeColor = (type: string) => {
    switch (type.toLowerCase()) {
        case "span":
            return "bg-gray-800 text-gray-300 border-gray-700";
        case "llm":
        case "generation":
            return "bg-[#3a1d16] text-[#ffb29b] border-[#5a2d20]";
        case "retrieval":
            return "bg-[#0d2a1f] text-[#6ee7b7] border-[#1a4d3a]";
        case "embedding":
            return "bg-[#1a2332] text-[#60a5fa] border-[#2a3a52]";
        default:
            return "bg-gray-800 text-gray-400 border-gray-700";
    }
};

interface SpanTreeItemProps {
    node: SpanNode;
    depth: number;
    expandedSpans: Record<string, boolean>;
    showDetails: Record<string, boolean>;
    toggleExpansion: (e: React.MouseEvent, id: string) => void;
    toggleDetails: (id: string) => void;
    traceLatency: number;
    isLastChild: boolean;
}

const SpanTreeItem = ({
    node,
    depth,
    expandedSpans,
    showDetails,
    toggleExpansion,
    toggleDetails,
    traceLatency,
    isLastChild
}: SpanTreeItemProps) => {
    const isExpanded = expandedSpans[node.span_id];
    const isDetailsVisible = showDetails[node.span_id];
    const hasChildren = node.children.length > 0;

    return (
        <div className="relative">
            {/* Vertical lines connecting to parent */}
            {depth > 0 && (
                <>
                    {/* Line coming from above */}
                    <div
                        className="absolute border-l border-gray-700"
                        style={{
                            left: `-${0.75}rem`,
                            top: 0,
                            height: isLastChild ? '1.5rem' : '100%'
                        }}
                    />
                    {/* Horizontal connector to the node */}
                    <div
                        className="absolute border-t border-gray-700"
                        style={{
                            left: `-${0.75}rem`,
                            top: '1.5rem',
                            width: '0.75rem'
                        }}
                    />
                </>
            )}

            <div
                className={`group flex items-center gap-4 py-2 px-3 hover:bg-[#1a1f2b] transition-colors cursor-pointer border border-[#1e2330] rounded-lg mb-2 mx-2 bg-[#11141d] shadow-sm`}
                onClick={() => toggleDetails(node.span_id)}
            >
                {/* Tree indentation and toggle */}
                <div className="flex items-center gap-2 min-w-[320px]" style={{ paddingLeft: `${depth * 1.5}rem` }}>
                    <div
                        className="w-6 h-6 flex items-center justify-center hover:bg-gray-800 rounded cursor-pointer"
                        onClick={(e) => toggleExpansion(e, node.span_id)}
                    >
                        {hasChildren && (
                            isExpanded ? <ChevronDown size={14} className="text-gray-400" /> : <ChevronRight size={14} className="text-gray-400" />
                        )}
                    </div>

                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border uppercase tracking-wider ${getBadgeColor(node.type)}`}>
                        {node.type}
                    </span>

                    <div className="flex flex-col ml-1">
                        <span className="text-sm font-medium text-gray-200 group-hover:text-blue-400 transition-colors">
                            {node.name}
                        </span>
                        {node.model && (
                            <span className="text-[10px] text-gray-500">
                                Model: <span className="text-gray-400">{node.model}</span>
                            </span>
                        )}
                    </div>
                </div>

                {/* Spacer */}
                <div className="flex-1" />

                {/* Stats */}
                <div className="flex items-center gap-5 text-xs tabular-nums text-gray-400 w-64 justify-end">
                    <span className="flex items-center gap-1.5 whitespace-nowrap">
                        <Clock size={12} className="text-gray-600" />
                        {node.latency_ms}ms
                    </span>

                    {node.usage?.total_tokens && (
                        <span className="flex items-center gap-1.5 whitespace-nowrap">
                            <Database size={12} className="text-gray-600" />
                            {node.usage.total_tokens}
                        </span>
                    )}

                    {node.type.toLowerCase() === 'llm' && (
                        <span className="text-emerald-500/80 font-medium">
                            ${(node as any).cost_usd?.toFixed(6) ?? '0.000000'}
                        </span>
                    )}
                </div>
            </div>

            {/* DETAILS JSON */}
            {isDetailsVisible && (
                <div className="mx-4 mb-3 p-4 bg-[#0d1015] border border-[#1e2330] rounded-lg shadow-inner overflow-hidden">
                    <pre className="text-[11px] font-mono text-gray-400 overflow-x-auto">
                        {JSON.stringify(node, null, 2)}
                    </pre>
                </div>
            )}

            {/* Recursive Children */}
            {isExpanded && hasChildren && (
                <div className="mt-1">
                    {node.children.map((child, index) => (
                        <SpanTreeItem
                            key={child.span_id}
                            node={child}
                            depth={depth + 1}
                            expandedSpans={expandedSpans}
                            showDetails={showDetails}
                            toggleExpansion={toggleExpansion}
                            toggleDetails={toggleDetails}
                            traceLatency={traceLatency}
                            isLastChild={index === node.children.length - 1}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};


export default function TraceDetails() {
    const { traceId } = useParams<{ traceId: string }>();
    const navigate = useNavigate();

    const [trace, setTrace] = useState<Trace | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [activeTab, setActiveTab] =
        useState<"input" | "output" | "metadata">("input");

    const [rca, setRca] = useState<RCAResult | null>(null);

    const [expandedSpans, setExpandedSpans] =
        useState<Record<string, boolean>>({});
    const [showDetails, setShowDetails] =
        useState<Record<string, boolean>>({});

    useEffect(() => {
        if (!traceId) return;

        setLoading(true);

        api
            .get(`/traces/${traceId}`)
            .then((res) => {
                setTrace(res.data);

                // Expand all spans by default
                if (res.data.spans) {
                    const initialExpanded: Record<string, boolean> = {};
                    res.data.spans.forEach((s: any) => {
                        initialExpanded[s.span_id] = true;
                    });
                    setExpandedSpans(initialExpanded);
                }
            })
            .catch((err) => setError(err.message || "Failed to load trace"))
            .finally(() => setLoading(false));

        api
            .get(`/rca/${traceId}`)
            .then((res) => setRca(res.data))
            .catch(() => setRca(null));
    }, [traceId]);

    const toggleExpansion = (e: React.MouseEvent, spanId: string) => {
        e.stopPropagation();
        setExpandedSpans((prev) => ({
            ...prev,
            [spanId]: !prev[spanId],
        }));
    };

    const toggleDetails = (spanId: string) => {
        setShowDetails((prev) => ({
            ...prev,
            [spanId]: !prev[spanId],
        }));
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

    const provider = trace.provider_raw || {};
    const scores = trace.scores || {};

    const spans = (trace.spans || []).sort(
        (a: any, b: any) => a.start_time - b.start_time
    );
    const traceLatency = trace.latency_ms || 1;

    const totalTokens =
        trace.total_tokens ??
        trace.tokens ??
        provider.total_tokens ??
        0;

    const promptTokens =
        trace.prompt_tokens ??
        trace.tokens_in ??
        provider.prompt_tokens ??
        0;

    const completionTokens =
        trace.completion_tokens ??
        trace.tokens_out ??
        provider.completion_tokens ??
        0;

    return (
        <div className="space-y-6 text-white pb-12">

            {/* HEADER */}

            <div className="flex items-center gap-4 border-b border-[#1e2330] pb-4">
                <button
                    onClick={() => navigate("/traces")}
                    className="p-2 hover:bg-[#1a1f2b] rounded-full"
                >
                    <ArrowLeft size={20} className="text-gray-400" />
                </button>

                <div>
                    <h1 className="text-2xl font-bold">Trace Detail</h1>
                    <p className="text-sm font-mono text-gray-500">{trace.trace_id}</p>
                </div>
            </div>

            {/* METRIC CARDS */}

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">

                <div className="bg-[#151921] border border-gray-800 rounded-xl p-5">
                    <p className="text-xs text-gray-500 mb-2">Name</p>

                    <span className="px-3 py-1 bg-[#1a2332] border border-gray-700 rounded-full text-sm text-gray-300">
                        {trace.trace_name}
                    </span>
                </div>

                <div className="bg-[#151921] border border-gray-800 rounded-xl p-5">
                    <p className="text-xs text-gray-500 mb-1">Latency</p>
                    <p className="text-xl font-bold">{trace.latency_ms}ms</p>
                </div>

                <div className="bg-[#151921] border border-gray-800 rounded-xl p-5">
                    <p className="text-xs text-gray-500 mb-1">Tokens</p>

                    <p className="text-xl font-bold">
                        {Number(totalTokens).toLocaleString()}
                    </p>

                    <p className="text-[10px] text-gray-500 mt-1">
                        {promptTokens} in / {completionTokens} out
                    </p>
                </div>

                <div className="bg-[#151921] border border-gray-800 rounded-xl p-5">
                    <p className="text-xs text-gray-500 mb-1">Cost</p>

                    <p className="text-xl font-bold">
                        ${Number(trace.total_cost_usd ?? trace.cost ?? 0).toFixed(6)}
                    </p>
                </div>

            </div>

            {/* EVALUATION */}

            <div className="bg-[#151921] border border-gray-800 rounded-xl p-6">

                <h3 className="font-bold mb-4">Evaluation Scores</h3>

                {Object.keys(scores).length > 0 ? (

                    <div className="flex gap-2 flex-wrap">

                        {Object.entries(scores).map(([k, v]) => (

                            <span
                                key={k}
                                className={`px-3 py-1.5 rounded-full text-xs border
                ${Number(v) < 0.3
                                        ? "bg-[#3a1d16] text-[#ffb29b]"
                                        : Number(v) < 0.6
                                            ? "bg-[#2f1e0a] text-[#fcd34d]"
                                            : "bg-[#0d2a1f] text-[#6ee7b7]"
                                    }`}
                            >
                                {k} {Number(v).toFixed(3)}
                            </span>

                        ))}

                    </div>

                ) : (

                    <p className="text-sm text-gray-500 italic">
                        No evaluation scores linked to this trace.
                    </p>

                )}
            </div>

            {/* RCA */}

            <div className="bg-[#151921] border border-gray-800 rounded-xl p-6">

                <h3 className="font-bold mb-4 flex items-center gap-2">

                    {rca && rca.findings.includes("no_anomaly_detected")
                        ? <CheckCircle size={18} className="text-green-400" />
                        : <AlertTriangle size={18} className="text-amber-500" />}

                    Root Cause Analysis

                </h3>

                {!rca ? (

                    <p className="text-sm text-gray-500 italic">
                        No RCA found for this trace.
                    </p>

                ) : (

                    <>
                        <div className="mb-4">
                            <p className="text-xs text-gray-500 mb-2">Findings</p>

                            <div className="flex gap-2 flex-wrap">
                                {rca.findings.map((f) => (
                                    <span
                                        key={f}
                                        className={`px-3 py-1 rounded-full text-xs ${f === "no_anomaly_detected"
                                                ? "bg-[#0d2a1f] text-[#6ee7b7]"
                                                : "bg-[#3a1d16] text-[#ffb29b]"
                                            }`}
                                    >
                                        {f.replace(/_/g, " ")}
                                    </span>
                                ))}
                            </div>
                        </div>

                        <div className="mb-4">
                            <p className="text-xs text-gray-500 mb-2">Evidence</p>

                            <div className="bg-[#0d1015] p-3 rounded-lg text-xs font-mono">
                                {rca.evidence.map((e, i) => (
                                    <div key={i}>{e}</div>
                                ))}
                            </div>
                        </div>

                        <div>
                            <p className="text-xs text-gray-500 mb-2">Suggestions</p>

                            <ul className="list-disc list-inside text-sm text-gray-300">
                                {rca.suggestions.map((s, i) => (
                                    <li key={i}>{s}</li>
                                ))}
                            </ul>
                        </div>
                    </>
                )}
            </div>

            {/* SPANS */}
            {/* SPANS */}

            <div className="bg-[#151921] border border-gray-800 rounded-xl overflow-hidden shadow-2xl pb-4">
                <div className="p-4 border-b border-gray-800 bg-[#1a1f2b]/50 mb-4">
                    <h3 className="font-bold text-gray-200">Span Waterfall</h3>
                </div>

                <div className="px-2">
                    {buildSpanTree(spans).map((rootNode, index, array) => (
                        <SpanTreeItem
                            key={rootNode.span_id}
                            node={rootNode}
                            depth={0}
                            expandedSpans={expandedSpans}
                            showDetails={showDetails}
                            toggleExpansion={toggleExpansion}
                            toggleDetails={toggleDetails}
                            traceLatency={traceLatency}
                            isLastChild={index === array.length - 1}
                        />
                    ))}
                </div>
            </div>



            {/* INPUT / OUTPUT TABS */}

            <div>

                <div className="flex gap-1 mb-2">

                    {["input", "output", "metadata"].map((t) => (

                        <button
                            key={t}
                            onClick={() => setActiveTab(t as any)}
                            className={`px-4 py-2 text-xs ${activeTab === t
                                ? "bg-[#161a23] text-white"
                                : "bg-[#0e1117] text-gray-500"
                                }`}
                        >
                            {t}
                        </button>

                    ))}

                </div>

                <div className="bg-[#161a23] border border-[#1e2330] p-4 text-sm font-mono">

                    {activeTab === "input" && (
                        <pre>{JSON.stringify(trace.input, null, 2)}</pre>
                    )}

                    {activeTab === "output" && (
                        <pre>{JSON.stringify(trace.output, null, 2)}</pre>
                    )}

                    {activeTab === "metadata" && (
                        <pre>
                            {JSON.stringify(
                                {
                                    session: trace.session_id,
                                    user: trace.user_id,
                                    model: trace.model,
                                    provider: trace.provider,
                                    environment: trace.environment,
                                },
                                null,
                                2
                            )}
                        </pre>
                    )}

                </div>

            </div>

        </div>
    );
}