/**
 * PreviewPanel — live preview: remote iframe when URL ready, else Sandpack from editor files.
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
}) {
  const hasSandpack = sandpackFiles && Object.keys(sandpackFiles).length > 0;
  const useRemote = status === 'ready' && previewUrl;

  const statusColor = useRemote
    ? 'var(--state-success)'
    : status === 'building'
      ? 'var(--state-warning)'
      : hasSandpack
        ? 'var(--state-success)'
        : 'var(--text-muted)';

  const statusLabel = useRemote
    ? 'Live'
    : status === 'building'
      ? 'Building'
      : hasSandpack
        ? 'Sandbox'
        : 'Idle';

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
        {!useRemote && status === 'idle' && !hasSandpack && (
          <div className="pp-preview-idle">
            <span className="pp-preview-idle-text">Preview will appear after build completes, or run an iterative build to load Sandpack.</span>
          </div>
        )}

        {status === 'building' && !hasSandpack && (
          <div className="pp-preview-building">
            <div className="pp-preview-shimmer" />
            <span className="pp-preview-building-text">Building...</span>
          </div>
        )}

        {useRemote && (
          <iframe
            className="pp-preview-iframe"
            src={previewUrl}
            title="Live Preview"
            style={{ width: '100%', height: '100%', border: 'none' }}
          />
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
