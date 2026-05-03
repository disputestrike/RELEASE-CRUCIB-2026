/**
 * PreviewPanel — live preview: remote iframe when URL ready, else Sandpack from editor files.
 * `sandpackIsFallback`: show trust banner when Sandpack boots from a heuristic entry (no App.jsx).
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import ErrorOverlay from '../ErrorOverlay';
import { SandpackProvider, SandpackPreview } from '@codesandbox/sandpack-react';
import { RefreshCw, ExternalLink } from 'lucide-react';
import SandpackErrorBoundary from '../SandpackErrorBoundary';
import { derivePreviewReadiness } from '../../workspace/workspaceLiveUi';
import '../SandpackErrorBoundary.css';
import './PreviewPanel.css';

/**
 * Iframe and new-tab links must target the **API** origin when `REACT_APP_BACKEND_URL` is set;
 * a path-only `dev_server_url` (e.g. `/api/preview/.../serve`) otherwise resolves to the
 * static app host and returns HTML or 404 — blank white preview.
 */
function resolveAgentPreviewUrl(url, apiBase) {
  if (url == null || url === '') return null;
  if (/^https?:\/\//i.test(String(url))) return String(url);
  const p = String(url);
  if (p.startsWith('/') && apiBase && /^https?:\/\//i.test(apiBase)) {
    const origin = new URL(apiBase).origin;
    return `${origin}${p}`;
  }
  if (p.startsWith('/') && typeof window !== 'undefined' && (!apiBase || apiBase.startsWith('/'))) {
    return `${window.location.origin}${p}`;
  }
  return p;
}

function wsBaseFromApiBase(apiBase) {
  if (!apiBase) return '';
  if (apiBase.startsWith('https://')) return apiBase.replace('https://', 'wss://');
  if (apiBase.startsWith('http://')) return apiBase.replace('http://', 'ws://');
  if (apiBase.startsWith('/') && typeof window !== 'undefined') {
    const p = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${p}://${window.location.host}${apiBase}`;
  }
  return apiBase;
}

export default function PreviewPanel({
  previewUrl,
  status = 'idle',
  sandpackFiles = null,
  sandpackDeps = null,
  filesReadyKey = 'default',
  sandpackIsFallback = false,
  /** Plain-language hint when preview cannot render (e.g. verify failure). */
  blockedDetail = null,
  jobId = null,
  token = null,
  apiBase = '',
  /** Drives re-fetch of /dev-preview when the job or workspace on disk changes (e.g. dist/ lands). */
  jobStatus = null,
  events = [],
}) {
  const iframeRef = useRef(null);
  const [devServerUrl, setDevServerUrl] = useState(null);
  const [devPreviewError, setDevPreviewError] = useState(null);
  const [devPreviewStatus, setDevPreviewStatus] = useState(null);
  const [isBootingDevPreview, setIsBootingDevPreview] = useState(false);
  const [retryTick, setRetryTick] = useState(0);

  const hasSandpack = sandpackFiles && Object.keys(sandpackFiles).length > 0;
  const remotePreviewUrl = useMemo(() => previewUrl || devServerUrl || null, [previewUrl, devServerUrl]);
  const resolvedRemoteUrl = useMemo(
    () => resolveAgentPreviewUrl(remotePreviewUrl, apiBase),
    [remotePreviewUrl, apiBase],
  );
  const useRemote = Boolean(resolvedRemoteUrl);

  // Single-shot GET never worked: the build often returned 202 (no index.html) once, then dist appears
  // later. We also must re-run when jobStatus → completed and when filesReadyKey bumps (Sync / steps).
  useEffect(() => {
    let cancelled = false;
    let timeoutId = null;
    let attempt = 0;
    const maxAttempts = 40;

    if (previewUrl || !jobId || !token || !apiBase) return undefined;

    const isTerminal = (s) => s === 'cancelled';

    setIsBootingDevPreview(true);
    setDevPreviewError(null);
    setDevPreviewStatus(null);

    const scheduleRetry = (delayMs) => {
      if (cancelled) return;
      if (isTerminal(jobStatus)) return;
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        void doFetch();
      }, delayMs);
    };

    const doFetch = async () => {
      if (cancelled) return;
      try {
        const res = await axios.get(`${apiBase}/jobs/${encodeURIComponent(jobId)}/dev-preview`, {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 20000,
        });
        if (cancelled) return;
        setDevPreviewStatus(res.data || null);
        setIsBootingDevPreview(false);
        const u = res.data?.dev_server_url;
        if (u) {
          setDevServerUrl(u);
          setDevPreviewError(null);
          return;
        }
        setDevServerUrl(null);
        attempt += 1;
        if (!isTerminal(jobStatus) && attempt < maxAttempts) {
          setDevPreviewError(null);
          scheduleRetry(4000);
        }
      } catch (e) {
        if (cancelled) return;
        setDevPreviewStatus(e?.response?.data || null);
        setIsBootingDevPreview(false);
        setDevServerUrl(null);
        attempt += 1;
        if (!isTerminal(jobStatus) && attempt < maxAttempts) {
          setDevPreviewError(null);
          scheduleRetry(4000);
        } else {
          const detail = e?.response?.data?.detail || e?.message || 'Unable to start live preview';
          setDevPreviewError(String(detail));
        }
      }
    };

    void doFetch();

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [previewUrl, jobId, token, apiBase, retryTick, filesReadyKey, jobStatus]);

  useEffect(() => {
    if (!jobId || !token || !apiBase || !resolvedRemoteUrl) return undefined;
    const wsBase = wsBaseFromApiBase(apiBase);
    const ws = new WebSocket(`${wsBase}/ws/jobs/${jobId}/preview-watch?token=${encodeURIComponent(token)}`);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data || '{}');
        if (data?.type === 'files_changed' && Array.isArray(data.files) && data.files.length && iframeRef.current && resolvedRemoteUrl) {
          const u = resolvedRemoteUrl.replace(/\/$/, '');
          iframeRef.current.src = `${u}/?t=${Date.now()}`;
        }
      } catch {}
    };
    return () => { try { ws.close(); } catch {} };
  }, [jobId, token, apiBase, resolvedRemoteUrl]);

  const statusColor = useRemote
    ? 'var(--state-success)'
    : status === 'blocked'
      ? 'var(--text-muted)'
      : status === 'building'
        ? 'var(--state-warning)'
        : hasSandpack
          ? 'var(--state-success)'
          : 'var(--text-muted)';

  // TRUTH MODE: explicit indicator of preview type
  const previewMode = useRemote
    ? 'dev-server'
    : hasSandpack
      ? 'sandpack-fallback'
      : 'static';
  
  const statusLabel = useRemote
    ? 'Live (dev server)'
    : status === 'blocked'
      ? 'Fixing'
      : status === 'building'
        ? 'Taking shape'
        : hasSandpack
        ? 'Preview (fallback)'
        : 'Next up';
  const previewTitle = useRemote ? 'Live Preview' : 'Preview Console';
  const readiness = derivePreviewReadiness({
    previewStatus: status,
    previewUrl: resolvedRemoteUrl || remotePreviewUrl,
    hasSandpack,
    devPreviewStatus,
    devPreviewError,
    isBootingDevPreview,
  });
  const showBootingOverlay = isBootingDevPreview && !useRemote && !hasSandpack;
  const overlayMessage = devPreviewError || (showBootingOverlay
    ? 'Booting a workspace dev server so preview updates without a manual refresh.'
    : null);
  const overlayTitle = devPreviewError ? 'Preview issue' : 'Starting live preview';
  const activity = useMemo(() => {
    const rows = Array.isArray(events) ? events : [];
    const last = rows.length ? rows[rows.length - 1] : null;
    const payload = last?.payload && typeof last.payload === 'object' ? last.payload : {};
    const missing = payload.missing || payload.missing_routes || payload.missing_items || [];
    const files = payload.files || payload.changed_files || payload.output_files || [];
    return {
      eventType: last?.type || null,
      phase: payload.phase || payload.step || payload.step_key || 'intent routing',
      agent: payload.agent || payload.agent_name || payload.tool || 'orchestrator',
      files: Array.isArray(files) ? files.slice(0, 4) : [],
      missing: Array.isArray(missing) ? missing.slice(0, 4) : [],
    };
  }, [events]);

  return (
    <div className="preview-panel">
      <div className="pp-preview-header">
        <div className="pp-preview-title-row">
          <span className="pp-preview-dot" style={{ background: statusColor }} />
          <span className="pp-preview-title">{previewTitle}</span>
          <span className="pp-preview-status">{devServerUrl && !previewUrl ? 'Hot reload' : statusLabel}</span>
        </div>
        <div className="pp-preview-actions">
          {useRemote && (
            <>
              <button
                type="button"
                className="pp-preview-btn"
                onClick={() => {
                  if (iframeRef.current && resolvedRemoteUrl) {
                    const u = resolvedRemoteUrl.replace(/\/$/, '');
                    iframeRef.current.src = `${u}/?t=${Date.now()}`;
                  }
                }}
                title="Refresh preview"
              >
                <RefreshCw size={12} />
              </button>
              <a href={resolvedRemoteUrl || remotePreviewUrl} target="_blank" rel="noopener noreferrer" className="pp-preview-btn" title="Open in new tab">
                <ExternalLink size={12} />
              </a>
            </>
          )}
        </div>
      </div>

      <div className="pp-preview-body">
        {/* TRUTH BANNER: explicit mode indicator */}
        {previewMode === 'sandpack-fallback' && (
          <div className="pp-preview-truth-banner pp-preview-truth-fallback" role="status">
            <span className="pp-preview-truth-icon">!</span>
            <span className="pp-preview-truth-text">
              Preview is a fallback sandbox. Runtime not yet available.
            </span>
          </div>
        )}
        {previewMode === 'dev-server' && (
          <div className="pp-preview-truth-banner pp-preview-truth-live" role="status">
            <span className="pp-preview-truth-icon">OK</span>
            <span className="pp-preview-truth-text">
              Runtime preview serving
            </span>
          </div>
        )}
        <div className={`pp-preview-state-strip pp-preview-state-strip--${readiness.severity}`} role="status">
          <span className="pp-preview-state-label">{readiness.label}</span>
          <span className="pp-preview-state-detail">{readiness.detail}</span>
        </div>
        <ErrorOverlay
          title={overlayTitle}
          message={overlayMessage}
          onRetry={jobId && token && apiBase ? () => { setDevServerUrl(null); setDevPreviewError(null); setIsBootingDevPreview(false); setRetryTick((v) => v + 1); } : null}
        />
        {status === 'blocked' && hasSandpack && (
          <div className="pp-preview-blocked-banner" role="status">
            <span className="pp-preview-blocked-title">Preview fix continuing automatically</span>
            <p className="pp-preview-blocked-hint">
              {typeof blockedDetail === 'string' && blockedDetail.trim()
                ? blockedDetail
                : 'Add a short note below - what you see here is the last good snapshot.'}
            </p>
          </div>
        )}

        {!useRemote && status === 'idle' && !hasSandpack && (
          <div className="pp-preview-idle">
            <span className="pp-preview-idle-text">
              Your preview will appear here as files land — stay on this tab and it will update on its own.
            </span>
          </div>
        )}

        {status === 'blocked' && !hasSandpack && (
          <div className="pp-preview-blocked-full">
            <span className="pp-preview-blocked-title">Fixing preview now</span>
            <p className="pp-preview-blocked-hint">
              {typeof blockedDetail === 'string' && blockedDetail
                ? blockedDetail
                : 'The brain is applying fixes and will keep this run moving automatically.'}
            </p>
          </div>
        )}

        {status === 'building' && !hasSandpack && (
          <div className="pp-preview-building">
            <div className="pp-preview-shimmer" />
            <span className="pp-preview-building-text">Assembling your preview...</span>
            <div className="pp-build-activity" role="status">
              <div className="pp-build-activity-head">Generating workspace files...</div>
              <div className="pp-build-activity-row">Current phase: {activity.phase}</div>
              <div className="pp-build-activity-row">Active agent: {activity.agent}</div>
              {activity.files.length > 0 && (
                <div className="pp-build-activity-list">
                  {activity.files.map((f, i) => (
                    <div key={`${f}_${i}`}>- {String(f)}</div>
                  ))}
                </div>
              )}
              {activity.missing.length > 0 && (
                <div className="pp-build-activity-list">
                  {activity.missing.map((m, i) => (
                    <div key={`${m}_${i}`}>- missing: {String(m)}</div>
                  ))}
                </div>
              )}
            </div>
            {blockedDetail ? (
              <p className="pp-preview-blocked-hint" title={typeof blockedDetail === 'string' ? blockedDetail : undefined}>
                {typeof blockedDetail === 'string' ? blockedDetail : ''}
              </p>
            ) : null}
          </div>
        )}

        {!useRemote && status === 'ready' && !hasSandpack && (
          <div className="pp-preview-ready-fallback">
            <div className="pp-preview-fallback-message">
              <span className="pp-preview-idle-text">
                Workspace files ready. Sync generated code or add UI files below.
              </span>
            </div>
            {/* Show minimal Sandpack shell for immediate interactivity */}
            {sandpackDeps && (
              <div className="pp-sandpack-host" style={{ flex: 1, minHeight: '300px' }}>
                <SandpackProvider
                  key={filesReadyKey}
                  files={{
                    '/src/App.jsx': {
                      code: `export default function App() {
  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>Ready to code</h1>
      <p>Sync files or add your components to get started.</p>
    </div>
  );
}`,
                    },
                    '/src/index.js': {
                      code: `import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);`,
                    },
                  }}
                  theme={document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'}
                  template="react"
                  customSetup={{ dependencies: sandpackDeps }}
                  options={{
                    autoReload: true,
                    recompileMode: 'delayed',
                    recompileDelay: 500,
                  }}
                >
                  <SandpackErrorBoundary>
                    <SandpackPreview showOpenInCodeSandbox={false} style={{ height: '100%', minHeight: 280 }} />
                  </SandpackErrorBoundary>
                </SandpackProvider>
              </div>
            )}
            {!sandpackDeps && (
              <div className="pp-preview-waiting">
                <span className="pp-preview-idle-text">
                  Dependencies loading — check back in a moment.
                </span>
              </div>
            )}
          </div>
        )}

        {useRemote && (
          <iframe ref={iframeRef} className="pp-preview-iframe" src={resolvedRemoteUrl || remotePreviewUrl} title="Live Preview" />
        )}

        {!useRemote && hasSandpack && sandpackDeps && sandpackIsFallback && (
          <div className="pp-preview-trust-banner" role="status">
            Starter shell: we&apos;re showing a minimal preview until your app entry is ready. Sync files or add{' '}
            <code>/src/App.jsx</code> — deploy may differ until targets match.
          </div>
        )}

        {!useRemote && hasSandpack && sandpackDeps && (
          <div className="pp-sandpack-host">
            <SandpackProvider
              key={filesReadyKey}
              files={sandpackFiles}
              theme={document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'}
              template="react"
              customSetup={{ dependencies: sandpackDeps }}
              options={{
                externalResources: [
                  'https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css',
                  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap',
                ],
                autoReload: true,
                recompileMode: 'delayed',
                recompileDelay: 500,
              }}
            >
              <SandpackErrorBoundary>
                <SandpackPreview showOpenInCodeSandbox={false} style={{ height: '100%', minHeight: 280 }} />
              </SandpackErrorBoundary>
            </SandpackProvider>
          </div>
        )}
      </div>
    </div>
  );
}
