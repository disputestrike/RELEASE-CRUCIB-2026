import React, { useMemo, useState } from 'react';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import {
  GitBranch, Play, Users, RefreshCcw, CheckCircle2, AlertCircle,
  Sparkles, ShieldCheck, Zap, DollarSign,
} from 'lucide-react';
import './WhatIfPage.css';

const PRESETS = [
  { title: 'Swap payment provider', text: 'What if we replace Stripe with LemonSqueezy in the billing flow next quarter?' },
  { title: 'Migrate off AWS', text: 'What if we migrate our production workloads from AWS to Cloudflare + Neon in the next 6 months?' },
  { title: 'Raise prices 30%', text: 'What if we raise our Pro-tier pricing by 30% and grandfather existing customers for 12 months?' },
  { title: 'Drop a feature', text: 'What if we deprecate the on-prem deployment option and refund those customers?' },
  { title: 'Change tech stack', text: 'What if we rewrite the backend from FastAPI to Rust (Axum) to improve throughput?' },
];

export default function WhatIfPage() {
  const { token } = useAuth();
  const [scenario, setScenario] = useState(PRESETS[0].text);
  const [mode, setMode] = useState('decision');
  const [population, setPopulation] = useState(48);
  const [rounds, setRounds] = useState(4);
  const [cost, setCost] = useState(0.30);
  const [security, setSecurity] = useState(0.35);
  const [speed, setSpeed] = useState(0.35);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const normalizedPriors = useMemo(() => {
    const total = cost + security + speed || 1;
    return {
      cost_sensitive: cost / total,
      security_first: security / total,
      speed_first: speed / total,
    };
  }, [cost, security, speed]);

  const runSimulation = async () => {
    const s = String(scenario || '').trim();
    if (!s) { setError('Describe a scenario to simulate.'); return; }
    setLoading(true); setError(''); setResult(null);
    try {
      const res = await fetch(`${API}/runtime/what-if`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          mode: mode,
          scenario: s,
          population_size: Math.max(3, Math.min(256, Number(population) || 48)),
          rounds: Math.max(1, Math.min(8, Number(rounds) || 4)),
          priors: normalizedPriors,
        }),
      });
      if (!res.ok) {
        const body = await res.text().catch(() => '');
        setError(`Simulation failed (HTTP ${res.status}). ${body?.slice(0, 140) || ''}`);
        return;
      }
      const payload = await res.json();
      setResult(payload);
    } catch (e) {
      setError('Simulation failed — network or server error.');
    } finally {
      setLoading(false);
    }
  };

  const updates = Array.isArray(result?.updates) ? result.updates : [];
  const lastRound = updates[updates.length - 1] || null;
  const recommendation = result?.recommendation || null;
  const consensusReached = !!result?.consensus_reached;

  return (
    <div className="whatif-page">
      <header className="whatif-hero">
        <div className="whatif-hero-icon"><GitBranch size={22} /></div>
        <div className="whatif-hero-text">
          <h1>What-If Analysis</h1>
          <p>
            Spin up a population of expert agents (architect, backend, security, UX, devops)
            and simulate how they'd debate a decision across multiple rounds. Use it for
            vendor swaps, pricing moves, architecture changes, feature cuts — anything with
            real tradeoffs before you commit engineering time.
          </p>
        </div>
      </header>

      <section className="whatif-card">
        <div className="whatif-card-head">
          <h2>Scenario</h2>
          <span className="whatif-card-sub">Describe the change you're weighing.</span>
        </div>
        <textarea
          className="whatif-textarea"
          value={scenario}
        <div style={{ marginTop: "10px", display: "flex", gap: "12px", alignItems: "center" }}>          <label style={{ fontSize: "12px", fontWeight: "600", color: "#374151" }}>Mode:</label>          <select            value={mode}            onChange={(e) => setMode(e.target.value)}            style={{              padding: "6px 10px",              borderRadius: "6px",              border: "1px solid #d1d5db",              fontSize: "12px",              fontWeight: "500",              cursor: "pointer",              backgroundColor: "#fff",              color: "#1f2937",            }}          >            <option value="decision">Decision Mode</option>            <option value="forecast">Forecast Mode</option>            <option value="market_reaction">Market Reaction Mode</option>          </select>        </div>
          onChange={(e) => setScenario(e.target.value)}
          rows={4}
          placeholder="What if we…"
        />
        <div className="whatif-presets">
          {PRESETS.map((p) => (
            <button key={p.title} type="button" className="whatif-preset" onClick={() => setScenario(p.text)}>
              <Sparkles size={12} /><span>{p.title}</span>
            </button>
          ))}
        </div>
        <div className="whatif-controls">
          <label className="whatif-control">
            <span><Users size={13} /> Agents<em>{population}</em></span>
            <input type="range" min={8} max={128} step={4} value={population}
              onChange={(e) => setPopulation(Number(e.target.value))} />
          </label>
          <label className="whatif-control">
            <span><RefreshCcw size={13} /> Rounds<em>{rounds}</em></span>
            <input type="range" min={1} max={8} step={1} value={rounds}
              onChange={(e) => setRounds(Number(e.target.value))} />
          </label>
        </div>
        <div className="whatif-priors">
          <div className="whatif-priors-head">Priors mix (normalized automatically)</div>
          <div className="whatif-prior-row">
            <span className="whatif-prior-label"><DollarSign size={12} /> Cost-sensitive</span>
            <input type="range" min={0} max={1} step={0.05} value={cost}
              onChange={(e) => setCost(Number(e.target.value))} />
            <em>{Math.round(normalizedPriors.cost_sensitive * 100)}%</em>
          </div>
          <div className="whatif-prior-row">
            <span className="whatif-prior-label"><ShieldCheck size={12} /> Security-first</span>
            <input type="range" min={0} max={1} step={0.05} value={security}
              onChange={(e) => setSecurity(Number(e.target.value))} />
            <em>{Math.round(normalizedPriors.security_first * 100)}%</em>
          </div>
          <div className="whatif-prior-row">
            <span className="whatif-prior-label"><Zap size={12} /> Speed-first</span>
            <input type="range" min={0} max={1} step={0.05} value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))} />
            <em>{Math.round(normalizedPriors.speed_first * 100)}%</em>
          </div>
        </div>
        <div className="whatif-actions">
          <button type="button" className="whatif-run" onClick={runSimulation} disabled={loading}>
            <Play size={14} />
            {loading ? 'Running simulation…' : 'Run simulation'}
          </button>
          {error && (<span className="whatif-error"><AlertCircle size={13} /> {error}</span>)}
        </div>
      </section>

      {recommendation && (
        <section className="whatif-card whatif-reco">
          <div className="whatif-reco-head">
            <div className="whatif-reco-badge">
              {consensusReached ? <CheckCircle2 size={14} /> : <GitBranch size={14} />}
              {consensusReached ? 'Consensus reached' : 'Debate still open'}
            </div>
            <div className="whatif-reco-confidence">
              Confidence: <strong>{Math.round((recommendation.confidence || 0) * 100)}%</strong>
              {recommendation.evidence_quality && (
                <span className="ml-2 text-xs opacity-70">
                  (Evidence: {recommendation.evidence_quality})
                </span>
              )}
            </div>
          </div>
          <div className="whatif-reco-title">Recommended action</div>
          <p className="whatif-reco-text">{recommendation.recommended_action}</p>
          {recommendation.uncertainty && (
            <div className="mb-3 p-2 bg-yellow-50 border border-yellow-100 rounded text-xs text-yellow-800">
              <strong>Uncertainty:</strong> {recommendation.uncertainty}
            </div>
          )}
          {Array.isArray(recommendation.data_sources) && recommendation.data_sources.length > 0 && (
            <div className="mb-3 text-xs text-gray-500">
              <strong>Data Sources:</strong> {recommendation.data_sources.join(', ')}
            </div>
          )}
          {Array.isArray(recommendation.tradeoffs) && recommendation.tradeoffs.length > 0 && (
            <div className="whatif-reco-tradeoffs">
              <div className="whatif-reco-tradeoffs-label">Key arguments</div>
              <ul>
                {recommendation.tradeoffs.slice(0, 5).map((t, i) => (<li key={`t-${i}`}>{t}</li>))}
              </ul>
            </div>
          )}
        </section>
      )}

      {lastRound && (
        <section className="whatif-card">
          <div className="whatif-card-head">
            <h2>Final round clustering</h2>
            <span className="whatif-card-sub">
              Round {lastRound.round} of {result.rounds_executed} · {result.population_size} agents
            </span>
          </div>
          <div className="whatif-clusters">
            {(lastRound.clusters || []).map((c) => {
              const pct = result.population_size
                ? Math.round((Number(c.size) / result.population_size) * 100) : 0;
              return (
                <div key={c.id} className="whatif-cluster">
                  <div className="whatif-cluster-head">
                    <strong>{c.id.replace('cluster_', 'Cluster ').toUpperCase()}</strong>
                    <span>{c.size} agents · {pct}%</span>
                  </div>
                  <div className="whatif-cluster-bar">
                    <div className="whatif-cluster-fill" style={{ width: `${pct}%` }} />
                  </div>
                  <div className="whatif-cluster-position">{c.position}</div>
                  {Array.isArray(c.key_arguments) && c.key_arguments.length > 0 && (
                    <ul className="whatif-cluster-args">
                      {c.key_arguments.slice(0, 3).map((a, i) => (<li key={`${c.id}-${i}`}>{a}</li>))}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {updates.length > 1 && (
        <section className="whatif-card">
          <div className="whatif-card-head">
            <h2>Round-by-round evolution</h2>
            <span className="whatif-card-sub">
              How agent clusters shifted across {updates.length} rounds of debate.
            </span>
          </div>
          <div className="whatif-timeline">
            {updates.map((u) => (
              <div key={`r-${u.round}`} className="whatif-timeline-row">
                <div className="whatif-timeline-label">R{u.round}</div>
                <div className="whatif-timeline-track">
                  {(u.clusters || []).map((c) => {
                    const pct = result.population_size
                      ? (Number(c.size) / result.population_size) * 100 : 0;
                    const color =
                      c.id === 'cluster_a' ? '#059669'
                      : c.id === 'cluster_b' ? '#10b981'
                      : '#9ca3af';
                    return (
                      <div key={`${u.round}-${c.id}`} className="whatif-timeline-seg"
                        style={{ width: `${pct}%`, background: color }}
                        title={`${c.id}: ${c.size} agents`} />
                    );
                  })}
                </div>
                <div className="whatif-timeline-state">
                  {u.consensus_emerging ? 'consensus' : 'contested'}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {!result && !loading && (
        <section className="whatif-empty">
          <GitBranch size={18} />
          <div>
            <strong>Run a simulation to see results.</strong>
            <p>Pick a preset or describe your own scenario, tune the priors for how your team
              actually thinks, then hit <em>Run simulation</em>.</p>
          </div>
        </section>
      )}
    </div>
  );
}
