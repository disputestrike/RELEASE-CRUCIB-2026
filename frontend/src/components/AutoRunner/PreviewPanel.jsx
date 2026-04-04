/**
 * PreviewPanel — persistent live preview iframe panel.
 * States: idle (grid bg), building (shimmer), ready (iframe).
 * Props: previewUrl, status ('idle' | 'building' | 'ready')
 */
import React from 'react';
import { RefreshCw, ExternalLink } from 'lucide-react';
import './PreviewPanel.css';

export default function PreviewPanel({ previewUrl, status = 'idle' }) {
  const statusColor =
    status === 'ready' ? 'var(--state-success)' :
    status === 'building' ? 'var(--state-warning)' :
    'var(--text-muted)';

  const statusLabel =
    status === 'ready' ? 'Live' :
    status === 'building' ? 'Building' :
    'Idle';

  return (
    <div className="preview-panel">
      <div className="pp-preview-header">
        <div className="pp-preview-title-row">
          <span className="pp-preview-dot" style={{ background: statusColor }} />
          <span className="pp-preview-title">Live Preview</span>
          <span className="pp-preview-status">{statusLabel}</span>
        </div>
        <div className="pp-preview-actions">
          {status === 'ready' && previewUrl && (
            <>
              <button
                className="pp-preview-btn"
                onClick={() => {
                  const iframe = document.querySelector('.pp-preview-iframe');
                  if (iframe) iframe.src = previewUrl;
                }}
                title="Refresh preview"
              >
                <RefreshCw size={12} />
              </button>
              <a
                href={previewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="pp-preview-btn"
                title="Open in new tab"
              >
                <ExternalLink size={12} />
              </a>
            </>
          )}
        </div>
      </div>

      <div className="pp-preview-body">
        {status === 'idle' && (
          <div className="pp-preview-idle">
            <span className="pp-preview-idle-text">
              Preview will appear after build completes
            </span>
          </div>
        )}

        {status === 'building' && (
          <div className="pp-preview-building">
            <div className="pp-preview-shimmer" />
            <span className="pp-preview-building-text">Building...</span>
          </div>
        )}

        {status === 'ready' && previewUrl && (
          <iframe
            className="pp-preview-iframe"
            src={previewUrl}
            title="Live Preview"
            style={{ width: '100%', height: '100%', border: 'none' }}
          />
        )}
      </div>
    </div>
  );
}
