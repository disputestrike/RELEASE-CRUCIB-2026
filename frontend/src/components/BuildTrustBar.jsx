/**
 * BuildTrustBar — persistent trust signals always visible
 * Quality score, security status, deploy readiness, errors
 * Shown in header when a build is active or complete
 */
import React from 'react';

export default function BuildTrustBar({ quality = 0, security = null, errors = 0, deployReady = false, stage = 'input' }) {
  if (stage === 'input') return null;

  const qColor = quality >= 80 ? '#10b981' : quality >= 60 ? '#f59e0b' : quality > 0 ? '#ef4444' : '#9ca3af';
  const secIcon = security === 'passed' ? '✓' : security === 'failed' ? '✗' : security === 'scanning' ? '⟳' : '–';
  const secColor = security === 'passed' ? '#10b981' : security === 'failed' ? '#ef4444' : '#9ca3af';

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12, height: 28,
      padding: '0 12px', background: '#fafafa', borderBottom: '1px solid #f0f0f0',
      fontSize: 11, color: '#6b7280',
    }}>
      {/* Quality */}
      {quality > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ color: qColor, fontWeight: 600 }}>Q {quality}/100</span>
        </div>
      )}

      {/* Security */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <span style={{ color: secColor }}>Security {secIcon}</span>
      </div>

      {/* Errors */}
      {errors > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#ef4444' }}>
          <span>⚠ {errors} issue{errors !== 1 ? 's' : ''}</span>
        </div>
      )}

      {errors === 0 && stage === 'completed' && (
        <div style={{ color: '#10b981' }}>✓ No issues</div>
      )}

      {/* Deploy readiness */}
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4 }}>
        <div style={{
          width: 6, height: 6, borderRadius: '50%',
          background: deployReady ? '#10b981' : stage === 'running' ? '#f59e0b' : '#e5e7eb',
        }} />
        <span style={{ color: deployReady ? '#10b981' : '#9ca3af' }}>
          {deployReady ? 'Deploy ready' : stage === 'running' ? 'Building' : stage === 'failed' ? 'Build failed' : 'Pending'}
        </span>
      </div>
    </div>
  );
}
