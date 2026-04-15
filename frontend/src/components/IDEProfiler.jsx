import { useState } from "react";
import axios from "axios";
import { useAuth } from '../App';
import { API_BASE as API } from '../apiBase';
import { logApiError } from "../utils/apiError";

export default function IDEProfiler() {
  const { token } = useAuth();
  const [projectId, setProjectId] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stopLoading, setStopLoading] = useState(false);

  const startProfiler = () => {
    setLoading(true);
    setSummary(null);
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    axios
      .post(`${API}/ide/profiler/start`, null, { params: { project_id: projectId }, headers })
      .then((r) => setSessionId(r.data.session_id))
      .catch((e) => logApiError("IDEProfiler start", e))
      .finally(() => setLoading(false));
  };

  const stopProfiler = () => {
    if (!sessionId) return;
    setStopLoading(true);
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    axios
      .post(`${API}/ide/profiler/stop`, null, { params: { session_id: sessionId }, headers })
      .then((r) => {
        setSummary(r.data.summary || r.data);
        setSessionId(null);
      })
      .catch((e) => logApiError("IDEProfiler stop", e))
      .finally(() => setStopLoading(false));
  };

  return (
    <div className="p-6 max-w-2xl">
      <h2 className="text-lg font-medium text-[#1A1A1A] mb-2">Profiler</h2>
      <p className="text-sm text-[#666] mb-4">Start/stop profiler for a project (backend stub — real profiler can be wired later).</p>
      <input
        type="text"
        value={projectId}
        onChange={(e) => setProjectId(e.target.value)}
        className="border border-gray-200 rounded px-3 py-2 text-sm w-full mb-2"
        placeholder="Project ID"
      />
      <div className="flex gap-2 mb-4">
        <button type="button" onClick={startProfiler} disabled={loading || sessionId || !projectId.trim()} className="px-4 py-2 bg-[#1A1A1A] text-white rounded text-sm disabled:opacity-50">
          {loading ? "Starting…" : "Start profiler"}
        </button>
        {sessionId && (
          <button type="button" onClick={stopProfiler} disabled={stopLoading} className="px-4 py-2 border border-gray-300 text-[#1A1A1A] rounded text-sm disabled:opacity-50">
            {stopLoading ? "Stopping…" : "Stop profiler"}
          </button>
        )}
      </div>
      {sessionId && <p className="text-sm text-[#666] mb-2">Session: {sessionId} — click Stop to see summary.</p>}
      {summary && Object.keys(summary).length > 0 && (
        <pre className="p-3 bg-gray-100 text-[#1A1A1A] border border-gray-200 rounded text-xs overflow-auto">{JSON.stringify(summary, null, 2)}</pre>
      )}
      {summary && Object.keys(summary).length === 0 && <p className="text-sm text-[#666]">Profiler stopped. No summary data (stub).</p>}
    </div>
  );
}
