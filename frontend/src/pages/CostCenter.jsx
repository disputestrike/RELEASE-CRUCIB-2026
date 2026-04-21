import React, { useEffect, useState } from "react";

const API = process.env.REACT_APP_BACKEND_URL
  ? `${process.env.REACT_APP_BACKEND_URL}/api`
  : "/api";

/**
 * CostCenter
 * Surfaces /api/cost/totals + /api/cost/pricing so users can see per-run and
 * per-model spend. Pulled in from the external audit (paid product positioning —
 * no local-model probe).
 */
export default function CostCenter() {
  const [totals, setTotals] = useState(null);
  const [pricing, setPricing] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("access_token") || "";
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const [tRes, pRes] = await Promise.all([
        fetch(`${API}/cost/totals`, { headers }),
        fetch(`${API}/cost/pricing`, { headers }),
      ]);
      if (!tRes.ok) throw new Error(`totals ${tRes.status}`);
      if (!pRes.ok) throw new Error(`pricing ${pRes.status}`);
      setTotals(await tRes.json());
      setPricing(await pRes.json());
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  return (
    <div data-testid="cost-center" style={{ padding: 24, color: "#e5e7eb" }}>
      <h1 style={{ fontSize: 24, marginBottom: 4 }}>Cost Center</h1>
      <div style={{ opacity: 0.7, marginBottom: 16 }}>
        Live cost usage across all runs. Auto-refreshes every 15s.
      </div>

      {error && (
        <div
          data-testid="cost-error"
          style={{
            padding: 12,
            background: "#3f1d1d",
            border: "1px solid #7f1d1d",
            borderRadius: 6,
            marginBottom: 12,
          }}
        >
          {error}
        </div>
      )}

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: 12,
          marginBottom: 24,
        }}
      >
        <Card label="Total runs" value={totals?.runs ?? (loading ? "..." : 0)} />
        <Card
          label="Total tokens"
          value={
            totals
              ? `${(totals.total_input_tokens || 0).toLocaleString()} in / ${(
                  totals.total_output_tokens || 0
                ).toLocaleString()} out`
              : loading
              ? "..."
              : "0"
          }
        />
        <Card
          label="Total cost"
          value={totals ? `$${Number(totals.total_usd || 0).toFixed(4)}` : loading ? "..." : "$0.0000"}
        />
      </section>

      <h2 style={{ fontSize: 18, marginBottom: 8 }}>Per-run breakdown</h2>
      <div
        style={{
          background: "#0b0f17",
          border: "1px solid #1f2937",
          borderRadius: 6,
          overflow: "hidden",
          marginBottom: 24,
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead style={{ background: "#111827" }}>
            <tr>
              <Th>Run ID</Th>
              <Th>Model</Th>
              <Th>Turns</Th>
              <Th>Input tokens</Th>
              <Th>Output tokens</Th>
              <Th>Cost (USD)</Th>
            </tr>
          </thead>
          <tbody>
            {(totals?.runs_detail || []).length === 0 && (
              <tr>
                <td colSpan={6} style={{ padding: 12, opacity: 0.6, textAlign: "center" }}>
                  No runs tracked yet.
                </td>
              </tr>
            )}
            {(totals?.runs_detail || []).map((r) => (
              <tr key={r.run_id} style={{ borderTop: "1px solid #1f2937" }}>
                <Td mono>{r.run_id}</Td>
                <Td>{r.model || "-"}</Td>
                <Td>{r.turns || 0}</Td>
                <Td>{(r.input_tokens || 0).toLocaleString()}</Td>
                <Td>{(r.output_tokens || 0).toLocaleString()}</Td>
                <Td>${Number(r.usd || 0).toFixed(4)}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 style={{ fontSize: 18, marginBottom: 8 }}>Pricing table</h2>
      <div
        style={{
          background: "#0b0f17",
          border: "1px solid #1f2937",
          borderRadius: 6,
          overflow: "hidden",
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead style={{ background: "#111827" }}>
            <tr>
              <Th>Model</Th>
              <Th>Input ($/1M)</Th>
              <Th>Output ($/1M)</Th>
            </tr>
          </thead>
          <tbody>
            {pricing &&
              Object.entries(pricing.pricing || {}).map(([model, p]) => (
                <tr key={model} style={{ borderTop: "1px solid #1f2937" }}>
                  <Td mono>{model}</Td>
                  <Td>${Number(p.input).toFixed(2)}</Td>
                  <Td>${Number(p.output).toFixed(2)}</Td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Card({ label, value }) {
  return (
    <div
      style={{
        padding: 16,
        background: "#0b0f17",
        border: "1px solid #1f2937",
        borderRadius: 6,
      }}
    >
      <div style={{ fontSize: 12, opacity: 0.65, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 600 }}>{value}</div>
    </div>
  );
}

function Th({ children }) {
  return (
    <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600, opacity: 0.8 }}>
      {children}
    </th>
  );
}

function Td({ children, mono }) {
  return (
    <td
      style={{
        padding: "8px 12px",
        fontFamily: mono ? "ui-monospace, SFMono-Regular, Menlo, monospace" : undefined,
        fontSize: mono ? 12 : undefined,
      }}
    >
      {children}
    </td>
  );
}
