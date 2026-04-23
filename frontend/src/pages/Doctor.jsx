import React, { useEffect, useState } from "react";

const API = process.env.REACT_APP_BACKEND_URL
  ? `${process.env.REACT_APP_BACKEND_URL}/api`
  : "/api";

/**
 * Doctor
 * Diagnostic page - runs GET /api/doctor and renders system checks (python/node/
 * git, env vars, etc). Matches the developer UX of `gh auth status` or
 * `goose doctor` from the audit.
 */
export default function Doctor() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("access_token") || "";
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(`${API}/doctor`, { headers });
      if (!res.ok) throw new Error(`doctor ${res.status}`);
      setData(await res.json());
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    run();
  }, []);

  const checks = data?.checks || [];
  const okCount = checks.filter((c) => c.status === "ok").length;
  const warnCount = checks.filter((c) => c.status === "warn").length;
  const failCount = checks.filter((c) => c.status === "fail").length;

  return (
    <div data-testid="doctor-page" style={{ padding: 24, color: "var(--theme-text)" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 8,
        }}
      >
        <h1 style={{ fontSize: 24 }}>Doctor</h1>
        <button
          data-testid="doctor-rerun"
          onClick={run}
          disabled={loading}
          style={{
            padding: "6px 12px",
            background: "var(--theme-accent)",
            border: "1px solid #2563eb",
            borderRadius: 4,
            color: "white",
            cursor: loading ? "wait" : "pointer",
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "Running..." : "Re-run"}
        </button>
      </div>
      <div style={{ opacity: 0.7, marginBottom: 16 }}>
        System diagnostics for CrucibAI. Surfaces missing env vars, version
        mismatches and service health before a run fails.
      </div>

      {error && (
        <div
          data-testid="doctor-error"
          style={{
            padding: 12,
            background: "var(--theme-surface2)",
            border: "1px solid #ef4444",
            borderRadius: 6,
            marginBottom: 12,
          }}
        >
          {error}
        </div>
      )}

      {data && (
        <section
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
            gap: 12,
            marginBottom: 20,
          }}
        >
          <Card label="OK" value={okCount} color="#10b981" />
          <Card label="Warn" value={warnCount} color="#f59e0b" />
          <Card label="Fail" value={failCount} color="#ef4444" />
        </section>
      )}

      <div
        style={{
          background: "var(--theme-surface)",
          border: "1px solid var(--theme-border)",
          borderRadius: 6,
          overflow: "hidden",
        }}
      >
        {checks.length === 0 && (
          <div style={{ padding: 16, opacity: 0.6, textAlign: "center" }}>
            {loading ? "Running diagnostics..." : "No checks returned."}
          </div>
        )}
        {checks.map((c, i) => (
          <div
            key={`${c.name}-${i}`}
            data-testid={`doctor-check-${c.name}`}
            style={{
              display: "grid",
              gridTemplateColumns: "100px 220px 1fr",
              alignItems: "center",
              padding: "10px 12px",
              borderTop: i === 0 ? "none" : "1px solid var(--theme-border)",
              gap: 12,
            }}
          >
            <Badge status={c.status} />
            <div style={{ fontFamily: "ui-monospace, monospace", fontSize: 13 }}>
              {c.name}
            </div>
            <div style={{ fontSize: 13, opacity: 0.85 }}>{c.detail || c.message || ""}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Card({ label, value, color }) {
  return (
    <div
      style={{
        padding: 16,
        background: "var(--theme-surface)",
        border: `1px solid ${color || "var(--theme-border)"}`,
        borderRadius: 6,
      }}
    >
      <div style={{ fontSize: 12, opacity: 0.65, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

function Badge({ status }) {
  const map = {
    ok: { bg: "#064e3b", fg: "#6ee7b7", label: "OK" },
    warn: { bg: "#78350f", fg: "#fbbf24", label: "WARN" },
    fail: { bg: "#ef4444", fg: "#fca5a5", label: "FAIL" },
  };
  const s = map[status] || { bg: "var(--theme-border)", fg: "#cbd5e1", label: status || "?" };
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 4,
        background: s.bg,
        color: s.fg,
        fontSize: 12,
        fontWeight: 600,
        textAlign: "center",
      }}
    >
      {s.label}
    </span>
  );
}
