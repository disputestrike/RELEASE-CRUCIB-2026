import { useState } from "react";
import axios from "axios";
import { useAuth } from '../App';
import { API_BASE as API } from '../apiBase';
import { logApiError } from "../utils/apiError";

export default function IDETerminal() {
  const { token } = useAuth();
  const [sessionId, setSessionId] = useState(null);
  const [projectId, setProjectId] = useState("");
  const [command, setCommand] = useState("dir");
  const [output, setOutput] = useState(null);
  const [loading, setLoading] = useState(false);
  const [execLoading, setExecLoading] = useState(false);

  const createSession = () => {
    setLoading(true);
    setOutput(null);
    const params = { project_id: projectId, shell: "/bin/bash" };
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    axios
      .post(`${API}/terminal/create`, null, { params, headers })
      .then((r) => setSessionId(r.data.session_id))
      .catch((e) => logApiError("IDETerminal create", e))
      .finally(() => setLoading(false));
  };

  const runCommand = () => {
    if (!sessionId) return;
    setExecLoading(true);
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    axios
      .post(`${API}/terminal/${sessionId}/execute`, { command, timeout: 30 }, { headers })
      .then((r) => setOutput(r.data))
      .catch((e) => {
        logApiError("IDETerminal execute", e);
        setOutput({ returncode: -1, stdout: "", stderr: e?.response?.data?.detail || e?.message || "Request failed" });
      })
      .finally(() => setExecLoading(false));
  };

  return (
    <div className="p-6 max-w-2xl">
      <h2 className="text-lg font-medium text-[#1A1A1A] mb-2">Terminal (full implementation)</h2>
      <p className="text-sm text-[#666] mb-4">Creates a session and runs commands in your authenticated project workspace.</p>
      <input
        type="text"
        value={projectId}
        onChange={(e) => setProjectId(e.target.value)}
        className="border border-gray-200 rounded px-3 py-2 text-sm w-full mb-2"
        placeholder="Project ID (optional — from /app/projects/ID)"
      />
      <button type="button" onClick={createSession} disabled={loading || !projectId.trim()} className="px-4 py-2 bg-[#1A1A1A] text-white rounded text-sm disabled:opacity-50 mr-2">
        {loading ? "Creating…" : "Create session"}
      </button>
      {sessionId && (
        <>
          <p className="mt-3 text-sm text-[#666]">Session: {sessionId}</p>
          <div className="mt-3 flex gap-2">
            <input
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runCommand()}
              className="border border-gray-200 rounded px-3 py-2 text-sm flex-1 font-mono"
              placeholder="Command (e.g. dir, ls, npm run build)"
            />
            <button type="button" onClick={runCommand} disabled={execLoading} className="px-4 py-2 bg-[#1A1A1A] text-white rounded text-sm disabled:opacity-50">
              {execLoading ? "Running…" : "Run"}
            </button>
          </div>
          {output && (
            <pre className="mt-3 p-3 bg-gray-100 text-[#1A1A1A] border border-gray-200 rounded text-xs overflow-auto max-h-48">
              {output.stdout}
              {output.stderr ? `\n${output.stderr}` : ""}
              {output.returncode !== undefined && `\n[exit ${output.returncode}]`}
            </pre>
          )}
        </>
      )}
    </div>
  );
}
