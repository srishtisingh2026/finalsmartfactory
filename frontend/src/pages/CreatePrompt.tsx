import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Save, Terminal, ArrowLeft, Settings } from 'lucide-react';
import { api } from '../api/client';

const CreatePrompt = () => {
    const navigate = useNavigate();
    const [isLoading, setIsLoading] = useState(false);

    // Form State
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [tags, setTags] = useState("");
    const [content, setContent] = useState("");
    const [variables, setVariables] = useState<string[]>([]);

    // Variable Detection
    useEffect(() => {
        const regex = /\{\{([a-zA-Z0-9_]+)\}\}/g;
        const found: string[] = [];
        let match;
        const regexSingle = /\{([a-zA-Z0-9_]+)\}/g;

        let tempContent = content;
        while ((match = regex.exec(tempContent)) !== null) {
            found.push(match[1]);
        }
        while ((match = regexSingle.exec(tempContent)) !== null) {
            if (!found.includes(match[1])) found.push(match[1]);
        }
        setVariables([...new Set(found)]);
    }, [content]);

    // Model Config State
    const [modelConfig, setModelConfig] = useState({
        model: "gpt-4o",
        temperature: 0.7,
        maxTokens: 500,
        topP: 0.95,
        freqPenalty: 0,
        presPenalty: 0
    });

    const handleSave = async () => {
        if (!name.trim() || !content.trim()) {
            alert("Name and Content are required");
            return;
        }

        setIsLoading(true);
        try {
            const res = await api.post('/prompts', {
                name,
                description,
                content,
                variables,
                tags: tags.split(',').map(t => t.trim()).filter(Boolean),
                model_parameters: modelConfig
            });

            if (res.status === 200) {
                navigate('/prompts');
            }
        } catch (e: any) {
            console.error(e);
            alert(`Failed to create prompt: ${e.response?.data?.detail || 'Unknown error'}`);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="h-[calc(100vh-theme(spacing.24))] flex flex-col bg-[#111827] rounded-xl shadow-lg border border-slate-800 overflow-hidden text-slate-200">
            {/* Header */}
            <div className="p-6 border-b border-slate-800 flex justify-between items-center bg-[#111827]">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => navigate('/prompts')}
                        className="p-2 hover:bg-slate-800 rounded-full text-slate-400 transition-colors"
                    >
                        <ArrowLeft size={20} />
                    </button>
                    <div>
                        <h1 className="text-xl font-bold text-slate-100">Create New Prompt</h1>
                        <p className="text-sm text-slate-500">Configure your prompt template and variables</p>
                    </div>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={() => navigate('/prompts')}
                        className="px-4 py-2 border border-slate-700 text-slate-400 rounded-lg hover:bg-slate-800 text-sm font-medium transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={isLoading}
                        className="flex items-center px-4 py-2 bg-teal-500 text-slate-950 rounded-lg hover:bg-teal-400 text-sm font-bold disabled:opacity-50 transition-colors shadow-[0_0_10px_rgba(20,184,166,0.3)]"
                    >
                        <Save size={16} className="mr-2" />
                        {isLoading ? 'Creating...' : 'Create Prompt'}
                    </button>
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden">
                {/* Main Form */}
                <div className="flex-1 overflow-y-auto p-8 border-r border-slate-800 bg-[#0B0E14]">
                    <div className="max-w-2xl space-y-6">

                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-1">Prompt Name</label>
                            <input
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className="w-full px-4 py-2 bg-[#0D1117] border border-slate-700 rounded-lg text-slate-200 focus:ring-1 focus:ring-teal-500 focus:border-teal-500 outline-none transition-all placeholder-slate-600"
                                placeholder="e.g., Customer Support Agent"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-1">Description</label>
                            <textarea
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                className="w-full px-4 py-2 bg-[#0D1117] border border-slate-700 rounded-lg text-slate-200 focus:ring-1 focus:ring-teal-500 focus:border-teal-500 outline-none transition-all h-24 resize-none placeholder-slate-600"
                                placeholder="What is this prompt used for?"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-1">Tags</label>
                            <input
                                type="text"
                                value={tags}
                                onChange={(e) => setTags(e.target.value)}
                                className="w-full px-4 py-2 bg-[#0D1117] border border-slate-700 rounded-lg text-slate-200 focus:ring-1 focus:ring-teal-500 focus:border-teal-500 outline-none transition-all placeholder-slate-600"
                                placeholder="production, version-1, experimental (comma separated)"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-1">
                                Prompt Content
                                <span className="ml-2 text-xs font-normal text-slate-500">Use {'{{variable}}'} for dynamic inputs</span>
                            </label>
                            <div className="bg-[#151921] rounded-xl border border-slate-800 p-1 relative min-h-[300px] flex flex-col group">
                                <div className="absolute top-4 left-4 z-10">
                                    <span className="px-2 py-1 bg-slate-800 text-slate-400 text-[10px] uppercase font-bold rounded border border-slate-700">System</span>
                                </div>
                                <textarea
                                    className="flex-1 w-full bg-[#0D1117] text-slate-300 font-mono text-sm p-6 pt-12 focus:outline-none resize-none leading-relaxed rounded-lg"
                                    value={content}
                                    onChange={(e) => setContent(e.target.value)}
                                    spellCheck={false}
                                    placeholder="You are a helpful assistant. User query: {{query}}"
                                />
                            </div>
                        </div>

                    </div>
                </div>

                {/* Sidebar Info & Config */}
                <div className="w-80 bg-[#111827] p-6 overflow-y-auto hidden xl:block border-l border-slate-800">

                    {/* Model Config Section */}
                    <div className="mb-8">
                        <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2">
                            <Settings size={16} className="text-teal-500" />
                            Model Configuration
                        </h3>

                        <div className="space-y-4">
                            <div>
                                <label className="text-xs font-semibold text-slate-400 block mb-1">Model</label>
                                <select
                                    value={modelConfig.model}
                                    onChange={(e) => setModelConfig({ ...modelConfig, model: e.target.value })}
                                    className="w-full bg-[#0D1117] border border-slate-700 text-slate-200 text-xs rounded p-2 focus:border-teal-500 outline-none"
                                >
                                    <option value="gpt-4o">gpt-4o</option>
                                    <option value="gpt-4-turbo">gpt-4-turbo</option>
                                    <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                                </select>
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-xs font-semibold text-slate-400 block mb-1">Temp</label>
                                    <input
                                        type="number" step="0.1"
                                        value={modelConfig.temperature}
                                        onChange={(e) => setModelConfig({ ...modelConfig, temperature: parseFloat(e.target.value) })}
                                        className="w-full bg-[#0D1117] border border-slate-700 text-slate-200 text-xs rounded p-2 focus:border-teal-500 outline-none"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs font-semibold text-slate-400 block mb-1">Max Tokens</label>
                                    <input
                                        type="number"
                                        value={modelConfig.maxTokens}
                                        onChange={(e) => setModelConfig({ ...modelConfig, maxTokens: parseInt(e.target.value) })}
                                        className="w-full bg-[#0D1117] border border-slate-700 text-slate-200 text-xs rounded p-2 focus:border-teal-500 outline-none"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-xs font-semibold text-slate-400 block mb-1">Top P</label>
                                    <input
                                        type="number" step="0.05"
                                        value={modelConfig.topP}
                                        onChange={(e) => setModelConfig({ ...modelConfig, topP: parseFloat(e.target.value) })}
                                        className="w-full bg-[#0D1117] border border-slate-700 text-slate-200 text-xs rounded p-2 focus:border-teal-500 outline-none"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs font-semibold text-slate-400 block mb-1">Freq Penalty</label>
                                    <input
                                        type="number" step="0.1"
                                        value={modelConfig.freqPenalty}
                                        onChange={(e) => setModelConfig({ ...modelConfig, freqPenalty: parseFloat(e.target.value) })}
                                        className="w-full bg-[#0D1117] border border-slate-700 text-slate-200 text-xs rounded p-2 focus:border-teal-500 outline-none"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="sticky top-0">
                        <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2">
                            <Terminal size={16} className="text-teal-500" />
                            Detected Variables
                        </h3>

                        <div className="space-y-3">
                            {variables.length > 0 ? (
                                variables.map(v => (
                                    <div key={v} className="bg-[#0D1117] px-3 py-2 rounded-lg border border-slate-800 flex items-center justify-between">
                                        <span className="font-mono text-teal-400 text-sm">{v}</span>
                                        <span className="text-[10px] uppercase font-bold text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700">STR</span>
                                    </div>
                                ))
                            ) : (
                                <div className="text-sm text-slate-500 italic p-4 text-center border border-dashed border-slate-800 rounded-lg">
                                    No variables detected.
                                </div>
                            )}
                        </div>

                        <div className="mt-8">
                            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Quick Tips</h4>
                            <ul className="text-sm text-slate-500 space-y-2 list-disc list-inside">
                                <li>Use curly braces for {`{{variables}}`}</li>
                                <li>Variables are auto-detected</li>
                                <li>Description helps others understand intent</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};


export default CreatePrompt;