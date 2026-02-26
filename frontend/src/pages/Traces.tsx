import { useEffect, useState, useMemo } from "react";
import { api, type Trace } from "../api/client";

export default function Traces() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api
      .get("/traces")
      .then((res) => setTraces(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const filteredTraces = useMemo(() => {
    if (!search.trim()) return traces;
    const q = search.toLowerCase();
    return traces.filter((t) =>
      t.trace_name?.toLowerCase().includes(q)
    );
  }, [traces, search]);

  if (loading) {
    return <div className="p-6 text-gray-400 text-sm">Loading traces…</div>;
  }

  return (
    <div className="space-y-4 text-white">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Traces</h1>
          <p className="text-xs text-gray-400">
            {filteredTraces.length} traces
          </p>
        </div>

        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by trace name…"
          className="bg-[#161a23] border border-gray-700 rounded-md px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-teal-500 w-56"
        />
      </div>

      <div className="overflow-x-auto rounded-xl border border-[#1f242d] bg-[#0d1117]">
        <table className="min-w-full text-xs">
          <thead className="bg-[#161b22] border-b border-[#1f242d]">
            <tr className="text-gray-400">
              <th className="px-3 py-2 text-left font-medium">Timestamp</th>
              <th className="px-3 py-2 text-left font-medium">Name</th>
              <th className="px-3 py-2 text-left font-medium w-[40%]">Input</th>
              <th className="px-3 py-2 text-left font-medium">Latency</th>
              <th className="px-3 py-2 text-left font-medium">Tokens</th>
              <th className="px-3 py-2 text-left font-medium">Cost</th>
              <th className="px-3 py-2 text-left font-medium">Scores</th>
            </tr>
          </thead>

          <tbody>
            {filteredTraces.map((t) => {
              const scores = t.scores || {};

              return (
                <tr
                  key={t.trace_id}
                  className="border-b border-[#1f242d] hover:bg-[#161a23] transition"
                >
                  <td className="px-3 py-2 text-gray-400 whitespace-nowrap">
                    {new Date(t.timestamp).toLocaleString()}
                  </td>

                  <td className="px-3 py-2">
                    <span className="px-2 py-0.5 rounded-full bg-[#0f172a] border border-[#1f2937] text-xs font-medium text-gray-200">
                      {t.trace_name}
                    </span>
                  </td>

                  <td className="px-3 py-2 text-gray-300 truncate max-w-[520px]">
                    {t.input}
                  </td>

                  <td className="px-3 py-2 text-gray-300">
                    {t.latency_ms}ms
                  </td>

                  <td className="px-3 py-2 text-gray-300">
                    {(t.tokens ?? 0).toFixed(3)}
                  </td>

                  <td className="px-3 py-2 text-gray-300">
                    ${(t.cost ?? 0).toFixed(5)}
                  </td>

                  <td className="px-3 py-2">
                    <div className="flex gap-1.5 flex-wrap max-w-[260px]">
                      {Object.entries(scores).map(([k, v]) => (
                        <span
                          key={k}
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold
                            ${
                              v < 0.3
                                ? "bg-[#3a1d16] text-[#ffb29b]"
                                : v < 0.6
                                ? "bg-[#2f1e0a] text-[#fcd34d]"
                                : "bg-[#0d2a1f] text-[#6ee7b7]"
                            }`}
                        >
                          {k}: {Number(v).toFixed(2)}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              );
            })}

            {filteredTraces.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-gray-500">
                  No traces match “{search}”
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
