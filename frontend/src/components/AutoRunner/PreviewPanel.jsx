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
import '../SandpackErrorBoundary.css';
import './PreviewPanel.css';

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
}) {
  const iframeRef = useRef(null);
  const [devServerUrl, setDevServerUrl] = useState(null);
  const [devPreviewError, setDevPreviewError] = useState(null);
  const [isBootingDevPreview, setIsBootingDevPreview] = useState(false);
  const [retryTick, setRetryTick] = useState(0);

  const hasSandpack = sandpackFiles && Object.keys(sandpackFiles).length > 0;
  const remotePreviewUrl = useMemo(() => previewUrl || devServerUrl || null, [previewUrl, devServerUrl]);
  const useRemote = Boolean(remotePreviewUrl);

  useEffect(() => {
    let cancelled = false;
    if (previewUrl || !jobId || !token || !apiBase) return undefined;
    setIsBootingDevPreview(true);
    setDevPreviewError(null);
    axios.get(`${apiBase}/jobs/${jobId}/dev-preview`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (cancelled) return;
        setDevServerUrl(res.data?.dev_server_url || null);
      })
      .catch((err) => {
        if (cancelled) return;
        const detail = err?.response?.data?.detail || err?.message || 'Unable to start live preview';
        setDevPreviewError(String(detail));
      })
      .finally(() => { if (!cancelled) setIsBootingDevPreview(false); });
    return () => { cancelled = true; };
  }, [previewUrl, jobId, token, apiBase, retryTick]);

  useEffect(() => {
    if (!jobId || !token || !apiBase || !remotePreviewUrl) return undefined;
    const wsBase = apiBase.replace(/^http/i, 'ws');
    const ws = new WebSocket(`${wsBase}/ws/jobs/${jobId}/preview-watch?token=${encodeURIComponent(token)}`);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data || '{}');
        if (data?.type === 'files_changed' && Array.isArray(data.files) && data.files.length && iframeRef.current && remotePreviewUrl) {
          iframeRef.current.src = `${remotePreviewUrl.replace(/\/$/, '')}/?t=${Date.now()}`;
        }
      } catch {}
    };
    return () => { try { ws.close(); } catch {} };
  }, [jobId, token, apiBase, remotePreviewUrl]);

  const statusColor = useRemote
    ? 'var(--state-success)'
    : status === 'blocked'
      ? 'var(--state-error, #f87171)'
      : status === 'building'
        ? 'var(--state-warning)'
        : hasSandpack
          ? 'var(--state-success)'
          : 'var(--text-muted)';

  const statusLabel = useRemote
    ? 'Live'
    : status === 'blocked'
      ? 'Paused'
      : status === 'building'
        ? 'Taking shape'
        : hasSandpack
          ? 'Preview'
          : 'Next up';

  return (
    <div className="preview-panel">
      <div className="pp-preview-header">
        <div className="pp-preview-title-row">
          <span className="pp-preview-dot" style={{ background: statusColor }} />
          <span className="pp-preview-title">Live Preview</span>
          <span className="pp-preview-status">{devServerUrl && !previewUrl ? 'Hot reload' : statusLabel}</span>
        </div>
        <div className="pp-preview-actions">
          {useRemote && (
            <>
              <button
                type="button"
                className="pp-preview-btn"
                onClick={() => {
                  if (iframeRef.current && remotePreviewUrl) iframeRef.current.src = `${remotePreviewUrl.replace(/\/$/, '')}/?t=${Date.now()}`;
                }}
                title="Refresh preview"
              >
                <RefreshCw size={12} />
              </button>
              <a href={remotePreviewUrl} target="_blank" rel="noopener noreferrer" className="pp-preview-btn" title="Open in new tab">
                <ExternalLink size={12} />
              </a>
            </>
          )}
        </div>
      </div>

      <div className="pp-preview-body">
        <ErrorOverlay
          title={isBootingDevPreview ? 'Starting live preview' : 'Preview issue'}
          message={isBootingDevPreview ? 'Booting a workspace dev server so preview updates without a manual refresh.' : devPreviewError}
          onRetry={jobId && token && apiBase ? () => { setDevServerUrl(null); setDevPreviewError(null); setIsBootingDevPreview(false); setRetryTick((v) => v + 1); } : null}
        />
        {status === 'blocked' && hasSandpack && (
          <div className="pp-preview-blocked-banner" role="status">
            <span className="pp-preview-blocked-title">Preview paused — we&apos;ll continue with you</span>
            <p className="pp-preview-blocked-hint">
              {typeof blockedDetail === 'string' && blockedDetail.trim()
                ? blockedDetail
                : 'Add a short note below — what you see here is the last good snapshot.'}
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
            <span className="pp-preview-blocked-title">Paused for a moment</span>
            <p className="pp-preview-blocked-hint">
              {typeof blockedDetail === 'string' && blockedDetail
                ? blockedDetail
                : 'Send a quick note below to continue — your files may already be ahead in Code.'}
            </p>
          </div>
        )}

        {status === 'building' && !hasSandpack && (
          <div className="pp-preview-building">
            <div className="pp-preview-shimmer" />
            <span className="pp-preview-building-text">Assembling your preview…</span>
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
                Build complete! When your UI files are in the workspace, preview appears here automatically.
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
          <iframe ref={iframeRef} className="pp-preview-iframe" src={remotePreviewUrl} title="Live Preview" />
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
