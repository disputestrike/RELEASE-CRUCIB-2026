/**
 * Real-time build progress: WebSocket or polling for current_phase, progress_percent, tokens_used.
 * Used in AgentMonitor when project status is "running".
 */
import { useState, useEffect, useRef } from "react";

const PARALLEL_PHASES = [
  ["Planner"],
  ["Requirements Clarifier", "Stack Selector"],
  ["Frontend Generation", "Backend Generation", "Database Agent", "API Integration", "Test Generation", "Image Generation"],
  ["Video Generation", "Security Checker", "Test Executor", "UX Auditor", "Performance Analyzer"],
  ["Deployment Agent", "Error Recovery", "Memory Agent"],
  ["PDF Export", "Excel Export", "Markdown Export", "Scraping Agent", "Automation Agent"],
];

export default function BuildProgress({ projectId, apiBaseUrl }) {
  const [phase, setPhase] = useState(0);
  const [agent, setAgent] = useState("");
  const [status, setStatus] = useState("");
  const [progress, setProgress] = useState(0);
  const [tokensUsed, setTokensUsed] = useState(0);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!projectId || !apiBaseUrl) return;
    const wsUrl = (apiBaseUrl || "").replace(/^http/, "ws") + `/ws/projects/${projectId}/progress`;
    let closed = false;
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setPhase(data.phase ?? 0);
          setAgent(data.agent ?? "");
          setStatus(data.status ?? "");
          setProgress(data.progress ?? 0);
          setTokensUsed(data.tokens_used ?? 0);
        } catch (_) {}
      };
      ws.onclose = () => { if (!closed) setStatus("completed"); };
      return () => {
        closed = true;
        try { ws.close(); } catch (_) {}
      };
    } catch (_) {
      // Fallback: poll every 2s
      const interval = setInterval(async () => {
        try {
          const base = apiBaseUrl.replace(/\/$/, "");
          const r = await fetch(`${base}/api/projects/${projectId}`, { credentials: "include", headers: { Authorization: `Bearer ${localStorage.getItem("token")}` } });
          const p = await r.json();
          if (p.project) {
            setPhase(p.project.current_phase ?? 0);
            setAgent(p.project.current_agent ?? "");
            setStatus(p.project.status ?? "");
            setProgress(p.project.progress_percent ?? 0);
            setTokensUsed(p.project.tokens_used ?? 0);
            if (p.project.status === "completed" || p.project.status === "failed") clearInterval(interval);
          }
        } catch (_) {}
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [projectId, apiBaseUrl]);

  return (
    <div className="space-y-4 rounded-xl border border-gray-800 bg-gray-900/50 p-4">
      <h2 className="text-lg font-semibold">Building your app...</h2>
      <div className="space-y-2">
        {PARALLEL_PHASES.map((agents, idx) => (
          <div
            key={idx}
            className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${
              idx < phase ? "bg-gray-500/10 text-gray-400" : idx === phase ? "bg-gray-200/10 text-#c0c0c0" : "bg-gray-800/50 text-gray-500"
            }`}
          >
            <span className="font-medium">Phase {idx + 1}:</span>
            <span>{agents.join(", ")}</span>
            {idx < phase && <span className="ml-auto">✓</span>}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-4 text-sm text-gray-400">
        <span>Progress: {progress}%</span>
        <span>Tokens used: {tokensUsed.toLocaleString()}</span>
      </div>
    </div>
  );
}
