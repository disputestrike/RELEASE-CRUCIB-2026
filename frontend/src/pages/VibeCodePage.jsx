import { useState } from "react";
import axios from "axios";
import { API } from "../App";
import { logApiError } from "../utils/apiError";

export default function VibeCodePage() {
  const [text, setText] = useState("Build a simple React todo app with dark mode");
  const [vibe, setVibe] = useState(null);
  const [generated, setGenerated] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyze = () => {
    setLoading(true);
    axios
      .post(`${API}/vibecoding/analyze`, { text })
      .then((r) => {
        setVibe(r.data.vibe);
        setGenerated(null);
      })
      .catch((e) => {
        logApiError("VibeCode analyze", e);
      })
      .finally(() => setLoading(false));
  };

  const generate = () => {
    setLoading(true);
    axios
      .post(`${API}/vibecoding/generate`, { prompt: text, vibe_analysis: vibe })
      .then((r) => setGenerated(r.data))
      .catch((e) => {
        logApiError("VibeCode generate", e);
      })
      .finally(() => setLoading(false));
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-semibold text-[#1A1A1A] mb-2">VibeCode</h1>
      <p className="text-sm text-[#666] mb-4">Analyze your prompt for vibe, then generate code that matches.</p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        className="w-full border border-gray-200 rounded-lg p-3 text-sm mb-4 min-h-[80px]"
        placeholder="Describe what you want to build..."
      />
      <div className="flex gap-2 mb-4">
        <button type="button" onClick={analyze} disabled={loading} className="px-4 py-2 bg-gray-100 text-[#1A1A1A] rounded hover:bg-gray-200 disabled:opacity-50 text-sm">
          Analyze vibe
        </button>
        <button type="button" onClick={generate} disabled={loading} className="px-4 py-2 bg-[#1A1A1A] text-white rounded hover:bg-[#333] disabled:opacity-50 text-sm">
          Generate code
        </button>
      </div>
      {vibe && (
        <div className="mb-4 p-3 bg-gray-50 rounded-lg text-sm">
          <strong>Vibe:</strong> style={vibe.code_style}, complexity={vibe.project_complexity}, frameworks={vibe.detected_frameworks?.join(", ") || "—"}, languages={vibe.detected_languages?.join(", ") || "—"}
        </div>
      )}
      {generated && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <pre className="p-3 bg-gray-50 text-xs overflow-auto max-h-[400px] whitespace-pre-wrap">{generated.code}</pre>
          {generated.explanation && <p className="p-3 text-sm text-[#666] border-t">{generated.explanation}</p>}
        </div>
      )}
    </div>
  );
}
