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

  const caps = useMemo(() => getWorkspaceCapabilities(user), [user]);
  const requestedMode = readRequestedMode(searchParams);
  const surface = readRequestedSurface(searchParams);
  const canUseDeveloper = Boolean(caps.canUseAdvancedControls);

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

    const projectId = `runtime-${userId}`;
    const endpoint = `/api/debug/runtime-state/${encodeURIComponent(projectId)}?limit=100`;

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
  }, [effectiveMode, user]);

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
    const next = new URLSearchParams(searchParams);
    next.set('surface', nextSurface);
    setSearchParams(next, { replace: true });
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
      {modeNotice ? <div className="workspace-vnext-notice">{modeNotice}</div> : null}
      <UnifiedWorkspace workspaceSurface={surface} />
    </div>
  );
}
