import { useState } from "react";
import axios from "axios";
import { API } from "../App";
import { logApiError } from "../utils/apiError";

const SECTIONS = [
  { id: "tests", label: "Generate tests", placeholder: "Paste code to generate unit/integration tests", action: "Generate" },
  { id: "security", label: "Security scan", placeholder: "Paste code to scan for security issues", action: "Scan" },
  { id: "optimize", label: "Optimize code", placeholder: "Paste code to optimize for performance", action: "Optimize" },
  { id: "docs", label: "Generate docs", placeholder: "Project name and description for README", action: "Generate" },
];

export default function AIFeaturesPanel() {
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("javascript");
  const [framework, setFramework] = useState("");
  const [testType, setTestType] = useState("unit");
  const [activeSection, setActiveSection] = useState("tests");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [docProjectName, setDocProjectName] = useState("");
  const [docDescription, setDocDescription] = useState("");
  const [docFeatures, setDocFeatures] = useState("");

  const runAction = () => {
    setLoading(true);
    setResult(null);
    if (activeSection === "tests") {
      axios
        .post(`${API}/ai/tests/generate`, { code, language, framework: framework || undefined, test_type: testType })
        .then((r) => setResult({ type: "tests", ...r.data }))
        .catch((e) => {
          logApiError("AIFeaturesPanel tests", e);
          setResult({ type: "error", message: e?.response?.data?.detail || e?.message });
        })
        .finally(() => setLoading(false));
    } else if (activeSection === "security") {
      axios
        .post(`${API}/ai/security-scan`, { files: { "/App.js": code } })
        .then((r) => setResult({ type: "security", report: r.data.report, checklist: r.data.checklist, passed: r.data.passed, failed: r.data.failed }))
        .catch((e) => {
          logApiError("AIFeaturesPanel security", e);
          setResult({ type: "error", message: e?.response?.data?.detail || e?.message });
        })
        .finally(() => setLoading(false));
    } else if (activeSection === "optimize") {
      axios
        .post(`${API}/ai/optimize`, { code, language })
        .then((r) => setResult({ type: "optimize", code: r.data.code }))
        .catch((e) => {
          logApiError("AIFeaturesPanel optimize", e);
          setResult({ type: "error", message: e?.response?.data?.detail || e?.message });
        })
        .finally(() => setLoading(false));
    } else if (activeSection === "docs") {
      axios
        .post(`${API}/ai/docs/generate`, { project_name: docProjectName, description: docDescription, features: docFeatures ? docFeatures.split("\n").filter(Boolean) : undefined })
        .then((r) => setResult({ type: "docs", readme: r.data.readme }))
        .catch((e) => {
          logApiError("AIFeaturesPanel docs", e);
          setResult({ type: "error", message: e?.response?.data?.detail || e?.message });
        })
        .finally(() => setLoading(false));
    }
  };

  return (
    <div className="p-6 max-w-2xl">
      <h2 className="text-lg font-medium text-[#1A1A1A] mb-2">AI Features</h2>
      <p className="text-sm text-[#666] mb-4">Generate tests, run security scan, or optimize code. Uses your API keys from Settings when set.</p>
      <div className="flex gap-2 mb-3 border-b border-gray-200">
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setActiveSection(s.id)}
            className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px ${activeSection === s.id ? "border-[#1A1A1A] text-[#1A1A1A]" : "border-transparent text-[#666]"}`}
          >
            {s.label}
          </button>
        ))}
      </div>
      {activeSection === "tests" && (
        <div className="flex gap-2 mb-3">
          <select value={language} onChange={(e) => setLanguage(e.target.value)} className="border border-gray-200 rounded px-3 py-2 text-sm">
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
            <option value="python">Python</option>
          </select>
          <input type="text" value={framework} onChange={(e) => setFramework(e.target.value)} className="border border-gray-200 rounded px-3 py-2 text-sm flex-1" placeholder="Framework (optional)" />
          <select value={testType} onChange={(e) => setTestType(e.target.value)} className="border border-gray-200 rounded px-3 py-2 text-sm">
            <option value="unit">Unit</option>
            <option value="integration">Integration</option>
          </select>
        </div>
      )}
      {activeSection === "optimize" && (
        <div className="mb-3">
          <select value={language} onChange={(e) => setLanguage(e.target.value)} className="border border-gray-200 rounded px-3 py-2 text-sm">
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
            <option value="python">Python</option>
          </select>
        </div>
      )}
      {activeSection === "docs" && (
        <div className="space-y-2 mb-3">
          <input type="text" value={docProjectName} onChange={(e) => setDocProjectName(e.target.value)} className="border border-gray-200 rounded px-3 py-2 text-sm w-full" placeholder="Project name" />
          <input type="text" value={docDescription} onChange={(e) => setDocDescription(e.target.value)} className="border border-gray-200 rounded px-3 py-2 text-sm w-full" placeholder="Description (optional)" />
          <textarea value={docFeatures} onChange={(e) => setDocFeatures(e.target.value)} className="border border-gray-200 rounded px-3 py-2 text-sm w-full min-h-[60px]" placeholder="Features (one per line, optional)" />
        </div>
      )}
      {activeSection !== "docs" && <textarea
        value={code}
        onChange={(e) => setCode(e.target.value)}
        className="border border-gray-200 rounded px-3 py-2 text-sm w-full font-mono min-h-[120px] mb-3"
        placeholder={SECTIONS.find((s) => s.id === activeSection)?.placeholder}
      />}
      <button type="button" onClick={runAction} disabled={loading} className="px-4 py-2 bg-[#1A1A1A] text-white rounded text-sm disabled:opacity-50 mb-4">
        {loading ? "Running…" : SECTIONS.find((s) => s.id === activeSection)?.action}
      </button>
      {result && result.type === "error" && <p className="text-sm text-red-600">{result.message}</p>}
      {result && result.type === "tests" && (
        <div className="border border-gray-200 rounded bg-white p-3 text-sm">
          <p className="text-[#666] mb-1">{result.description}</p>
          <pre className="p-2 bg-gray-100 text-[#1A1A1A] rounded text-xs overflow-auto max-h-48 whitespace-pre-wrap">{result.code}</pre>
        </div>
      )}
      {result && result.type === "security" && (
        <div className="border border-gray-200 rounded bg-white p-3 text-sm">
          <p className="text-[#666] mb-1">Passed: {result.passed}, Failed: {result.failed}</p>
          <pre className="p-2 bg-gray-100 text-[#1A1A1A] rounded text-xs overflow-auto max-h-48 whitespace-pre-wrap">{result.report}</pre>
        </div>
      )}
      {result && result.type === "optimize" && (
        <div className="border border-gray-200 rounded bg-white p-3 text-sm">
          <pre className="p-2 bg-gray-100 text-[#1A1A1A] rounded text-xs overflow-auto max-h-48 whitespace-pre-wrap">{result.code}</pre>
        </div>
      )}
      {result && result.type === "docs" && (
        <div className="border border-gray-200 rounded bg-white p-3 text-sm">
          <pre className="p-2 bg-gray-100 text-[#1A1A1A] rounded text-xs overflow-auto max-h-48 whitespace-pre-wrap">{result.readme}</pre>
        </div>
      )}
    </div>
  );
}
