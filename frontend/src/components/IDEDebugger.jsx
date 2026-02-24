import { useState } from "react";
import axios from "axios";
import { API } from "../App";
import { logApiError } from "../utils/apiError";

export default function IDEDebugger() {
  const [projectId, setProjectId] = useState("test-project");
  const [sessionId, setSessionId] = useState(null);
  const [breakpoints, setBreakpoints] = useState([]);
  const [filePath, setFilePath] = useState("src/App.js");
  const [line, setLine] = useState(1);
  const [column, setColumn] = useState(0);
  const [condition, setCondition] = useState("");
  const [loading, setLoading] = useState(false);

  const startSession = () => {
    setLoading(true);
    axios
      .post(`${API}/ide/debug/start`, null, { params: { project_id: projectId } })
      .then((r) => {
        setSessionId(r.data.session_id);
        setBreakpoints([]);
      })
      .catch((e) => logApiError("IDEDebugger start", e))
      .finally(() => setLoading(false));
  };

  const addBreakpoint = () => {
    if (!sessionId) return;
    setLoading(true);
    axios
      .post(`${API}/ide/debug/${sessionId}/breakpoint`, {
        file_path: filePath,
        line: Number(line) || 1,
        column: Number(column) || 0,
        condition: condition || undefined,
      })
      .then((r) => setBreakpoints((prev) => [...prev, { id: r.data.id, file_path: r.data.file_path, line: r.data.line, column: r.data.column, condition: r.data.condition }]))
      .catch((e) => logApiError("IDEDebugger add breakpoint", e))
      .finally(() => setLoading(false));
  };

  const removeBreakpoint = (breakpointId) => {
    if (!sessionId) return;
    axios
      .delete(`${API}/ide/debug/${sessionId}/breakpoint/${breakpointId}`)
      .then(() => setBreakpoints((prev) => prev.filter((b) => b.id !== breakpointId)))
      .catch((e) => logApiError("IDEDebugger remove breakpoint", e));
  };

  return (
    <div className="p-6 max-w-2xl">
      <h2 className="text-lg font-medium text-[#1A1A1A] mb-2">Debugger</h2>
      <p className="text-sm text-[#666] mb-4">Start a debug session and set breakpoints (backend stub — real debugger can be wired later).</p>
      <input
        type="text"
        value={projectId}
        onChange={(e) => setProjectId(e.target.value)}
        className="border border-gray-200 rounded px-3 py-2 text-sm w-full mb-2"
        placeholder="Project ID"
      />
      <button type="button" onClick={startSession} disabled={loading} className="px-4 py-2 bg-[#1A1A1A] text-white rounded text-sm disabled:opacity-50 mb-4">
        {loading ? "Starting…" : "Start debug session"}
      </button>
      {sessionId && (
        <>
          <p className="text-sm text-[#666] mb-3">Session: {sessionId}</p>
          <div className="grid grid-cols-2 gap-2 mb-2">
            <input type="text" value={filePath} onChange={(e) => setFilePath(e.target.value)} className="border border-gray-200 rounded px-3 py-2 text-sm" placeholder="File path" />
            <input type="number" value={line} onChange={(e) => setLine(e.target.value)} className="border border-gray-200 rounded px-3 py-2 text-sm" placeholder="Line" min={1} />
            <input type="number" value={column} onChange={(e) => setColumn(e.target.value)} className="border border-gray-200 rounded px-3 py-2 text-sm" placeholder="Column" min={0} />
            <input type="text" value={condition} onChange={(e) => setCondition(e.target.value)} className="border border-gray-200 rounded px-3 py-2 text-sm col-span-2" placeholder="Condition (optional)" />
          </div>
          <button type="button" onClick={addBreakpoint} disabled={loading} className="px-4 py-2 bg-[#1A1A1A] text-white rounded text-sm disabled:opacity-50 mb-3">
            Add breakpoint
          </button>
          {breakpoints.length > 0 && (
            <ul className="border border-gray-200 rounded bg-white divide-y divide-gray-100">
              {breakpoints.map((bp) => (
                <li key={bp.id} className="flex items-center justify-between px-3 py-2 text-sm">
                  <span className="text-[#1A1A1A]">{bp.file_path}:{bp.line}{bp.column ? `:${bp.column}` : ""}{bp.condition ? ` (${bp.condition})` : ""}</span>
                  <button type="button" onClick={() => removeBreakpoint(bp.id)} className="text-[#666] hover:text-[#1A1A1A] text-xs">
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
