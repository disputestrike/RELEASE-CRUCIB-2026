import { useState } from "react";
import axios from "axios";
import { useAuth } from '../App';
import { API_BASE as API } from '../apiBase';
import { logApiError } from "../utils/apiError";

export default function IDEGit() {
  const { token } = useAuth();
  const [projectId, setProjectId] = useState("");
  const [status, setStatus] = useState(null);
  const [branches, setBranches] = useState([]);
  const [mergeBranch, setMergeBranch] = useState("");
  const [commitMessage, setCommitMessage] = useState("");
  const [resolveFilePath, setResolveFilePath] = useState("");
  const [resolveChoice, setResolveChoice] = useState("ours");
  const [loading, setLoading] = useState(false);
  const [branchLoading, setBranchLoading] = useState(false);
  const [mergeLoading, setMergeLoading] = useState(false);
  const [commitLoading, setCommitLoading] = useState(false);
  const [resolveLoading, setResolveLoading] = useState(false);

  const params = () => ({ project_id: projectId });
  const authConfig = () => ({ params: params(), headers: token ? { Authorization: `Bearer ${token}` } : {} });

  const fetchStatus = () => {
    setLoading(true);
    axios
      .get(`${API}/git/status`, authConfig())
      .then((r) => setStatus(r.data))
      .catch((e) => logApiError("IDEGit status", e))
      .finally(() => setLoading(false));
  };

  const fetchBranches = () => {
    setBranchLoading(true);
    axios
      .get(`${API}/git/branches`, authConfig())
      .then((r) => setBranches(r.data.branches || []))
      .catch((e) => {
        logApiError("IDEGit branches", e);
        setBranches([]);
      })
      .finally(() => setBranchLoading(false));
  };

  const doMerge = () => {
    if (!mergeBranch) return;
    setMergeLoading(true);
    axios
      .post(`${API}/git/merge`, null, { params: { ...params(), branch: mergeBranch }, headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => {
        if (r.data.status === "ok") fetchStatus();
      })
      .catch((e) => logApiError("IDEGit merge", e))
      .finally(() => setMergeLoading(false));
  };

  const doCommit = () => {
    if (!commitMessage.trim()) return;
    setCommitLoading(true);
    axios
      .post(`${API}/git/commit`, { message: commitMessage.trim() }, authConfig())
      .then((r) => {
        if (r.data.status === "ok") fetchStatus();
      })
      .catch((e) => logApiError("IDEGit commit", e))
      .finally(() => setCommitLoading(false));
  };

  const doResolve = () => {
    if (!resolveFilePath.trim()) return;
    setResolveLoading(true);
    axios
      .post(`${API}/git/resolve-conflict`, { file_path: resolveFilePath.trim(), resolution: resolveChoice }, authConfig())
      .then((r) => {
        if (r.data.status === "ok") fetchStatus();
      })
      .catch((e) => logApiError("IDEGit resolve", e))
      .finally(() => setResolveLoading(false));
  };

  return (
    <div className="p-6 max-w-2xl">
      <h2 className="text-lg font-medium text-[#1A1A1A] mb-2">Git</h2>
      <p className="text-sm text-[#666] mb-4">Repository status, branches, merge, commit, and resolve conflicts for your authenticated project workspace.</p>
      <input
        type="text"
        value={projectId}
        onChange={(e) => setProjectId(e.target.value)}
        className="border border-gray-200 rounded px-3 py-2 text-sm w-full mb-2"
        placeholder="Project ID"
      />
      <button type="button" onClick={fetchStatus} disabled={loading || !projectId.trim()} className="px-4 py-2 bg-[#1A1A1A] text-white rounded text-sm disabled:opacity-50 mr-2 mb-2">
        {loading ? "Loading…" : "Get status"}
      </button>
      <button type="button" onClick={fetchBranches} disabled={branchLoading || !projectId.trim()} className="px-4 py-2 border border-gray-300 text-[#1A1A1A] rounded text-sm disabled:opacity-50 mb-2">
        {branchLoading ? "Loading…" : "List branches"}
      </button>
      {status && (
        <div className="mt-3 p-3 border border-gray-200 rounded bg-white text-sm">
          <p><strong>Branch:</strong> {status.branch}</p>
          <p>Modified: {status.modified?.length ?? 0}, Staged: {status.staged?.length ?? 0}, Untracked: {status.untracked?.length ?? 0}</p>
          {status.conflicted?.length > 0 && <p className="text-neutral-600">Conflicted: {status.conflicted.join(", ")}</p>}
          {status.error && <p className="text-red-600">{status.error}</p>}
        </div>
      )}
      {branches.length > 0 && (
        <div className="mt-3 p-3 border border-gray-200 rounded bg-white">
          <p className="text-sm font-medium text-[#1A1A1A] mb-2">Branches</p>
          <ul className="text-sm text-[#666] mb-2 max-h-24 overflow-auto">{branches.map((b) => <li key={b}>{b}</li>)}</ul>
          <div className="flex gap-2">
            <select value={mergeBranch} onChange={(e) => setMergeBranch(e.target.value)} className="border border-gray-200 rounded px-3 py-2 text-sm flex-1">
              <option value="">Merge branch…</option>
              {branches.filter((b) => b !== status?.branch).map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
            <button type="button" onClick={doMerge} disabled={!mergeBranch || mergeLoading} className="px-4 py-2 bg-[#1A1A1A] text-white rounded text-sm disabled:opacity-50">
              {mergeLoading ? "Merging…" : "Merge"}
            </button>
          </div>
        </div>
      )}
      <div className="mt-3">
        <p className="text-sm font-medium text-[#1A1A1A] mb-1">Commit</p>
        <input
          type="text"
          value={commitMessage}
          onChange={(e) => setCommitMessage(e.target.value)}
          className="border border-gray-200 rounded px-3 py-2 text-sm w-full mb-2"
          placeholder="Commit message"
        />
        <button type="button" onClick={doCommit} disabled={!commitMessage.trim() || commitLoading} className="px-4 py-2 bg-[#1A1A1A] text-white rounded text-sm disabled:opacity-50">
          {commitLoading ? "Committing…" : "Commit"}
        </button>
      </div>
      {(status?.conflicted?.length > 0) && (
        <div className="mt-3 p-3 border border-gray-200 rounded bg-white">
          <p className="text-sm font-medium text-[#1A1A1A] mb-2">Resolve conflict</p>
          <input
            type="text"
            value={resolveFilePath}
            onChange={(e) => setResolveFilePath(e.target.value)}
            className="border border-gray-200 rounded px-3 py-2 text-sm w-full mb-2"
            placeholder="File path (e.g. src/App.js)"
          />
          <select value={resolveChoice} onChange={(e) => setResolveChoice(e.target.value)} className="border border-gray-200 rounded px-3 py-2 text-sm mb-2 mr-2">
            <option value="ours">Keep ours</option>
            <option value="theirs">Keep theirs</option>
          </select>
          <button type="button" onClick={doResolve} disabled={!resolveFilePath.trim() || resolveLoading} className="px-4 py-2 border border-gray-300 text-[#1A1A1A] rounded text-sm disabled:opacity-50">
            {resolveLoading ? "Resolving…" : "Resolve"}
          </button>
        </div>
      )}
    </div>
  );
}
