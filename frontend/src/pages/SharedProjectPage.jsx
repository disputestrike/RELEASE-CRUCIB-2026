// WS-J: public, anonymous-viewable shared project at /p/:slug
import React, { useEffect, useState } from "react";

export default function SharedProjectPage({ slug, apiBase = "" }) {
  const [share, setShare] = useState(null);
  const [error, setError] = useState(null);
  const [remixing, setRemixing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`${apiBase}/api/share/${encodeURIComponent(slug)}`);
        if (!r.ok) throw new Error(`status ${r.status}`);
        const j = await r.json();
        if (!cancelled) setShare(j);
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    })();
    return () => { cancelled = true; };
  }, [apiBase, slug]);

  async function remix() {
    setRemixing(true);
    try {
      const r = await fetch(`${apiBase}/api/share/${encodeURIComponent(slug)}/remix`, { method: "POST" });
      if (!r.ok) throw new Error(`remix failed: ${r.status}`);
      const j = await r.json();
      // Caller is free to redirect; shipping the minimal contract here.
      window.location.href = `/projects/${encodeURIComponent(j.new_project_id)}`;
    } catch (e) {
      setError(String(e));
      setRemixing(false);
    }
  }

  if (error) return <div style={{ padding: 24, color: "#f88" }}>Error: {error}</div>;
  if (!share) return <div style={{ padding: 24 }}>Loading shared project…</div>;

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ margin: 0 }}>{share.title || "Shared project"}</h1>
        <button onClick={remix} disabled={remixing}>{remixing ? "Remixing…" : "Remix"}</button>
      </div>
      <div style={{ opacity: 0.6, fontSize: 12, marginTop: 4 }}>
        slug: {share.slug} · views: {share.views} · remixes: {share.remixes}
      </div>
      <pre style={{ background: "#111", color: "#ddd", padding: 12, borderRadius: 6, marginTop: 16, overflow: "auto" }}>
{JSON.stringify(share.snapshot, null, 2)}
      </pre>
    </div>
  );
}
