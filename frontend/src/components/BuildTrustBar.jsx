import React from 'react';

export default function BuildTrustBar({ quality = 0, security = null, errors = 0, deployReady = false, stage = 'input' }) {
  if (stage === 'input') return null;

  const statusLabel = deployReady
    ? 'Ready to preview'
    : stage === 'running'
      ? 'Working'
      : stage === 'failed'
        ? 'Repairing'
        : 'Pending';
  const securityLabel = security === 'passed'
    ? 'Security checked'
    : security === 'failed'
      ? 'Security needs review'
      : security === 'scanning'
        ? 'Security checking'
        : 'Security pending';

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12, height: 28,
      padding: '0 12px', background: '#fafafa', borderBottom: '1px solid #e5e5e5',
      fontSize: 11, color: '#555555',
    }}>
      {quality > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ color: '#111111', fontWeight: 600 }}>Quality {quality}/100</span>
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <span>{securityLabel}</span>
      </div>

      {errors > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#555555' }}>
          <span>{errors} item{errors !== 1 ? 's' : ''} need another pass</span>
        </div>
      )}

      {errors === 0 && stage === 'completed' && (
        <div style={{ color: '#111111' }}>No open items</div>
      )}

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4 }}>
        <div style={{
          width: 6, height: 6, borderRadius: '50%',
          background: deployReady ? '#111111' : stage === 'running' ? '#777777' : '#d8d8d8',
        }} />
        <span style={{ color: deployReady ? '#111111' : '#777777' }}>{statusLabel}</span>
      </div>
    </div>
  );
}
