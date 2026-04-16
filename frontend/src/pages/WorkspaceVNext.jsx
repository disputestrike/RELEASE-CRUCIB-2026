import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { MonitorSmartphone, Wrench } from 'lucide-react';
import UnifiedWorkspace from './UnifiedWorkspace';
import { useAuth } from '../authContext';
import { getWorkspaceCapabilities } from '../lib/modePolicy';
import './WorkspaceVNext.css';

function readRequestedMode(searchParams) {
  const raw = String(searchParams.get('mode') || '').toLowerCase();
  if (raw === 'developer') return 'developer';
  if (raw === 'simple') return 'simple';
  return null;
}

/**
 * WorkspaceVNext is the canonical workspace controller.
 * It enforces policy-based mode selection and normalizes local mode keys for UnifiedWorkspace.
 */
export default function WorkspaceVNext() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [modeNotice, setModeNotice] = useState('');

  const caps = useMemo(() => getWorkspaceCapabilities(user), [user]);
  const requestedMode = readRequestedMode(searchParams);
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

  const setMode = (mode) => {
    if (mode === 'developer' && !canUseDeveloper) {
      setModeNotice('Developer mode is unavailable for this account.');
      return;
    }
    const next = new URLSearchParams(searchParams);
    next.set('mode', mode);
    setSearchParams(next, { replace: true });
  };

  return (
    <div className="workspace-vnext-root">
      <div className="workspace-vnext-toolbar">
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
      {modeNotice ? <div className="workspace-vnext-notice">{modeNotice}</div> : null}
      <UnifiedWorkspace />
    </div>
  );
}
