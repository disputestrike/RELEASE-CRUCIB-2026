// WS-B: ChatStream — consumes /api/chat/react SSE and renders events live.
// Feature-gated via localStorage.react_chat === '1'.

import React, { useEffect, useRef, useState } from "react";
import ThinkingStream from "./ThinkingStream";

export function isReactChatEnabled() {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem("react_chat") === "1";
  } catch (_) {
    return false;
  }
}

export default function ChatStream({ apiBase = "", onFinal }) {
  const [prompt, setPrompt] = useState("");
  const [events, setEvents] = useState([]);
  const [busy, setBusy] = useState(false);
  const [budget, setBudget] = useState({ used: 0, total: 8000 });
  const abortRef = useRef(null);

  if (!isReactChatEnabled()) return null;

  async function send() {
    if (!prompt.trim() || busy) return;
    setBusy(true);
    setEvents([]);
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const resp = await fetch(`${apiBase}/api/chat/react`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, thinking_budget: 8000, max_steps: 6 }),
        signal: controller.signal,
      });
      if (!resp.ok || !resp.body) {
        setEvents((prev) => [...prev, { type: "text", content: `error ${resp.status}` }]);
        setBusy(false);
        return;
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let carry = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        carry += decoder.decode(value, { stream: true });
        const frames = carry.split("\n\n");
        carry = frames.pop() || "";
        for (const frame of frames) {
          const line = frame.trim();
          if (!line.startsWith("data:")) continue;
          const payload = line.slice(5).trim();
          if (!payload) continue;
          try {
            const evt = JSON.parse(payload);
            setEvents((prev) => [...prev, evt]);
            if (evt.type === "final") {
              setBudget({ used: evt.tokens_used || 0, total: evt.budget || 8000 });
              if (typeof onFinal === "function") onFinal(evt);
            }
          } catch (_) {
            // skip malformed frame
          }
        }
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        setEvents((prev) => [...prev, { type: "text", content: String(err) }]);
      }
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  function cancel() {
    if (abortRef.current) abortRef.current.abort();
  }

  return (
    <div className="chat-stream" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <ThinkingStream events={events} budget={budget} />
      <div style={{ display: "flex", gap: 8 }}>
        <input
          style={{ flex: 1, padding: 6 }}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Ask with reasoning…"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          disabled={busy}
        />
        {busy ? (
          <button onClick={cancel}>Stop</button>
        ) : (
          <button onClick={send}>Send</button>
        )}
      </div>
    </div>
  );
}
