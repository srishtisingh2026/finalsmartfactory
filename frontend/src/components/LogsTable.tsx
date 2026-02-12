import React from "react";
import LogsFilters from "./LogsFilters";
import { ExternalLink } from "lucide-react";

import { type EvaluationLog } from "../api/client";

interface LogsTableProps {
  logs: EvaluationLog[];
  filteredLogs: EvaluationLog[];
  filterEvaluator: string;
  setFilterEvaluator: (val: string) => void;
  filterStatus: string;
  setFilterStatus: (val: string) => void;
  showEvaluatorDropdown: boolean;
  setShowEvaluatorDropdown: (val: boolean) => void;
  showStatusDropdown: boolean;
  setShowStatusDropdown: (val: boolean) => void;
  handleViewTrace: (traceId: string) => void;
}

const LogsTable: React.FC<LogsTableProps> = ({
  logs,
  filteredLogs,
  filterEvaluator,
  setFilterEvaluator,
  filterStatus,
  setFilterStatus,
  showEvaluatorDropdown,
  setShowEvaluatorDropdown,
  showStatusDropdown,
  setShowStatusDropdown,
  handleViewTrace
}) => {
  return (
    <div className="bg-[#161a23] border border-gray-800 rounded-2xl">
      <div className="p-6 border-b border-gray-800 bg-[#1c212e]/40 flex justify-between items-center">
        <h3 className="text-lg font-bold">Evaluation Execution Log</h3>

        <LogsFilters
          logs={logs}
          filterEvaluator={filterEvaluator}
          setFilterEvaluator={setFilterEvaluator}
          filterStatus={filterStatus}
          setFilterStatus={setFilterStatus}
          showEvaluatorDropdown={showEvaluatorDropdown}
          setShowEvaluatorDropdown={setShowEvaluatorDropdown}
          showStatusDropdown={showStatusDropdown}
          setShowStatusDropdown={setShowStatusDropdown}
        />
      </div>

      {/* 🔥 Scroll Wrapper for Responsive Table */}
      <div className="overflow-x-auto scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
        <table className="w-full text-left min-w-[900px]">
          <thead className="bg-[#161a23]">
            <tr className="border-b border-gray-800/80">
              {[
                "Timestamp",
                "Evaluator",
                "Trace ID",
                "Score",
                "Duration",
                "Status",
                "Actions"
              ].map((h) => (
                <th
                  key={h}
                  className="px-8 py-5 text-[10px] font-black text-gray-500 uppercase tracking-[0.2em]"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {filteredLogs.map((log, i) => {
              const statusStr = (log.status || "unknown").toLowerCase();

              return (
                <tr
                  key={i}
                  className="border-b border-gray-800/40 hover:bg-[#1c212e]/40"
                >
                  <td className="px-8 py-6 text-xs text-gray-400">
                    {log.timestamp
                      ? new Date(log.timestamp).toLocaleString()
                      : "N/A"}
                  </td>

                  <td className="px-8 py-6 text-sm font-bold text-gray-200">
                    {log.evaluator_name}
                  </td>

                  <td className="px-8 py-6">
                    <span className="px-3 py-1 bg-black border border-gray-800 text-gray-300 text-xs font-mono rounded-lg whitespace-nowrap">
                      {log.trace_id || "N/A"}
                    </span>
                  </td>

                  <td className="px-8 py-6 text-sm text-gray-300 font-bold">
                    {typeof log.score === "number"
                      ? log.score.toFixed(2)
                      : "-"}
                  </td>

                  <td className="px-8 py-6 text-xs text-gray-400 font-bold">
                    {typeof log.duration_ms === "number"
                      ? `${log.duration_ms}ms`
                      : "—"}
                  </td>

                  <td className="px-8 py-6">
                    <span
                      className={`px-3 py-1 rounded-full text-[10px] font-black uppercase border ${statusStr === "completed"
                          ? "bg-green-500/10 text-green-500 border-green-500/20"
                          : statusStr === "timeout"
                            ? "bg-orange-500/10 text-orange-400 border-orange-500/20"
                            : "bg-red-500/10 text-red-500 border-red-500/20"
                        }`}
                    >
                      {log.status || "Unknown"}
                    </span>
                  </td>

                  <td className="px-8 py-6">
                    <button
                      onClick={() => handleViewTrace(log.trace_id)}
                      className="flex items-center gap-2 px-4 py-2.5 bg-[#13bba4] text-black font-black rounded-lg"
                    >
                      <ExternalLink size={14} />
                      View Trace
                    </button>
                  </td>
                </tr>
              );
            })}

            {filteredLogs.length === 0 && (
              <tr>
                <td
                  colSpan={7}
                  className="p-16 text-center text-gray-500 text-sm opacity-40 italic"
                >
                  No historical evaluations found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default LogsTable;
