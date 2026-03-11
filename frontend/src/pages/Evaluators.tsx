import React, { useEffect, useState, useMemo } from "react";
import { Plus } from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";

import {
  api,
  type Evaluator,
  type Template,
  type EvaluationLog,
  type Trace,
} from "../api/client";

import EvaluatorsTable from "../components/EvaluatorsTable";
import TemplatesList from "../components/TemplatesList";
import LogsTable from "../components/LogsTable";
import TraceModal from "../components/TraceModal";

const ALL_EVALUATORS = "All Evaluators";
const ALL_STATUS = "All Status";

const EvaluatorsPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // ✅ FIXED: proper naming
  const [evaluators, setEvaluators] = useState<Evaluator[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [logs, setLogs] = useState<EvaluationLog[]>([]);
  const [loading, setLoading] = useState(true);

  const [activeTab, setActiveTab] =
    useState<"evaluators" | "templates" | "logs">(
      (location.state as any)?.tab ?? "evaluators"
    );

  const [selectedTrace, setSelectedTrace] = useState<Trace | null>(null);
  const [loadingTrace, setLoadingTrace] = useState(false);


  const [filterEvaluator, setFilterEvaluator] = useState(ALL_EVALUATORS);
  const [filterStatus, setFilterStatus] = useState(ALL_STATUS);
  const [showEvaluatorDropdown, setShowEvaluatorDropdown] = useState(false);
  const [showStatusDropdown, setShowStatusDropdown] = useState(false);

  useEffect(() => {
    const tab = (location.state as any)?.tab;
    if (tab) setActiveTab(tab);
  }, [location.state]);

  /** Filter logs with robust matching */
  const filteredLogs = useMemo(() => {
    console.log("Filtering logs...", { filterEvaluator, filterStatus, logsCount: logs.length });
    return logs.filter((log) => {
      // 1. Evaluator Filter
      const logEval = (log.evaluator_name || "-").toLowerCase().trim();
      const targetEval = filterEvaluator.toLowerCase().trim();
      const isAllEvaluators = targetEval === ALL_EVALUATORS.toLowerCase().trim();
      const evalMatch = isAllEvaluators || logEval === targetEval;

      // 2. Status Filter
      const logStatus = (log.status || "unknown").toLowerCase().trim();
      const targetStatus = filterStatus.toLowerCase().trim();
      const isAllStatus = targetStatus === ALL_STATUS.toLowerCase().trim();
      const statusMatch = isAllStatus || logStatus === targetStatus;

      const isMatch = evalMatch && statusMatch;

      if (!isAllEvaluators || !isAllStatus) {
        console.log(`[FILTER DEBUG] Trace: ${log.trace_id}`, {
          eval: { log: logEval, target: targetEval, isAll: isAllEvaluators, match: evalMatch },
          status: { log: logStatus, target: targetStatus, isAll: isAllStatus, match: statusMatch },
          isMatch
        });
      }

      return isMatch;
    });
  }, [logs, filterEvaluator, filterStatus, ALL_EVALUATORS, ALL_STATUS]);

  /** Fetch all data */
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);

    // ---- Evaluators
    try {
      const res = await api.get("/evaluators");
      const data = res.data;

      if (Array.isArray(data)) {
        setEvaluators(data);
      } else if (Array.isArray(data?.evaluators)) {
        setEvaluators(data.evaluators);
      } else {
        setEvaluators([]);
      }
    } catch {
      setEvaluators([]);
    }

    // ---- Templates
    try {
      const res = await api.get("/templates");
      const data = res.data;

      if (Array.isArray(data)) {
        setTemplates(data);
      } else if (Array.isArray(data?.templates)) {
        setTemplates(data.templates);
      } else {
        setTemplates([]);
      }
    } catch {
      setTemplates([]);
    }

    // ---- Evaluation Logs
    try {
      const res = await api.get("/evaluations");
      setLogs(Array.isArray(res.data) ? res.data : []);
    } catch {
      setLogs([]);
    }

    setLoading(false);
  };

  /** View trace modal */
  const handleViewTrace = async (traceId: string) => {
    if (!traceId) return;
    setLoadingTrace(true);

    try {
      const res = await api.get(`/traces/${traceId}`);
      setSelectedTrace(res.data);
    } finally {
      setLoadingTrace(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-[#13bba4]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-currentColor" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[#0e1117] text-white p-8">

      {/* HEADER */}
      <div className="flex justify-between items-start mb-10">
        <div>
          <h1 className="text-4xl font-bold tracking-tight mb-2">Evaluators</h1>
          <p className="text-gray-400 text-sm">Automated evaluation system</p>
        </div>

        <button
          onClick={() => navigate("/evaluators/new")}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#13bba4] text-black font-black rounded-lg"
        >
          <Plus size={18} strokeWidth={3} />
          New Evaluator
        </button>
      </div>

      {/* TABS */}
      <div className="flex gap-1 p-1 bg-gray-900/50 rounded-xl w-fit border border-gray-800 mb-10">
        {(["evaluators", "templates", "logs"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-6 py-2 rounded-lg text-xs font-bold capitalize ${activeTab === tab ? "bg-[#1c212e] text-white" : "text-gray-500"
              }`}
          >
            {tab === "logs" ? "Evaluation Log" : tab}
          </button>
        ))}
      </div>

      {/* TAB CONTENT */}

      {activeTab === "evaluators" && (
        <EvaluatorsTable evaluators={evaluators} />
      )}

      {activeTab === "templates" && (
        <TemplatesList
          templates={templates}
          onNewTemplate={() => navigate("/templates/new")}
        />
      )}

      {activeTab === "logs" && (
        <LogsTable
          logs={logs}
          filteredLogs={filteredLogs}
          filterEvaluator={filterEvaluator}
          setFilterEvaluator={setFilterEvaluator}
          filterStatus={filterStatus}
          setFilterStatus={setFilterStatus}
          showEvaluatorDropdown={showEvaluatorDropdown}
          setShowEvaluatorDropdown={setShowEvaluatorDropdown}
          showStatusDropdown={showStatusDropdown}
          setShowStatusDropdown={setShowStatusDropdown}
          handleViewTrace={handleViewTrace}
        />
      )}

      {(selectedTrace || loadingTrace) && (
        <TraceModal
          selectedTrace={selectedTrace}
          loadingTrace={loadingTrace}
          onClose={() => setSelectedTrace(null)}
        />
      )}
    </div>
  );
};

export default EvaluatorsPage;
