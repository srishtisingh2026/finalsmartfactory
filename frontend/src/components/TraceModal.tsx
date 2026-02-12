import { Activity, Loader2, X } from "lucide-react";
import { type Trace } from "../api/client";

interface TraceModalProps {
  selectedTrace: Trace | null;
  loadingTrace: boolean;
  onClose: () => void;
}

const TraceModal: React.FC<TraceModalProps> = ({
  selectedTrace,
  loadingTrace,
  onClose
}) => {
  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-[#161a23] border border-gray-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden shadow-xl">

        {/* Header */}
        <div className="p-6 border-b border-gray-800 bg-[#1c212e]/50 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2">
              <Activity className="text-[#13bba4]" />
              Trace Details
            </h2>
            <p className="text-xs text-gray-500 font-mono">
              ID: {selectedTrace?.trace_id || "loading..."}
            </p>
          </div>

          <button
            onClick={onClose}
            className="w-10 h-10 flex items-center justify-center rounded-lg bg-gray-800 hover:bg-gray-700"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loadingTrace ? (
            <div className="flex flex-col items-center justify-center py-10">
              <Loader2 className="animate-spin text-[#13bba4]" size={40} />
              <p className="mt-4 text-xs text-gray-500 uppercase tracking-widest">
                Fetching Trace...
              </p>
            </div>
          ) : selectedTrace ? (
            <>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-[#0e1117] border border-gray-800 rounded-xl p-4">
                  <label className="text-[10px] uppercase text-gray-500 font-black">
                    Latency
                  </label>
                  <p className="text-lg font-bold mt-1">
                    {selectedTrace.latency_ms || selectedTrace.latency || 0}ms
                  </p>
                </div>

                <div className="bg-[#0e1117] border border-gray-800 rounded-xl p-4">
                  <label className="text-[10px] uppercase text-gray-500 font-black">
                    Tokens
                  </label>
                  <p className="text-lg font-bold mt-1">
                    {selectedTrace.tokens || 0}
                  </p>
                </div>

                <div className="bg-[#0e1117] border border-gray-800 rounded-xl p-4">
                  <label className="text-[10px] uppercase text-gray-500 font-black">
                    Estimated Cost
                  </label>
                  <p className="text-lg font-bold text-[#13bba4] mt-1">
                    ${Number(selectedTrace.cost || 0).toFixed(4)}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="text-[10px] uppercase text-gray-500 font-black">
                    Input Prompt
                  </label>
                  <div className="mt-2 bg-[#0e1117] border border-gray-800 rounded-xl p-4 text-sm text-gray-300">
                    {selectedTrace.question ||
                      selectedTrace.input ||
                      "No input recorded"}
                  </div>
                </div>

                <div>
                  <label className="text-[10px] uppercase text-gray-500 font-black">
                    Model Output
                  </label>
                  <div className="mt-2 bg-[#0e1117] border border-[#13bba4]/20 rounded-xl p-4 text-sm text-gray-200 shadow-inner">
                    {selectedTrace.answer ||
                      selectedTrace.output ||
                      "No output recorded"}
                  </div>
                </div>
              </div>

              {(selectedTrace.context ||
                selectedTrace.retrieval_context) && (
                  <div>
                    <label className="text-[10px] uppercase text-gray-500 font-black">
                      Retrieval Context
                    </label>
                    <div className="mt-2 bg-[#0e1117] border border-gray-800 rounded-xl p-4 text-xs text-gray-400 whitespace-pre-wrap">
                      {typeof selectedTrace.context === "string"
                        ? selectedTrace.context
                        : JSON.stringify(
                          selectedTrace.context ||
                          selectedTrace.retrieval_context,
                          null,
                          2
                        )}
                    </div>
                  </div>
                )}
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-800 bg-[#1c212e]/30 flex justify-end">
          <button
            onClick={onClose}
            className="px-8 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default TraceModal;
