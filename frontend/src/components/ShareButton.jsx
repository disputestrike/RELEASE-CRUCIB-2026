// WS-J: creates a share link from the current project snapshot.
import React, { useState } from "react";

export default function ShareButton({ projectId, title, snapshot, apiBase = "" }) {
  const [url, setUrl] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  async function share() {
    setBusy(true);
    setErr(null);
    try {
      const r = await fetch(`${apiBase}/api/share`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId, title: title || "", snapshot: snapshot || {} }),
      });
      if (!r.ok) throw new Error(`status ${r.status}`);
      const j = await r.json();
      const full = `${window.location.origin}${j.url_path}`;
      setUrl(full);
      try { await navigator.clipboard.writeText(full); } catch (_) {}
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
      <button onClick={share} disabled={busy || !projectId}>
        {busy ? "Creating…" : "Share"}
      </button>
      {url && <a href={url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12 }}>{url} (copied)</a>}
      {err && <span style={{ color: "#f88", fontSize: 12 }}>{err}</span>}
    </div>
  );
}
