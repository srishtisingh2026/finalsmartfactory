import { type Evaluator } from "../api/client";

interface EvaluatorsTableProps {
  evaluators: Evaluator[] | { evaluators: Evaluator[] };
}

const EvaluatorsTable: React.FC<EvaluatorsTableProps> = ({ evaluators }) => {
  // --------------------------------------------------
  // Normalize input shape
  // Supports:
  //   evaluators = [...]
  //   evaluators = { evaluators: [...] }
  // --------------------------------------------------
  const allEvaluators = Array.isArray(evaluators)
    ? evaluators
    : evaluators?.evaluators || [];

  // --------------------------------------------------
  // Normalize ACTIVE evaluators
  // Backend currently uses mixed status values:
  //   "enabled", "active"
  // --------------------------------------------------
  const rows = allEvaluators.filter((ev) =>
    ["enabled", "active"].includes(ev.status)
  );

  return (
    <div className="bg-[#161a23] border border-gray-800 rounded-2xl overflow-hidden">
      <div className="p-6 border-b border-gray-800 bg-[#1c212e]/30">
        <h3 className="text-lg font-bold">Active Evaluators</h3>
      </div>

      {/* ---------------- EMPTY STATE ---------------- */}
      {rows.length === 0 ? (
        <div className="p-10 text-center text-gray-500 text-sm">
          No evaluators found
        </div>
      ) : (
        <table className="w-full text-left border-collapse">
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
            {rows.map((ev, i) => {
              const samplingPct =
                typeof ev.execution?.sampling_rate === "number"
                  ? ev.execution.sampling_rate * 100
                  : 0;

              const statusLabel = "active";

              return (
                <tr
                  key={ev.id || i}
                  className={`hover:bg-[#1c212e]/50 ${i !== rows.length - 1
                      ? "border-b border-gray-800/40"
                      : ""
                    }`}
                >
                  {/* Name */}
                  <td className="px-8 py-6 font-bold text-sm text-gray-200">
                    {ev.score_name || "—"}
                  </td>

                  {/* Status */}
                  <td className="px-8 py-6">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-green-500/10 border border-green-500/20 text-green-500 rounded-full text-[10px] font-black uppercase">
                      <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                      {statusLabel}
                    </span>
                  </td>

                  {/* Template */}
                  <td className="px-8 py-6">
                    <span className="px-3 py-1 bg-gray-800/60 text-gray-400 text-[10px] font-bold rounded-lg border border-gray-700/50">
                      {ev.template?.id || "Unknown"}
                    </span>
                  </td>

                  {/* Score Name */}
                  <td className="px-8 py-6 text-sm text-gray-400">
                    {ev.score_name || "—"}
                  </td>

                  {/* Target */}
                  <td className="px-8 py-6">
                    <span className="px-2 py-0.5 bg-gray-900 border border-gray-800 text-gray-500 text-[9px] font-black rounded uppercase tracking-widest">
                      {ev.target || "—"}
                    </span>
                  </td>

                  {/* Sampling */}
                  <td className="px-8 py-6 text-sm font-bold text-gray-300">
                    {samplingPct.toFixed(0)}%
                  </td>

                  {/* Created */}
                  <td className="px-8 py-6 text-sm text-gray-500">
                    {ev.created_at
                      ? new Date(ev.created_at).toLocaleDateString()
                      : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default EvaluatorsTable;
