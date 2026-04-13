/**
 * PreviewPanel — live preview: remote iframe when URL ready, else Sandpack from editor files.
 * `sandpackIsFallback`: show trust banner when Sandpack boots from a heuristic entry (no App.jsx).
 */
import React from 'react';
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
}) {
  const hasSandpack = sandpackFiles && Object.keys(sandpackFiles).length > 0;
  const useRemote = status === 'ready' && previewUrl;

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
          <span className="pp-preview-status">{statusLabel}</span>
        </div>
        <div className="pp-preview-actions">
          {useRemote && (
            <>
              <button
                type="button"
                className="pp-preview-btn"
                onClick={() => {
                  const iframe = document.querySelector('.pp-preview-iframe');
                  if (iframe) iframe.src = previewUrl;
                }}
                title="Refresh preview"
              >
                <RefreshCw size={12} />
              </button>
              <a href={previewUrl} target="_blank" rel="noopener noreferrer" className="pp-preview-btn" title="Open in new tab">
                <ExternalLink size={12} />
              </a>
            </>
          )}
        </div>
      </div>

      <div className="pp-preview-body">
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
          <div className="pp-preview-idle">
            <span className="pp-preview-idle-text">
              When your UI files are in the workspace, they&apos;ll run here — use Sync in the header if you need a fresh pull.
            </span>
          </div>
        )}

        {useRemote && (
          <iframe className="pp-preview-iframe" src={previewUrl} title="Live Preview" />
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
