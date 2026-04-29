import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { MonitorSmartphone, Wrench } from 'lucide-react';
import UnifiedWorkspace from './UnifiedWorkspace';
import { useAuth } from '../authContext';
import { getWorkspaceCapabilities } from '../lib/modePolicy';
import './WorkspaceVNext.css';

const SURFACES = ['build', 'inspect', 'what-if', 'deploy', 'repair'];

function readRequestedMode(searchParams) {
  const raw = String(searchParams.get('mode') || '').toLowerCase();
  if (raw === 'developer') return 'developer';
  if (raw === 'simple') return 'simple';
  return null;
}

function readRequestedSurface(searchParams) {
  const raw = String(searchParams.get('surface') || '').toLowerCase();
  return SURFACES.includes(raw) ? raw : 'build';
}

/**
 * WorkspaceVNext is the canonical workspace controller.
 * It enforces policy-based mode selection and normalizes local mode keys for UnifiedWorkspace.
 */
export default function WorkspaceVNext() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [modeNotice, setModeNotice] = useState('');
  const [runtimeTelemetry, setRuntimeTelemetry] = useState(null);
  const [surface, setSurfaceState] = useState(() => readRequestedSurface(searchParams));
  const [whatIfScenario, setWhatIfScenario] = useState('What if we replace Braintree with LemonSqueezy in the billing flow?');
  const [whatIfLoading, setWhatIfLoading] = useState(false);
  const [whatIfResult, setWhatIfResult] = useState(null);
  const [whatIfError, setWhatIfError] = useState('');
  const [whatIfRequireLive, setWhatIfRequireLive] = useState(false);

  const caps = useMemo(() => getWorkspaceCapabilities(user), [user]);
  const requestedMode = readRequestedMode(searchParams);
  const canUseDeveloper = Boolean(caps.canUseAdvancedControls);
  const projectId = useMemo(() => {
    const userId = String(user?.id || '').trim();
    return userId ? `runtime-${userId}` : '';
  }, [user]);

  const effectiveMode = useMemo(() => {
    if (requestedMode === 'developer' && canUseDeveloper) return 'developer';
    if (requestedMode === 'simple') return 'simple';
    return caps.mode;
  }, [requestedMode, canUseDeveloper, caps.mode]);

  useEffect(() => {
    if (requestedMode === 'developer' && !canUseDeveloper) {
      setModeNotice('Developer mode is unavailable for this account. Running in simple mode.');
      const next = new URLSearchParams(searchParams);
      next.set('mode', 'simple');
      setSearchParams(next, { replace: true });
      return;
    }
    setModeNotice('');
  }, [requestedMode, canUseDeveloper, searchParams, setSearchParams]);

  useEffect(() => {
    const uxMode = effectiveMode === 'developer' ? 'pro' : 'simple';
    localStorage.setItem('crucibai_workspace_mode', effectiveMode);
    localStorage.setItem('crucibai_ux_mode', uxMode);
  }, [effectiveMode]);

  useEffect(() => {
    let cancelled = false;
    const canShowTelemetry = effectiveMode === 'developer';
    const userId = String(user?.id || '').trim();
    if (!canShowTelemetry || !userId || typeof fetch !== 'function') {
      setRuntimeTelemetry(null);
      return () => {
        cancelled = true;
      };
    }

    const endpoint = '/api/runtime/inspect?limit=100';

    const load = async () => {
      try {
        const res = await fetch(endpoint, { credentials: 'include' });
        if (!res.ok) {
          if (!cancelled) setRuntimeTelemetry(null);
          return;
        }
        const payload = await res.json();
        if (!cancelled) setRuntimeTelemetry(payload);
      } catch {
        if (!cancelled) setRuntimeTelemetry(null);
      }
    };

    load();
    const t = setInterval(load, 10000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [effectiveMode, projectId, user]);

  const inspectDigest = useMemo(() => {
    const inspect = runtimeTelemetry?.inspect;
    if (!inspect) return null;
    const timeline = Array.isArray(inspect.timeline) ? inspect.timeline.slice(0, 8) : [];
    const failures = Array.isArray(inspect.failures) ? inspect.failures.slice(0, 3) : [];
    return {
      timeline,
      failures,
      taskStatusSummary: inspect.task_status_summary || {},
      phaseSummary: inspect.phase_summary || {},
    };
  }, [runtimeTelemetry]);

  const setMode = (mode) => {
    if (mode === 'developer' && !canUseDeveloper) {
      setModeNotice('Developer mode is unavailable for this account.');
      return;
    }
    const next = new URLSearchParams(searchParams);
    next.set('mode', mode);
    setSearchParams(next, { replace: true });
  };

  const setSurface = (nextSurface) => {
    setSurfaceState(nextSurface);
    const next = new URLSearchParams(searchParams);
    next.set('surface', nextSurface);
    setSearchParams(next, { replace: true });
  };

  const runWhatIf = async () => {
    const scenario = String(whatIfScenario || '').trim();
    if (!scenario || !projectId || typeof fetch !== 'function') {
      setWhatIfError('Scenario and runtime project are required.');
      return;
    }

    setWhatIfLoading(true);
    setWhatIfError('');
    try {
      const res = await fetch('/api/runtime/what-if', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario,
          population_size: 48,
          rounds: 4,
          require_live_retrieval_success: whatIfRequireLive,
          priors: {
            cost_sensitive: 0.3,
            security_first: 0.35,
            speed_first: 0.35,
          },
        }),
      });
      const rawText = await res.text();
      let payload = null;
      try {
        payload = rawText ? JSON.parse(rawText) : null;
      } catch {
        payload = null;
      }
      if (!res.ok) {
        setWhatIfResult(null);
        const detail = payload && typeof payload === 'object' ? payload.detail : null;
        if (res.status === 422 && detail && detail.code === 'retrieval_gate_failed') {
          setWhatIfError(detail.message || 'Live retrieval did not meet the evidence gate. Add API keys or disable “Require live evidence”.');
        } else {
          setWhatIfError((detail && detail.message) || rawText.slice(0, 200).trim() || 'What-if simulation failed.');
        }
        return;
      }
      setWhatIfResult(payload);
    } catch {
      setWhatIfResult(null);
      setWhatIfError('What-if simulation failed.');
    } finally {
      setWhatIfLoading(false);
    }
  };

  return (
    <div className="workspace-vnext-root">
      <div className="workspace-vnext-toolbar workspace-vnext-toolbar--mode">
        <button
          type="button"
          className={`workspace-vnext-mode ${effectiveMode === 'simple' ? 'active' : ''}`}
          onClick={() => setMode('simple')}
        >
          <MonitorSmartphone size={14} />
          Simple
        </button>
        <button
          type="button"
          className={`workspace-vnext-mode ${effectiveMode === 'developer' ? 'active' : ''}`}
          onClick={() => setMode('developer')}
          disabled={!canUseDeveloper}
          title={!canUseDeveloper ? 'Developer mode requires developer/internal access' : 'Switch to developer mode'}
        >
          <Wrench size={14} />
          Developer
        </button>
      </div>
      <div className="workspace-vnext-toolbar workspace-vnext-toolbar--surface" role="tablist" aria-label="Workspace surface mode">
        {SURFACES.map((item) => (
          <button
            key={item}
            type="button"
            className={`workspace-vnext-mode workspace-vnext-surface ${surface === item ? 'active' : ''}`}
            onClick={() => setSurface(item)}
            role="tab"
            aria-selected={surface === item}
          >
            {item === 'what-if' ? 'What-if' : item.charAt(0).toUpperCase() + item.slice(1)}
          </button>
        ))}
      </div>
      {runtimeTelemetry ? (
        <aside className="workspace-vnext-telemetry" aria-label="Runtime telemetry">
          <div className="workspace-vnext-telemetry-title">Runtime telemetry</div>
          <div className="workspace-vnext-telemetry-grid">
            <span>Tasks</span>
            <strong>{Number(runtimeTelemetry.task_count || 0)}</strong>
            <span>Memory nodes</span>
            <strong>{Number(runtimeTelemetry.memory_graph?.node_count || 0)}</strong>
            <span>Memory edges</span>
            <strong>{Number(runtimeTelemetry.memory_graph?.edge_count || 0)}</strong>
            <span>Ledger tasks</span>
            <strong>{Object.keys(runtimeTelemetry.cost_ledger || {}).length}</strong>
            <span>Recent events</span>
            <strong>{Array.isArray(runtimeTelemetry.recent_events) ? runtimeTelemetry.recent_events.length : 0}</strong>
          </div>
        </aside>
      ) : null}
      {surface === 'inspect' && inspectDigest ? (
        <aside className="workspace-vnext-inspect" aria-label="Inspect timeline">
          <div className="workspace-vnext-inspect-title">Inspect timeline</div>
          <div className="workspace-vnext-inspect-row">
            <span>Task states</span>
            <strong>
              {Object.entries(inspectDigest.taskStatusSummary)
                .map(([k, v]) => `${k}:${v}`)
                .join(' | ') || 'none'}
            </strong>
          </div>
          <div className="workspace-vnext-inspect-list" role="list">
            {inspectDigest.timeline.map((item, idx) => (
              <div key={`${item.type || 'evt'}-${idx}`} role="listitem" className="workspace-vnext-inspect-item">
                <span>{item.type || 'event'}</span>
                <strong>{item.phase || item.agent || item.status || 'runtime'}</strong>
              </div>
            ))}
          </div>
          {inspectDigest.failures.length ? (
            <div className="workspace-vnext-inspect-failures">
              <div className="workspace-vnext-inspect-subtitle">Recent failures</div>
              {inspectDigest.failures.map((f, idx) => (
                <p key={`${f.type || 'failure'}-${idx}`}>{f.error || f.type}</p>
              ))}
            </div>
          ) : null}
        </aside>
      ) : null}
      {surface === 'what-if' ? (
        <aside className="workspace-vnext-whatif" aria-label="What-if simulation">
          <div className="workspace-vnext-inspect-title">What-if simulation</div>
          <label htmlFor="workspace-vnext-scenario">Scenario</label>
          <textarea
            id="workspace-vnext-scenario"
            value={whatIfScenario}
            onChange={(e) => setWhatIfScenario(e.target.value)}
            rows={4}
          />
          <label className="workspace-vnext-whatif-strict">
            <input
              type="checkbox"
              checked={whatIfRequireLive}
              onChange={(e) => setWhatIfRequireLive(e.target.checked)}
              disabled={whatIfLoading}
            />
            <span>Require live evidence gate (422 if retrieval fails)</span>
          </label>
          <button type="button" onClick={runWhatIf} disabled={whatIfLoading}>
            {whatIfLoading ? 'Running...' : 'Run simulation'}
          </button>
          {whatIfError ? <p className="workspace-vnext-whatif-error">{whatIfError}</p> : null}
          {whatIfResult ? (
            <div className="workspace-vnext-whatif-result">
              <p>
                <strong>Recommendation:</strong> {whatIfResult?.recommendation?.recommended_action || 'Collect more evidence'}
              </p>
              <p>
                <strong>Confidence:</strong> {whatIfResult?.recommendation?.confidence ?? 'n/a'}
              </p>
              <p>
                <strong>Rounds:</strong> {whatIfResult?.rounds_executed ?? 0}
              </p>
            </div>
          ) : null}
        </aside>
      ) : null}
      {modeNotice ? <div className="workspace-vnext-notice">{modeNotice}</div> : null}
      <UnifiedWorkspace workspaceSurface={surface} />
    </div>
  );
}
