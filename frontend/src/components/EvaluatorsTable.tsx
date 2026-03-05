import React, { useState } from "react";
import {
  type Evaluator,
  updateEvaluatorStatus,
  updateSamplingRate
} from "../api/client";

interface EvaluatorsTableProps {
  evaluators: Evaluator[];
}

const EvaluatorsTable: React.FC<EvaluatorsTableProps> = ({ evaluators }) => {

  const [rows, setRows] = useState<Evaluator[]>(evaluators || []);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  };

  const handleToggle = async (ev: Evaluator) => {

    const newStatus = ev.status === "active" ? "inactive" : "active";

    try {

      await updateEvaluatorStatus(ev.id, newStatus);

      setRows((prev) =>
        prev.map((r) =>
          r.id === ev.id ? { ...r, status: newStatus } : r
        )
      );

      showToast(
        `Evaluator ${newStatus === "active" ? "activated" : "deactivated"}`
      );

    } catch (err) {
      console.error("Failed to update evaluator status", err);
      showToast("Failed to update evaluator status");
    }
  };

  const handleSamplingUpdate = async (ev: Evaluator, value: string) => {

    const rate = parseFloat(value);

    if (isNaN(rate) || rate < 0 || rate > 1) {
      showToast("Sampling rate must be between 0 and 1");
      return;
    }

    if (rate === ev.execution?.sampling_rate) return;

    try {

      await updateSamplingRate(ev.id, rate);

      setRows((prev) =>
        prev.map((r) =>
          r.id === ev.id
            ? {
                ...r,
                execution: {
                  ...r.execution,
                  sampling_rate: rate
                }
              }
            : r
        )
      );

      showToast("Sampling rate updated");

    } catch (err) {
      console.error("Sampling update failed", err);
      showToast("Failed to update sampling rate");
    }
  };

  return (
    <div className="relative bg-[#161a23] border border-gray-800 rounded-2xl overflow-hidden">

      {/* Toast Notification */}
      {toast && (
        <div className="absolute top-4 right-4 bg-green-600 text-white text-sm px-4 py-2 rounded-lg shadow-lg z-50 animate-fade-in">
          {toast}
        </div>
      )}

      {/* Header */}
      <div className="p-6 border-b border-gray-800 bg-[#1c212e]/40">
        <h3 className="text-lg font-bold text-white">Active Evaluators</h3>
      </div>

      {rows.length === 0 ? (
        <div className="p-10 text-center text-gray-500 text-sm">
          No evaluators found
        </div>
      ) : (
        <div className="overflow-x-auto">

          <table className="w-full text-left border-collapse min-w-[950px]">

            {/* Header */}
            <thead className="bg-[#161a23]">
              <tr className="border-b border-gray-800/80">
                {[
                  "Name",
                  "Status",
                  "Template",
                  "Score Name",
                  "Target",
                  "Sampling",
                  "Created",
                  "Toggle"
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

            {/* Body */}
            <tbody>
              {rows.map((ev, i) => {

                const isActive = ev.status === "active";

                return (
                  <tr
                    key={ev.id || i}
                    className="border-b border-gray-800/40 hover:bg-[#1c212e]/40 transition-colors"
                  >

                    {/* Name */}
                    <td className="px-8 py-6 text-sm font-bold text-gray-200">
                      {ev.name || ev.score_name}
                    </td>

                    {/* Status */}
                    <td className="px-8 py-6">
                      <span
                        className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-black uppercase border ${
                          isActive
                            ? "bg-green-500/10 text-green-500 border-green-500/20"
                            : "bg-gray-700/20 text-gray-400 border-gray-600"
                        }`}
                      >
                        <div
                          className={`w-1.5 h-1.5 rounded-full ${
                            isActive ? "bg-green-500" : "bg-gray-500"
                          }`}
                        />
                        {ev.status}
                      </span>
                    </td>

                    {/* Template */}
                    <td className="px-8 py-6">
                      <span className="px-3 py-1 bg-gray-800/60 text-gray-300 text-xs font-bold rounded-lg border border-gray-700/50">
                        {ev.template?.id}
                      </span>
                    </td>

                    {/* Score Name */}
                    <td className="px-8 py-6 text-sm text-gray-400 font-mono">
                      {ev.score_name}
                    </td>

                    {/* Target */}
                    <td className="px-8 py-6">
                      <span className="px-2 py-0.5 bg-gray-900 border border-gray-800 text-gray-400 text-[9px] font-black rounded uppercase tracking-widest">
                        {ev.target}
                      </span>
                    </td>

                    {/* Sampling */}
                    <td className="px-8 py-6">
                      <input
                        type="number"
                        min="0"
                        max="1"
                        step="0.05"
                        defaultValue={ev.execution?.sampling_rate ?? 1}
                        className="w-20 bg-[#0e1117] border border-gray-700 rounded px-2 py-1 text-sm text-gray-300"
                        onBlur={(e) =>
                          handleSamplingUpdate(ev, e.target.value)
                        }
                      />
                    </td>

                    {/* Created */}
                    <td className="px-8 py-6 text-sm text-gray-500">
                      {ev.created_at
                        ? new Date(ev.created_at).toLocaleDateString()
                        : "-"}
                    </td>

                    {/* Toggle */}
                    <td className="px-8 py-6">
                      <button
                        onClick={() => handleToggle(ev)}
                        className={`px-3 py-1 rounded-lg text-xs font-bold transition ${
                          isActive
                            ? "bg-red-500/20 text-red-400 hover:bg-red-500/30"
                            : "bg-green-500/20 text-green-400 hover:bg-green-500/30"
                        }`}
                      >
                        {isActive ? "Deactivate" : "Activate"}
                      </button>
                    </td>

                  </tr>
                );
              })}
            </tbody>

          </table>

        </div>
      )}
    </div>
  );
};

export default EvaluatorsTable;