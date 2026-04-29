import React, { useMemo, useRef, useState, useEffect, useCallback } from 'react';
import {
  Activity,
  AlertTriangle,
  Brain,
  CheckCircle2,
  FileText,
  GitBranch,
  Loader2,
  MessageSquare,
  Play,
  RadioTower,
  RefreshCw,
  Search,
  ShieldCheck,
  Telescope,
  Zap,
  Users,
} from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import { useTaskStore } from '../stores/useTaskStore';
import VoiceInput from '../components/VoiceInput';
import { hydrateSimulationDetail } from './whatIfHydrate';
import './WhatIfPage.css';

const VERDICT_STYLE_LABELS = {
  probability_interval: 'Calibrated probability interval',
  risk_reward_interval: 'Risk / reward interval',
  yes_no_unclear: 'Yes / no / unclear',
  go_no_go_with_prerequisites: 'Go / no-go with prerequisites',
  recommendation_with_expected_impact: 'Recommendation with expected impact',
  reaction_segments: 'Reaction segments',
  uncertainty_first: 'Uncertainty-first framing',
};

const PROMPTS = [
  'Will the Lakers win the NBA championship?',
  'Should we raise prices by 30% next quarter?',
  'What happens if Nigeria bans crypto?',
  'Should we migrate off AWS?',
  'Will customers hate this redesign?',
];

function pct(value) {
  const n = Number(value || 0);
  return `${Math.round(n * 100)}%`;
}

/** Coerce heterogeneous API list items to display text — never render a plain object in JSX (#31). */
function simDisplayLine(raw) {
  if (raw == null) return '';
  if (typeof raw === 'string' || typeof raw === 'number' || typeof raw === 'boolean') {
    return String(raw);
  }
  if (typeof raw === 'object') {
    return (
      raw.claim_text ||
      raw.issue ||
      raw.detail ||
      raw.text ||
      raw.label ||
      raw.description ||
      (raw.supports_or_refutes && (raw.claim_text || raw.evidence_id)
        ? `${raw.supports_or_refutes}: ${raw.claim_text || raw.evidence_id}`
        : null) ||
      JSON.stringify(raw)
    );
  }
  return String(raw);
}

/** Stable React key when list items may be objects (keys must not be [object Object]). */
function simLineKey(prefix, raw, idx) {
  const idPart =
    raw != null && typeof raw === 'object' && typeof raw.id === 'string' && raw.id ? raw.id : null;
  return idPart ? `${prefix}-${idPart}` : `${prefix}-${idx}-${simDisplayLine(raw).slice(0, 64)}`;
}

function stringifyAside(raw) {
  if (raw == null) return '';
  if (typeof raw === 'string' || typeof raw === 'number' || typeof raw === 'boolean') {
    return String(raw);
  }
  if (typeof raw === 'object') {
    return simDisplayLine(raw);
  }
  return String(raw);
}

async function readJsonResponse(response, label) {
  const contentType = response.headers.get('content-type') || '';
  const body = await response.text();
  const preview = body.slice(0, 180).replace(/\s+/g, ' ').trim();

  if (!response.ok) {
    throw new Error(`${label} failed (${response.status}). ${preview}`);
  }
  if (!contentType.toLowerCase().includes('application/json')) {
    throw new Error(`${label} returned ${contentType || 'non-JSON'} instead of JSON. ${preview}`);
  }
  try {
    return JSON.parse(body);
  } catch (err) {
    throw new Error(`${label} returned invalid JSON. ${preview}`);
  }
}

const SIM_ACTIVITY_KEY = 'crucibai_simulation_activity_strip';

function readActivityStrip() {
  try {
    const raw = JSON.parse(sessionStorage.getItem(SIM_ACTIVITY_KEY) || '[]');
    return Array.isArray(raw) ? raw : [];
  } catch {
    return [];
  }
}

function pushSimulationActivity(entry) {
  try {
    const next = [{ ...entry, ts: Date.now() }, ...readActivityStrip()].slice(0, 16);
    sessionStorage.setItem(SIM_ACTIVITY_KEY, JSON.stringify(next));
    return next;
  } catch {
    return readActivityStrip();
  }
}

function seededRandom(seedStr) {
  let h = 2166136261;
  const s = String(seedStr || 'x');
  for (let i = 0; i < s.length; i += 1) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return () => {
    h ^= h >>> 13;
    h = Math.imul(h, 1274126177);
    return ((h ^ (h >>> 15)) >>> 0) / 4294967296;
  };
}

const STANCE_COLORS = ['#16a34a', '#dc2626', '#ca8a04', '#64748b', '#7c3aed', '#0891b2'];

function PopulationDotsCanvas({ clusters, seedKey }) {
  const ref = useRef(null);
  const dots = useMemo(() => {
    if (!clusters || !clusters.length) return [];
    const out = [];
    const totalDots = Math.min(2000, Math.max(240, clusters.length * 260));
    let assigned = 0;
    clusters.forEach((c, ci) => {
      const share = Math.max(0.02, Number(c.share ?? 0.1));
      const count = Math.max(24, Math.floor(totalDots * share));
      const rnd = seededRandom(`${seedKey || 's'}_${ci}_${c.label}`);
      const col = STANCE_COLORS[ci % STANCE_COLORS.length];
      for (let j = 0; j < count && assigned < totalDots; j += 1) {
        out.push({ x: rnd() * 100, y: rnd() * 100, col });
        assigned += 1;
      }
    });
    return out.slice(0, totalDots);
  }, [clusters, seedKey]);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas || !dots.length) return undefined;
    const ctx = canvas.getContext('2d');
    if (!ctx) return undefined;
    const w = canvas.width;
    const h = canvas.height;
    let raf = 0;
    let t = 0;
    const loop = () => {
      t += 0.01;
      ctx.fillStyle = '#f8fafc';
      ctx.fillRect(0, 0, w, h);
      dots.forEach((d, ji) => {
        const sway = Math.sin(t + ji * 0.04) * 0.95;
        const swayY = Math.cos(t * 0.93 + ji * 0.035) * 0.85;
        const nx = Math.max(0, Math.min(100, d.x + sway));
        const ny = Math.max(0, Math.min(100, d.y + swayY));
        ctx.beginPath();
        ctx.fillStyle = d.col;
        ctx.globalAlpha = 0.85;
        ctx.arc((nx / 100) * w, (ny / 100) * h, 2.1, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [dots]);

  return <canvas ref={ref} width={720} height={300} className="sim-live-world-canvas" role="img" aria-label="Sample population stance visualization" />;
}

function Panel({ title, icon, children, aside }) {
  const Icon = icon || Activity;
  return (
    <section className="sim-panel">
      <div className="sim-panel-head">
        <div className="sim-panel-title"><Icon size={15} /> {title}</div>
        {aside && <div className="sim-panel-aside">{aside}</div>}
      </div>
      {children}
    </section>
  );
}

export default function WhatIfPage() {
  const { token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const { upsertTask } = useTaskStore();
  const [prompt, setPrompt] = useState(PROMPTS[0]);
  const [assumptionsText, setAssumptionsText] = useState('');
  const [depth, setDepth] = useState('balanced');
  const [requireLiveRetrievalSuccess, setRequireLiveRetrievalSuccess] = useState(() => {
    try {
      return typeof window !== 'undefined' && window.localStorage.getItem('crucib_require_live_retrieval') === '1';
    } catch {
      return false;
    }
  });
  const [attachments, setAttachments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [hydrating, setHydrating] = useState(false);
  const [activityStrip, setActivityStrip] = useState(() => readActivityStrip());
  const loadedFromUrlRef = useRef('');

  const assumptions = useMemo(
    () => assumptionsText.split('\n').map((row) => row.trim()).filter(Boolean),
    [assumptionsText],
  );

  const persistCompletedRun = useCallback(
    (payload, cleanPrompt) => {
      const simId = payload?.simulation?.id || payload?.run?.simulation_id;
      const runId = payload?.run?.id;
      if (!simId || !runId) return;
      const taskId = `sim_${simId}_${runId}`;
      upsertTask({
        id: taskId,
        name: cleanPrompt.slice(0, 120) || 'Simulation',
        prompt: cleanPrompt,
        type: 'simulation',
        status: 'completed',
        simulationId: simId,
        runId,
        createdAt: Date.now(),
      });
      setSearchParams(
        { simulationId: simId, runId },
        { replace: true },
      );
    },
    [setSearchParams, upsertTask],
  );

  const applyRunPayload = useCallback((payload) => {
    if (payload?.fallback_used === 'runtime_what_if') {
      setResult(payload);
      return;
    }
    if (payload?.run && payload?.agents) {
      setResult(payload);
      return;
    }
    setResult(payload);
  }, []);

  useEffect(() => {
    const sid = (searchParams.get('simulationId') || '').trim();
    const rid = (searchParams.get('runId') || '').trim();
    if (!sid || !rid || !token) return;
    const key = `${sid}|${rid}`;
    if (loadedFromUrlRef.current === key) return;
    let cancelled = false;
    (async () => {
      setHydrating(true);
      setError('');
      try {
        const res = await fetch(`${API}/simulations/${encodeURIComponent(sid)}/runs/${encodeURIComponent(rid)}`, {
          credentials: 'include',
          headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        });
        const body = await readJsonResponse(res, 'Load simulation run');
        if (cancelled) return;
        const hydrated = hydrateSimulationDetail(body);
        const sim = body.simulation || {};
        if (sim.prompt) setPrompt(String(sim.prompt));
        if (Array.isArray(sim.assumptions) && sim.assumptions.length) {
          setAssumptionsText(sim.assumptions.join('\n'));
        }
        setResult(hydrated);
        loadedFromUrlRef.current = key;
      } catch (e) {
        if (!cancelled) setError(e?.message || 'Could not load saved simulation.');
      } finally {
        if (!cancelled) setHydrating(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [searchParams, token]);

  const runSimulation = async () => {
    const cleanPrompt = String(prompt || '').trim();
    if (!cleanPrompt) {
      setError('Enter a scenario to simulate.');
      return;
    }
    setLoading(true);
    setError('');
    setResult(null);
    loadedFromUrlRef.current = '';
    pushSimulationActivity({ status: 'running', label: cleanPrompt.slice(0, 80) });
    setActivityStrip(readActivityStrip());
    try {
      const headers = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };
      const createRes = await fetch(`${API}/simulations`, {
        method: 'POST',
        credentials: 'include',
        headers,
        body: JSON.stringify({
          prompt: cleanPrompt,
          assumptions,
          attachments,
          metadata: { surface: 'simulation_command_center' },
        }),
      });
      const created = await readJsonResponse(createRes, 'Create simulation');
      const simulationId = created?.simulation?.id;
      if (!simulationId) throw new Error('Simulation create response did not include an id.');

      const runPayload = {
        simulation_id: simulationId,
        prompt: cleanPrompt,
        assumptions,
        attachments,
        depth,
        use_live_evidence: true,
        require_live_retrieval_success: requireLiveRetrievalSuccess,
        metadata: { surface: 'simulation_command_center', depth },
      };
      const runRes = await fetch(`${API}/simulations/run`, {
        method: 'POST',
        credentials: 'include',
        headers,
        body: JSON.stringify(runPayload),
      });
      const runText = await runRes.text();
      let runJson = null;
      try {
        runJson = runText ? JSON.parse(runText) : null;
      } catch {
        runJson = null;
      }

      if (runRes.ok && runJson && typeof runJson === 'object') {
        applyRunPayload(runJson);
        persistCompletedRun(runJson, cleanPrompt);
        pushSimulationActivity({ status: 'completed', label: cleanPrompt.slice(0, 80), simulationId, runId: runJson?.run?.id });
        setActivityStrip(readActivityStrip());
      } else {
        const detail = runJson && typeof runJson === 'object' ? runJson.detail : null;
        const gateFailed = runRes.status === 422 && detail && detail.code === 'retrieval_gate_failed';
        if (gateFailed) {
          setError(detail.message || 'Live retrieval did not pass the evidence gate.');
          setResult({
            retrieval_gate_failed: true,
            retrieval_debug: detail.retrieval_debug || null,
          });
          pushSimulationActivity({ status: 'error', label: cleanPrompt.slice(0, 80), note: 'retrieval gate' });
          setActivityStrip(readActivityStrip());
        } else if (requireLiveRetrievalSuccess) {
          setError(
            (detail && detail.message) || runText.slice(0, 260).trim() || `Simulation run failed (${runRes.status}).`,
          );
          pushSimulationActivity({ status: 'error', label: cleanPrompt.slice(0, 80) });
          setActivityStrip(readActivityStrip());
        } else {
          try {
            const fallbackRes = await fetch(`${API}/runtime/what-if`, {
              method: 'POST',
              credentials: 'include',
              headers,
              body: JSON.stringify({
                scenario: cleanPrompt,
                depth,
                require_live_retrieval_success: requireLiveRetrievalSuccess,
                metadata: { surface: 'simulation_command_center', fallback_from: 'simulations_run', depth },
              }),
            });
            const fallback = await readJsonResponse(fallbackRes, 'Run simulation fallback');
            const merged = { ...fallback, fallback_used: 'runtime_what_if' };
            setResult(merged);
            pushSimulationActivity({ status: 'completed', label: cleanPrompt.slice(0, 80), note: 'compat runtime' });
            setActivityStrip(readActivityStrip());
          } catch {
            setError(
              (detail && detail.message) || runText.slice(0, 260).trim() || 'Simulation run and compatibility fallback both failed.',
            );
            pushSimulationActivity({ status: 'error', label: cleanPrompt.slice(0, 80) });
            setActivityStrip(readActivityStrip());
          }
        }
      }
    } catch (err) {
      setError(err?.message || 'Simulation failed.');
      pushSimulationActivity({ status: 'error', label: cleanPrompt.slice(0, 80) });
      setActivityStrip(readActivityStrip());
    } finally {
      setLoading(false);
    }
  };

  const classification = result?.classification || {};
  const trust = result?.trust_score || {};
  const report = result?.report || {};
  const agents = Array.isArray(result?.agents) ? result.agents : [];
  const messages = Array.isArray(result?.agent_messages) ? result.agent_messages : [];
  const updates = Array.isArray(result?.belief_updates) ? result.belief_updates : [];
  const outcomes = Array.isArray(result?.outcomes) ? result.outcomes : [];
  const evidence = Array.isArray(result?.evidence) ? result.evidence : [];
  const sources = Array.isArray(result?.sources) ? result.sources : [];
  const populationModel = result?.population_model || report?.population_model || {};
  const populationClusters = Array.isArray(populationModel?.clusters) ? populationModel.clusters : [];
  const missingEvidence = Array.isArray(result?.missing_evidence) ? result.missing_evidence : [];
  const unsupportedClaims = Array.isArray(result?.unsupported_claims) ? result.unsupported_claims : [];
  const finalVerdict = result?.final_verdict || report?.final_verdict || {};
  const outputAnswer = useMemo(() => {
    if (!result) return {};
    const fromApi = result.output_answer || report.output_answer;
    if (fromApi && typeof fromApi === 'object' && (fromApi.direct_answer || fromApi.confidence)) return fromApi;
    const fv = finalVerdict || {};
    const parts = [fv.verdict && `Structural verdict: ${fv.verdict}.`, fv.why, fv.next_best_action].filter(Boolean);
    return {
      direct_answer: parts.join(' ') || '—',
      confidence: fv.confidence_label || '—',
      evidence_status: 'Retrieval ledger not available (legacy or partial payload).',
      reasoning_summary: fv.why || '',
      data_used_summary: '',
      data_missing: Array.isArray(result.missing_evidence) ? result.missing_evidence : [],
      best_next_action: fv.next_best_action || '',
      assumption_based_insight: '',
      safety_compliance_note: '',
      exploratory: true,
    };
  }, [result, report, finalVerdict]);
  const retrievalDebug = useMemo(
    () =>
      result?.retrieval_debug
      || report?.evidence_summary?.retrieval_debug
      || outputAnswer?.retrieval_debug
      || null,
    [result, report, outputAnswer],
  );
  const evidencePolicyNested = report?.evidence_summary?.evidence_policy;
  const evidencePolicy = evidencePolicyNested || result?.trust_score?.evidence_policy || {};
  const replayEvents = Array.isArray(result?.replay_events) ? result.replay_events : [];
  const simulationPulse = Array.isArray(result?.simulation_pulse) ? result.simulation_pulse : [];
  const repExploreFor = Array.isArray(report.strongest_evidence_for) ? report.strongest_evidence_for : [];
  const repExploreAgainst = Array.isArray(report.strongest_evidence_against) ? report.strongest_evidence_against : [];
  const repWhatChange = Array.isArray(report.what_would_change_the_outcome) ? report.what_would_change_the_outcome : [];
  const debateMode = result?.debate_engine_mode ?? result?.run?.debate_engine_mode ?? null;
  const debateAside =
    debateMode === 'llm_augmented_claude'
      ? 'Claude-augmented dialogue'
      : debateMode === 'template_skeleton'
        ? 'Deterministic scaffold'
        : debateMode ? String(debateMode) : '—';

  const debateMessageCap =
    debateMode === 'llm_augmented_claude' ? 12 : 5;
  const engineLabel =
    loading || hydrating
      ? hydrating
        ? 'Loading saved run…'
        : 'Simulation running…'
      : classification.domain
        ? String(classification.domain)
        : '—';

  return (
    <div className="simulation-page">
      <header className="simulation-hero">
        <div className="simulation-kicker"><RadioTower size={14} /> Reality Engine</div>
        <h1>Simulation</h1>
        <p>
          Ask any scenario. CrucibAI classifies it, identifies evidence needs, creates
          scenario-specific agents, runs debate rounds, tracks belief shifts, produces
          an auditable report with trust scoring, and shows how modeled viewpoints cluster—on this page only.
        </p>
        <div className="sim-engine-line" aria-live="polite">
          <GitBranch size={14} aria-hidden /> <span>Scenario domain: <strong>{engineLabel}</strong></span>
          {(loading || hydrating) && <Loader2 size={14} className="spin sim-inline-spin" aria-hidden />}
        </div>
      </header>

      {activityStrip.length > 0 && (
        <section className="sim-activity-strip" aria-label="Simulation activity on this browser">
          <div className="sim-activity-head">Recent runs (this device)</div>
          <ul className="sim-activity-list">
            {activityStrip.map((row, idx) => (
              <li key={`${row.ts || idx}_${idx}`}>
                <span className={`sim-activity-badge sim-activity-${row.status || 'unknown'}`}>{row.status || '—'}</span>
                <span className="sim-activity-label">{row.label || 'Simulation'}{row.note ? ` · ${row.note}` : ''}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {(hydrating || (loading && !result)) && (
        <div className="simulation-status-banner" role="status">
          <Loader2 className="spin" size={16} aria-hidden />
          {hydrating ? 'Opening your saved Reality Engine run…' : 'Agents and population models are running—keep this tab open.'}
        </div>
      )}
      <Panel title="Universal Input" icon={Search}>
        <textarea
          className="simulation-prompt"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          rows={5}
          placeholder="Ask any forecast, decision, market reaction, product, sports, business, finance, policy, or engineering scenario..."
        />
        <div className="simulation-input-tools">
          <VoiceInput
            apiEndpoint={API}
            token={token}
            disabled={loading || hydrating}
            onTranscribed={(text) => {
              setPrompt((current) => {
                const existing = String(current || '').trim();
                return existing ? `${existing}\n${text}` : text;
              });
            }}
          />
        </div>
        <div className="simulation-presets">
          {PROMPTS.map((item) => (
            <button type="button" key={item} onClick={() => setPrompt(item)}>
              {item}
            </button>
          ))}
        </div>
        <textarea
          className="simulation-assumptions"
          value={assumptionsText}
          onChange={(event) => setAssumptionsText(event.target.value)}
          rows={3}
          placeholder="Optional assumptions, one per line. Example: LeBron is healthy. CAC is $90. Railway is the target host."
        />
        <div className="simulation-evidence-gate">
          <label className="simulation-evidence-gate-label">
            <input
              type="checkbox"
              checked={requireLiveRetrievalSuccess}
              onChange={(e) => {
                const v = e.target.checked;
                setRequireLiveRetrievalSuccess(v);
                try {
                  window.localStorage.setItem('crucib_require_live_retrieval', v ? '1' : '0');
                } catch {
                  /* ignore */
                }
              }}
              disabled={loading || hydrating}
            />
            <span>
              <strong>Require live evidence gate</strong>
              <small>
                For current or time-sensitive scenarios, fail the run (HTTP 422) if retrieval does not hit multiple
                collector families—instead of falling back to an exploratory answer. Uses the same flag as the API{' '}
                <code>require_live_retrieval_success</code>.
              </small>
            </span>
          </label>
        </div>
        <div className="simulation-controls">
          <fieldset className="simulation-depth">
            <legend>Simulation Depth</legend>
            {[
              ['fast', 'Fast', 'Quick read with light evidence retrieval.'],
              ['balanced', 'Balanced', 'Best default for most decisions and forecasts.'],
              ['deep', 'Deep', 'More evidence, debate, and population modeling.'],
              ['maximum', 'Maximum', 'Largest audited run for high-stakes scenarios.'],
            ].map(([value, label, description]) => (
              <button
                type="button"
                key={value}
                className={depth === value ? 'active' : ''}
                onClick={() => setDepth(value)}
              >
                <strong>{label}</strong>
                <span>{description}</span>
              </button>
            ))}
          </fieldset>
          <label className="simulation-file">
            <span>Attachments</span>
            <input
              type="file"
              multiple
              onChange={(event) => {
                const files = Array.from(event.target.files || []);
                setAttachments(files.map((file) => ({ name: file.name, size: file.size, type: file.type || 'unknown' })));
              }}
            />
          </label>
        </div>
        {attachments.length > 0 && (
          <div className="simulation-attachments">
            {attachments.map((file) => <span key={`${file.name}-${file.size}`}>{file.name}</span>)}
          </div>
        )}
        <div className="simulation-actions simulation-actions-row">
          <button type="button" className="simulation-run" onClick={runSimulation} disabled={loading || hydrating}>
            {loading ? <Loader2 size={15} className="spin" /> : <Play size={15} />}
            {loading ? 'Running Simulation...' : 'Run Simulation'}
          </button>
          <button
            type="button"
            className="simulation-secondary"
            onClick={runSimulation}
            disabled={loading || hydrating}
            title="Re-run using the same prompt and depth"
          >
            <RefreshCw size={14} /> Rerun
          </button>
          {error && <span className="simulation-error"><AlertTriangle size={14} /> {error}</span>}
        </div>
      </Panel>

      {result && (
        <>
          <Panel title="Auto-Detected Scenario" icon={Brain} aside={stringifyAside(result.engine)}>
            <div className="simulation-grid four">
              <div><span>Domain</span><strong>{classification.domain}</strong></div>
              <div><span>Scenario type</span><strong>{String(classification.scenario_type || '').replaceAll('_', ' ')}</strong></div>
              <div><span>Time sensitivity</span><strong>{classification.time_sensitivity}</strong></div>
              <div><span>Output style</span><strong>{String(classification.output_style || '').replaceAll('_', ' ')}</strong></div>
            </div>
            <p className="simulation-interpretation">{classification.interpretation}</p>
            {Array.isArray(classification.required_evidence) && (
              <div className="simulation-chips">
                {classification.required_evidence.map((item, idx) => (
                  <span key={simLineKey('req', item, idx)}>{simDisplayLine(item)}</span>
                ))}
              </div>
            )}
          </Panel>

          {finalVerdict.verdict && (
            <Panel title="Final Verdict" icon={CheckCircle2} aside={stringifyAside(finalVerdict.confidence_label)}>
              <div className="simulation-grid four">
                <div><span>Verdict</span><strong>{finalVerdict.verdict}</strong></div>
                <div><span>Probability</span><strong>{pct(finalVerdict.probability)}</strong></div>
                <div><span>Interval</span><strong>{pct(finalVerdict.lower_bound)}-{pct(finalVerdict.upper_bound)}</strong></div>
                <div><span>Coverage</span><strong>{pct(finalVerdict.evidence_coverage)}</strong></div>
              </div>
              <p className="simulation-interpretation">{finalVerdict.next_best_action}</p>
              {finalVerdict.official_gate_failed && (
                <div className="simulation-warning"><AlertTriangle size={13} /> Strong verdict is gated until fresh primary or trusted evidence is available.</div>
              )}
            </Panel>
          )}

          <Panel title="Output Answer" icon={MessageSquare} aside={outputAnswer.exploratory ? 'May include exploratory synthesis' : 'Mapped to this run'}>
            <div className="simulation-output-answer">
              <section>
                <h4>Direct answer</h4>
                <p className="simulation-oa-direct">{outputAnswer.direct_answer || '—'}</p>
              </section>
              <div className="simulation-grid two">
                <div><span>Confidence</span><strong className="simulation-oa-muted">{outputAnswer.confidence || '—'}</strong></div>
                <div><span>Best next action</span><strong className="simulation-oa-muted">{outputAnswer.best_next_action || '—'}</strong></div>
              </div>
              <section>
                <h4>Evidence status (retrieval)</h4>
                <p className="simulation-oa-meta">{outputAnswer.evidence_status || '—'}</p>
              </section>
              <section>
                <h4>Reasoning summary</h4>
                <p className="simulation-oa-meta">{outputAnswer.reasoning_summary || '—'}</p>
              </section>
              <section>
                <h4>Data used</h4>
                <pre className="simulation-oa-pre">{outputAnswer.data_used_summary || '—'}</pre>
              </section>
              {Array.isArray(outputAnswer.data_missing) && outputAnswer.data_missing.length > 0 && (
                <section>
                  <h4>Data missing</h4>
                  <ul className="simulation-oa-list">
                    {outputAnswer.data_missing.map((item, idx) => (
                      <li key={simLineKey('oa-miss', item, idx)}>{simDisplayLine(item)}</li>
                    ))}
                  </ul>
                </section>
              )}
              <section>
                <h4>Assumption-based insight</h4>
                <p className="simulation-oa-meta">{outputAnswer.assumption_based_insight || '—'}</p>
              </section>
              <section>
                <h4>Safety / compliance</h4>
                <p className="simulation-oa-safety">{outputAnswer.safety_compliance_note || '—'}</p>
              </section>
            </div>
          </Panel>

          {retrievalDebug && typeof retrievalDebug === 'object' && (
            <Panel title="Evidence retrieval status" icon={Telescope} aside={retrievalDebug.gate?.passed === false ? 'Gate failed — inspect collectors' : 'Pipeline debug'}>
              <p className="simulation-interpretation simulation-retrieval-lede">
                Query variants, per-collector HTTP diagnostics, accept/reject hints, and gate reasons. Use this before blaming “template simulation.”
              </p>
              <pre className="simulation-retrieval-json" aria-label="Retrieval debug JSON">
                {JSON.stringify(retrievalDebug, null, 2)}
              </pre>
            </Panel>
          )}

          <Panel title="Evidence Panel" icon={FileText} aside={`${sources.length} sources / ${evidence.length} facts`}>
            <div className="simulation-evidence-layout">
              <div>
                <h3>Sources used</h3>
                {sources.map((source) => (
                  <div className="simulation-source" key={source.id}>
                    <strong>{source.title}</strong>
                    <span>{source.type} / reliability: {source.reliability} / freshness: {source.freshness}</span>
                  </div>
                ))}
              </div>
              <div>
                <h3>Evidence gaps</h3>
                {missingEvidence.map((item, idx) => (
                  <div className="simulation-gap" key={simLineKey('gap', item, idx)}>
                    {simDisplayLine(item)}
                  </div>
                ))}
                {unsupportedClaims.map((item, idx) => (
                  <div className="simulation-warning" key={simLineKey('unsup', item, idx)}>
                    {simDisplayLine(item)}
                  </div>
                ))}
                {evidencePolicy.minimum_coverage != null && (
                  <div className="simulation-gap simulation-gap-policy">
                    Modeled credibility floor for this domain (minimum coverage):{' '}
                    <strong>{pct(evidencePolicy.minimum_coverage)}</strong>
                    {evidencePolicy.official_required_for_strong_verdict ? (
                      <span>. Primary or authorized sources matter for a strong directional verdict when the policy requires them.</span>
                    ) : null}
                  </div>
                )}
              </div>
            </div>
          </Panel>

          <Panel title="Agent Arena" icon={Users} aside={`${agents.length} core agents`}>
            <div className="simulation-agent-grid">
              {agents.map((agent) => (
                <div className="simulation-agent" key={agent.id}>
                  <div className="simulation-agent-head">
                    <strong>{agent.role}</strong>
                    <span>{pct(agent.current_belief)}</span>
                  </div>
                  <p>{agent.domain_expertise}</p>
                  <div className="simulation-meter"><i style={{ width: pct(agent.current_belief) }} /></div>
                  {agent.latest_argument && <p>{agent.latest_argument}</p>}
                  <footer>confidence {pct(agent.confidence)} / {agent.persona}</footer>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Population Reaction" icon={RadioTower} aside={populationModel.population_size ? `${Number(populationModel.population_size).toLocaleString()} perspectives` : 'modeled perspectives'}>
            <p className="simulation-interpretation">{populationModel.summary || 'Population modeling will appear when a run completes.'}</p>
            <div className="simulation-population-grid">
              {populationClusters.map((cluster) => (
                <div className="simulation-population" key={cluster.id || cluster.label}>
                  <div className="simulation-outcome-head">
                    <strong>{cluster.label}</strong>
                    <span>{pct(cluster.share)}</span>
                  </div>
                  <div className="simulation-meter"><i style={{ width: pct(cluster.share) }} /></div>
                  <p>{cluster.rationale}</p>
                  <footer>{Number(cluster.size || 0).toLocaleString()} modeled perspectives / {cluster.expected_shift}</footer>
                </div>
              ))}
            </div>
            {(populationModel.warnings || []).map((warning, idx) => (
              <div className="simulation-warning" key={simLineKey('pop-warn', warning, idx)}>
                <AlertTriangle size={13} /> {simDisplayLine(warning)}
              </div>
            ))}
          </Panel>

          {simulationPulse.length > 0 && (
            <Panel title="Simulation pulse" icon={Zap} aside={`${simulationPulse.length} beats · derived from debate + cohorts`}>
              <p className="simulation-interpretation sim-pulse-lede">
                What actually moved inside this run—each row is mechanically tied to arena messages or population clustering, not a generic narration block.
              </p>
              <ul className="simulation-pulse-feed" aria-label="Simulation pulse beats">
                {simulationPulse.map((pulse, idx) => (
                  <li key={`pulse_${pulse.kind || 'k'}_${idx}`} className="simulation-pulse-row" style={{ animationDelay: `${idx * 0.06}s` }}>
                    <span className="pulse-emoji" aria-hidden>{pulse.emoji || '·'}</span>
                    <div>
                      <strong className="pulse-title">{pulse.title || pulse.kind}</strong>
                      <p className="pulse-body">{pulse.body}</p>
                      {pulse.cause ? (
                        <footer className="pulse-cause">Why this line exists: {pulse.cause}</footer>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            </Panel>
          )}

          <Panel title="Live World View" icon={RadioTower} aside={`${populationModel.population_size ? Number(populationModel.population_size).toLocaleString() : '—'} modeled perspectives · sampled visualization`}>
            <p className="simulation-interpretation">
              Dots are sampled proportional to cohort weights—use this as an at-a-glance stance map alongside the audited clusters below.
            </p>
            <PopulationDotsCanvas
              clusters={populationClusters.length ? populationClusters : [{ label: 'Aggregated', share: 1, rationale: 'No cluster split returned.' }]}
              seedKey={result?.run?.id || `${classification.domain || 'x'}-${finalVerdict?.verdict || 'v'}`}
            />
            {replayEvents.length > 0 && (
              <div className="sim-replay-snippet">
                <h4>Latest engine events</h4>
                <ul>
                  {replayEvents.slice(-10).reverse().map((ev) => (
                    <li key={ev.id || `${ev.created_at}_${ev.event_type}`}>
                      <code>{ev.event_type || ev.type}</code>
                      {' '}
                      <span className="sim-replay-muted">{String(ev.created_at || '').slice(0, 19)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Panel>

          <Panel title="Debate Timeline" icon={GitBranch} aside={debateAside}>
            {(debateMode === 'template_skeleton' || debateMode === 'llm_augmented_claude') && (
              <p className="simulation-debate-kicker">
                {debateMode === 'llm_augmented_claude'
                  ? 'Lines below blend the structural debate lattice with Claude-expanded expert wording tied to harvested evidence—not recycled boilerplate.'
                  : 'Structural debate lattice runs first; configure ANTHROPIC_API_KEY and enable REALITY_ENGINE_LLM_DEBATE for expert-expanded turns.'}
              </p>
            )}
            <div className="simulation-timeline">
              {(result.rounds || []).map((round) => {
                const roundMessages = messages.filter((msg) => msg.round_id === round.id).slice(0, debateMessageCap);
                const roundUpdates = updates.filter((update) => update.round_id === round.id).slice(0, 3);
                return (
                  <div className="simulation-round" key={round.id}>
                    <div className="simulation-round-head">
                      <strong>Round {round.round_number}</strong>
                      <span>{round.purpose}</span>
                    </div>
                    {roundMessages.map((msg) => <p key={msg.id}>{msg.content}</p>)}
                    {roundUpdates.map((update) => (
                      <div className="simulation-belief" key={update.id}>
                        belief {pct(update.previous_belief)} -> {pct(update.new_belief)} / {update.reason}
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          </Panel>

          <Panel title="Outcomes" icon={Activity}>
            <div className="simulation-outcomes">
              {outcomes.map((outcome) => (
                <div className="simulation-outcome" key={outcome.id}>
                  <div className="simulation-outcome-head">
                    <strong>{outcome.label}</strong>
                    <span>{outcome.display_likelihood}</span>
                  </div>
                  <p>{outcome.rationale}</p>
                  <h4>What would change it</h4>
                  {(outcome.what_would_change || []).slice(0, 3).map((item, idx) => (
                    <em key={simLineKey('wwc', item, idx)}>{simDisplayLine(item)}</em>
                  ))}
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Trust Panel" icon={ShieldCheck} aside={stringifyAside(trust.trust_score)}>
            <div className="simulation-trust-grid">
              {Object.entries(trust.components || {}).map(([key, value]) => (
                <div key={key}>
                  <span>{key.replaceAll('_', ' ')}</span>
                  <strong>{pct(value)}</strong>
                </div>
              ))}
            </div>
            {(trust.warnings || []).map((warning, idx) => (
              <div className="simulation-warning" key={simLineKey('trust-warn', warning, idx)}>
                <AlertTriangle size={13} /> {simDisplayLine(warning)}
              </div>
            ))}
          </Panel>

          {(repExploreFor.length > 0
            || repExploreAgainst.length > 0
            || repWhatChange.length > 0
            || evidencePolicy.verdict_style
            || evidencePolicy.minimum_coverage != null) && (
            <Panel title="Credibility & next exploration" icon={Telescope} aside={trust.score != null ? pct(Number(trust.score)) : ''}>
              <p className="simulation-interpretation">
                Audited signals from this run—the strongest factual pulls, what would move the needle, and the policy frame used so you can interpret confidence honestly.
              </p>
              <div className="simulation-grid two simulation-credibility-row">
                <div>
                  <span>Coverage vs floor</span>
                  <strong>
                    {finalVerdict.evidence_coverage != null ? pct(finalVerdict.evidence_coverage) : '—'} mapped · floor{' '}
                    {evidencePolicy.minimum_coverage != null ? pct(evidencePolicy.minimum_coverage) : '—'}
                  </strong>
                </div>
                <div><span>Verdict framing</span><strong>{VERDICT_STYLE_LABELS[evidencePolicy.verdict_style] || evidencePolicy.verdict_style || '—'}</strong></div>
              </div>
              {repWhatChange.length > 0 && (
                <div className="sim-explore-block">
                  <h4>What would most change this picture</h4>
                  <ul>
                    {repWhatChange.map((item, idx) => (
                      <li key={simLineKey('rwtc', item, idx)}>{simDisplayLine(item)}</li>
                    ))}
                  </ul>
                </div>
              )}
              {(repExploreFor.length > 0 || repExploreAgainst.length > 0) && (
                <div className="sim-explore-columns">
                  {repExploreFor.length > 0 && (
                    <div className="sim-explore-block">
                      <h4>Strongest support in this run</h4>
                      <ul>
                        {repExploreFor.map((item, idx) => (
                          <li key={simLineKey('sef', item, idx)}>{simDisplayLine(item)}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {repExploreAgainst.length > 0 && (
                    <div className="sim-explore-block">
                      <h4>Strongest counterweight</h4>
                      <ul>
                        {repExploreAgainst.map((item, idx) => (
                          <li key={simLineKey('sea', item, idx)}>{simDisplayLine(item)}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </Panel>
          )}

          <Panel title="Final Report" icon={CheckCircle2}>
            <div className="simulation-report">
              <h3>{report.executive_summary}</h3>
              <p>{result.recommendation?.recommendation}</p>
              <h4>Next data to collect</h4>
              <ul>
                {(report.next_data_to_collect || []).map((item, idx) => (
                  <li key={simLineKey('next', item, idx)}>{simDisplayLine(item)}</li>
                ))}
              </ul>
              <div className="simulation-replay">
                Simulation {report.replay_metadata?.simulation_id} / Run {report.replay_metadata?.run_id}
              </div>
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}
