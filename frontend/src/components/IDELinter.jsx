import { useState } from "react";
import axios from "axios";
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import { logApiError } from "../utils/apiError";

export default function IDELinter() {
  const { token } = useAuth();
  const [projectId, setProjectId] = useState("");
  const [filePath, setFilePath] = useState("");
  const [code, setCode] = useState("");
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(false);

  const runLint = () => {
    setLoading(true);
    const params = { project_id: projectId };
    if (filePath) params.file_path = filePath;
    if (code) params.code = code.slice(0, 4000);
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    axios
      .post(`${API}/ide/lint`, null, { params, headers })
      .then((r) => setIssues(r.data.issues || []))
      .catch((e) => {
        logApiError("IDELinter", e);
        setIssues([]);
      })
      .finally(() => setLoading(false));
  };

  return (
    <div className="p-6 max-w-2xl">
      <h2 className="text-lg font-medium text-[#1A1A1A] mb-2">Linter</h2>
      <p className="text-sm text-[#666] mb-4">Run lint for a project or paste code (backend stub — returns empty until real linter is wired).</p>
      <input
        type="text"
        value={projectId}
        onChange={(e) => setProjectId(e.target.value)}
        className="border border-gray-200 rounded px-3 py-2 text-sm w-full mb-2"
        placeholder="Project ID"
      />
      <input
        type="text"
        value={filePath}
        onChange={(e) => setFilePath(e.target.value)}
        className="border border-gray-200 rounded px-3 py-2 text-sm w-full mb-2"
        placeholder="File path (optional)"
      />
      <textarea
        value={code}
        onChange={(e) => setCode(e.target.value)}
        className="border border-gray-200 rounded px-3 py-2 text-sm w-full mb-2 font-mono min-h-[80px]"
        placeholder="Or paste code to lint (optional)"
      />
      <button type="button" onClick={runLint} disabled={loading || !projectId.trim()} className="px-4 py-2 bg-[#1A1A1A] text-white rounded text-sm disabled:opacity-50 mb-4">
        {loading ? "Running…" : "Run lint"}
      </button>
      {issues.length > 0 ? (
        <ul className="border border-gray-200 rounded bg-white divide-y divide-gray-100">
          {issues.map((issue, i) => (
            <li key={i} className="px-3 py-2 text-sm">
              <span className={`font-medium ${issue.severity === "error" ? "text-red-600" : issue.severity === "warning" ? "text-neutral-600" : "text-[#666]"}`}>{issue.severity}</span>{" "}
              {issue.file_path && `${issue.file_path}:`}{issue.line}:{issue.column} — {issue.message}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-[#666]">No issues reported. Run lint to check.</p>
      )}
    </div>
  );
}
