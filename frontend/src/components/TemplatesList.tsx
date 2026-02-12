import { Plus } from "lucide-react";
import { type Template } from "../api/client";

interface TemplatesListProps {
  templates: Template[];
  onNewTemplate: () => void;
}

const TemplatesList: React.FC<TemplatesListProps> = ({ templates, onNewTemplate }) => {
  return (
    <div className="flex flex-col w-full gap-6 mt-4">

      {/* Header Row */}
      <div className="flex justify-between items-center mb-2">
        <h2 className="text-xl font-bold">Evaluator Templates</h2>

        <button
          onClick={onNewTemplate}
          className="
            flex items-center gap-2 px-4 py-2 
            rounded-lg font-bold text-white
            bg-[#1c212e] border border-gray-700
            transition-all duration-150

            hover:bg-[#13bba4] hover:text-black hover:border-transparent
        "
        >
          <Plus size={16} />
          New Template
        </button>

      </div>

      {/* Template Cards */}
      {templates.map((t) => {
        const updated = t.updated_at
          ? new Date(t.updated_at).toLocaleString()
          : "Unknown";

        return (
          <div
            key={t.template_id}
            className="bg-[#161a23] border border-gray-800 rounded-2xl p-6"
          >

            {/* Header */}
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-bold text-white">{t.name}</h3>
                <p className="text-sm text-gray-400">{t.description}</p>
              </div>

              <div className="px-3 py-1 bg-gray-800 text-gray-300 text-xs font-black rounded-lg">
                v{t.version}
              </div>
            </div>

            {/* Template Body */}
            <div className="bg-[#0e1117] border border-gray-800 rounded-xl p-4 text-sm text-gray-300 whitespace-pre-wrap mb-4">
              {t.template}
            </div>

            {/* Model + Inputs */}
            <div className="flex flex-wrap items-center gap-3 mb-3">
              <span className="px-3 py-1 bg-gray-800 text-gray-300 text-xs font-bold rounded-lg border border-gray-700">
                Model: {t.model}
              </span>

              {t.inputs?.map((inp) => (
                <span
                  key={inp}
                  className="px-3 py-1 bg-black text-gray-300 text-xs font-mono rounded-lg border border-gray-800"
                >
                  {`{{${inp}}}`}
                </span>
              ))}
            </div>

            {/* Timestamp */}
            <p className="text-xs text-gray-500">Last updated: {updated}</p>
          </div>
        );
      })}
    </div>
  );
};

export default TemplatesList;
