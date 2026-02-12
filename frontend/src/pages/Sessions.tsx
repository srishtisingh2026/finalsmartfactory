import { useEffect, useState } from "react";
import { api, type Session } from "../api/client";

export default function Sessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/sessions")
      .then((res) => {
        setSessions(res.data);
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    return date.toLocaleString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  };

  if (loading) {
    return (
      <div className="p-8 text-[#8e9196] font-medium">
        Loading sessions...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold text-white tracking-tight">
          Sessions
        </h1>
        <p className="text-[#8e9196] text-sm font-medium">
          {sessions.length} sessions
        </p>
      </div>

      <div className="bg-[#11141d] rounded-xl border border-[#1e2330] overflow-hidden shadow-2xl">
        <div className="px-6 py-5 border-b border-[#1e2330]">
          <h2 className="text-xl font-bold text-white">All Sessions</h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="text-[#8e9196] text-[11px] uppercase tracking-wider font-bold border-b border-[#1e2330]">
                <th className="px-6 py-4">Session ID</th>
                <th className="px-6 py-4">User</th>
                <th className="px-6 py-4 text-center">Traces</th>
                <th className="px-6 py-4 text-center">Total Tokens</th>
                <th className="px-6 py-4 text-center">Total Cost</th>
                <th className="px-6 py-4">Created</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-[#1e2330]">
              {sessions.map((s) => (
                <tr key={s.session_id} className="hover:bg-[#1a1c23] transition-colors group">
                  <td className="px-6 py-4">
                    <span className="bg-[#1a1c23] group-hover:bg-[#252833] text-white text-xs font-bold px-3 py-1.5 rounded-full border border-[#1e2330] transition-colors">
                      {s.session_id}
                    </span>
                  </td>

                  <td className="px-6 py-4 text-sm text-[#e0e0e0] font-medium">
                    {s.user || s.user_id || "Unknown"}
                  </td>

                  <td className="px-6 py-4 text-sm text-[#e0e0e0] text-center font-bold">
                    {s.trace_count}
                  </td>

                  <td className="px-6 py-4 text-sm text-[#e0e0e0] text-center font-bold">
                    {s.total_tokens?.toLocaleString()}
                  </td>

                  <td className="px-6 py-4 text-sm text-[#e0e0e0] text-center font-bold">
                    ${s.total_cost?.toFixed(6)}
                  </td>

                  <td className="px-6 py-4 text-sm text-[#e0e0e0] font-medium">
                    {formatDate(s.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>

          </table>
        </div>
      </div>
    </div>
  );
}
