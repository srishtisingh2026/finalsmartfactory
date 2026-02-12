import { ChevronDown, Check } from "lucide-react";
import { type EvaluationLog } from "../api/client";

interface LogsFiltersProps {
  logs: EvaluationLog[];
  filterEvaluator: string;
  setFilterEvaluator: (val: string) => void;
  filterStatus: string;
  setFilterStatus: (val: string) => void;
  showEvaluatorDropdown: boolean;
  setShowEvaluatorDropdown: (val: boolean) => void;
  showStatusDropdown: boolean;
  setShowStatusDropdown: (val: boolean) => void;
}

const LogsFilters: React.FC<LogsFiltersProps> = ({
  logs,
  filterEvaluator,
  setFilterEvaluator,
  filterStatus,
  setFilterStatus,
  showEvaluatorDropdown,
  setShowEvaluatorDropdown,
  showStatusDropdown,
  setShowStatusDropdown
}) => {
  const evaluatorOptions = [
    "All Evaluators",
    ...Array.from(new Set(logs.map((l) => l.evaluator_name)))
  ];

  const statusOptions = ["All Status", "Completed", "Error", "Timeout"];

  return (
    <div className="flex gap-3">

      {/* -------------------- Evaluator Dropdown -------------------- */}
      <div className="relative">
        <button
          onClick={() => {
            setShowEvaluatorDropdown(!showEvaluatorDropdown);
            setShowStatusDropdown(false);
          }}
          className="flex items-center justify-between gap-2 bg-[#0e1117] border border-gray-800 text-gray-300 text-xs font-bold rounded-lg px-4 py-2 w-40"
        >
          {filterEvaluator}
          <ChevronDown size={14} />
        </button>

        {showEvaluatorDropdown && (
          <div className="absolute mt-2 w-56 bg-[#ffffff] text-black border border-gray-700 rounded-xl shadow-xl z-50 py-2">
            {evaluatorOptions.map((opt) => {
              const isSelected = filterEvaluator === opt;

              return (
                <button
                  key={opt}
                  onClick={() => {
                    setFilterEvaluator(opt);
                    setShowEvaluatorDropdown(false);
                  }}
                  className={`w-full flex items-center gap-2 text-left px-4 py-2 text-sm rounded-lg
                    ${isSelected
                      ? "bg-[#13bba4] text-black font-bold"
                      : "text-gray-800 hover:bg-gray-200"
                    }
                  `}
                >
                  {isSelected && <Check size={14} className="text-black" />}
                  {opt}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* -------------------- Status Dropdown -------------------- */}
      <div className="relative">
        <button
          onClick={() => {
            setShowStatusDropdown(!showStatusDropdown);
            setShowEvaluatorDropdown(false);
          }}
          className="flex items-center justify-between gap-2 bg-[#0e1117] border border-gray-800 text-gray-300 text-xs font-bold rounded-lg px-4 py-2 w-32"
        >
          {filterStatus}
          <ChevronDown size={14} />
        </button>

        {showStatusDropdown && (
          <div className="absolute mt-2 w-48 bg-[#ffffff] text-black border border-gray-700 rounded-xl shadow-xl z-50 py-2">
            {statusOptions.map((opt) => {
              const isSelected = filterStatus === opt;

              return (
                <button
                  key={opt}
                  onClick={() => {
                    setFilterStatus(opt);
                    setShowStatusDropdown(false);
                  }}
                  className={`w-full flex items-center gap-2 text-left px-4 py-2 text-sm rounded-lg
                    ${isSelected
                      ? "bg-[#13bba4] text-black font-bold"
                      : "text-gray-800 hover:bg-gray-200"
                    }
                  `}
                >
                  {isSelected && <Check size={14} className="text-black" />}
                  {opt}
                </button>
              );
            })}
          </div>
        )}
      </div>

    </div>
  );
};

export default LogsFilters;
