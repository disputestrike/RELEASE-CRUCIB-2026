// WS-L: ThinkingStream — renders ReAct events with a thinking-budget progress bar.

import React from "react";

export default function ThinkingStream({ events = [], budget = { used: 0, total: 8000 } }) {
  const pct = Math.min(100, Math.round(((budget.used || 0) / (budget.total || 1)) * 100));
  return (
    <div className="thinking-stream" style={{ border: "1px solid #2a2a33", padding: 8, borderRadius: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, opacity: 0.75 }}>
        <span>Thinking budget</span>
        <span>{budget.used || 0} / {budget.total || 0}</span>
      </div>
      <div style={{ height: 4, background: "#1a1a20", borderRadius: 2, overflow: "hidden", marginTop: 4 }}>
        <div style={{ height: "100%", width: `${pct}%`, background: pct > 80 ? "#e06c3a" : "#5a8df0", transition: "width 200ms" }} />
      </div>
      <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
        {events.map((e, i) => (
          <EventRow key={i} event={e} />
        ))}
      </div>
    </div>
  );
}

function EventRow({ event }) {
  const common = { padding: 6, borderRadius: 4, fontSize: 13 };
  switch (event.type) {
    case "thought":
      return (
        <div style={{ ...common, background: "#1a1a24", color: "#c8c8d0", fontStyle: "italic" }}>
          💭 {event.content}
        </div>
      );
    case "tool_call":
      return (
        <div style={{ ...common, background: "#1a2230", color: "#8fb8ff" }}>
          🔧 {event.name}({JSON.stringify(event.args)})
        </div>
      );
    case "tool_result":
      return (
        <div style={{ ...common, background: event.ok ? "#1a2a1a" : "#2a1a1a", color: event.ok ? "#8ce08c" : "#ff8c8c" }}>
          {event.ok ? "✓" : "✗"} result: {safeStringify(event.result)}
        </div>
      );
    case "text":
      return <div style={{ ...common, background: "#222", color: "#eee" }}>{event.content}</div>;
    case "final":
      return (
        <div style={{ ...common, background: "#1b2a1b", color: "#c0f0c0" }}>
          ● final ({event.steps} steps, {event.elapsed_ms}ms): {event.content}
        </div>
      );
    default:
      return null;
  }
}

function safeStringify(v) {
  try {
    const s = typeof v === "string" ? v : JSON.stringify(v);
    return s.length > 240 ? s.slice(0, 240) + "…" : s;
  } catch {
    return String(v);
  }
}
