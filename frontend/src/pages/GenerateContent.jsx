/**
 * CrucibAI for Docs / Slides / Sheets (C1–C3).
 * Generate documents, slide decks, or spreadsheet data from a prompt.
 */
import { useState } from "react";
import axios from "axios";
import { useAuth } from "../App";
import { FileText, Presentation, Table, Loader2, Download } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL === '' ? '/api' : `${process.env.REACT_APP_BACKEND_URL || "http://localhost:8000"}/api`;

const tabs = [
  { id: "doc", label: "Docs", icon: FileText, formatOptions: [{ value: "markdown", label: "Markdown" }, { value: "plain", label: "Plain text" }] },
  { id: "slides", label: "Slides", icon: Presentation, formatOptions: [{ value: "markdown", label: "Markdown (slide deck)" }, { value: "outline", label: "Outline" }] },
  { id: "sheets", label: "Sheets", icon: Table, formatOptions: [{ value: "csv", label: "CSV" }, { value: "json", label: "JSON" }] },
];

export default function GenerateContent() {
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState("doc");
  const [prompt, setPrompt] = useState("");
  const [format, setFormat] = useState("markdown");
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [modelUsed, setModelUsed] = useState("");

  const currentTab = tabs.find((t) => t.id === activeTab) || tabs[0];
  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  const handleFormatChange = (e) => {
    const v = e.target.value;
    setFormat(v);
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError("Enter a prompt");
      return;
    }
    setError(null);
    setLoading(true);
    setContent("");
    try {
      const endpoint = `${API}/generate/${activeTab}`;
      const res = await axios.post(endpoint, { prompt: prompt.trim(), format }, { headers, timeout: 60000 });
      setContent(res.data.content || "");
      setModelUsed(res.data.model_used || "");
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  const download = () => {
    if (!content) return;
    const ext = activeTab === "doc" ? (format === "plain" ? "txt" : "md") : activeTab === "slides" ? "md" : format === "json" ? "json" : "csv";
    const mime = ext === "json" ? "application/json" : ext === "csv" ? "text/csv" : "text/markdown";
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `crucibai-${activeTab}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-[60vh] p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">CrucibAI for Docs, Slides & Sheets</h1>
      <p className="text-gray-600 text-sm mb-6">Generate documents, slide decks, or tabular data from a single prompt.</p>

      <div className="flex gap-2 border-b border-gray-200 mb-6">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => { setActiveTab(t.id); setFormat(t.formatOptions[0]?.value || "markdown"); setContent(""); setError(null); }}
            className={`flex items-center gap-2 px-4 py-2 rounded-t font-medium text-sm ${activeTab === t.id ? "bg-black text-[#1A1A1A]" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">What do you want to create?</label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={activeTab === "doc" ? "e.g. Product requirements doc for a task management app" : activeTab === "slides" ? "e.g. 5-slide pitch deck for a fintech startup" : "e.g. Quarterly sales data for 4 regions, 3 months"}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-#f5f5f50 focus:border-gray-300 min-h-[80px]"
            rows={3}
          />
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">Format:</label>
            <select value={format} onChange={handleFormatChange} className="border border-gray-300 rounded px-2 py-1 text-sm">
              {currentTab.formatOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <button
            type="button"
            onClick={handleGenerate}
            disabled={loading}
            className="px-4 py-2 bg-black text-[#1A1A1A] rounded-lg font-medium text-sm hover:bg-black disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            Generate
          </button>
        </div>
      </div>

      {error && <p className="text-gray-600 text-sm mt-2">{error}</p>}
      {modelUsed && <p className="text-gray-500 text-xs mt-1">Model: {modelUsed}</p>}

      {content && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Result</span>
            <button type="button" onClick={download} className="flex items-center gap-1 text-sm text-#000000 hover:underline">
              <Download className="w-4 h-4" />
              Download
            </button>
          </div>
          <pre className="w-full p-4 bg-gray-50 border border-gray-200 rounded-lg text-sm overflow-auto max-h-[400px] whitespace-pre-wrap font-sans">{content}</pre>
        </div>
      )}
    </div>
  );
}
