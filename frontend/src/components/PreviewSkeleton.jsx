import React from 'react';

const STATUS_MESSAGES = {
  queued: 'Thinking',
  planning: 'Planning the workspace',
  running: 'Building the workspace',
  frontend: 'Rendering the interface',
  backend: 'Connecting the backend',
  database: 'Preparing the data layer',
  testing: 'Checking the workspace',
  deploying: 'Starting the preview',
  live: 'Preview ready',
  failed: 'Repairing preview',
};

export default function PreviewSkeleton({ stage = 'running', currentPhase = '', previewUrl = null }) {
  const statusMsg = STATUS_MESSAGES[currentPhase?.toLowerCase()] ||
                    STATUS_MESSAGES[stage] ||
                    'Thinking';
  const isLive = stage === 'completed' && previewUrl;

  if (isLive) return null;

  return (
    <div style={{
      width: '100%', height: '100%', background: '#fff',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      <div style={{
        padding: '8px 12px', background: '#f9f9f9', borderBottom: '1px solid #e5e5e5',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <div style={{ display: 'flex', gap: 4 }}>
          {['#d8d8d8', '#c8c8c8', '#b8b8b8'].map(c => (
            <div key={c} style={{ width: 10, height: 10, borderRadius: '50%', background: c }} />
          ))}
        </div>
        <div style={{
          flex: 1, height: 22, background: '#f3f3f3', borderRadius: 4,
          display: 'flex', alignItems: 'center', paddingLeft: 10,
        }}>
          <span style={{ fontSize: 11, color: '#777777' }}>
            {stage === 'failed' ? 'Repairing preview' : 'Thinking'}
          </span>
        </div>
      </div>

      <div style={{ flex: 1, padding: 16, overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
          <div style={{ width: 80, height: 12, background: '#f3f3f3', borderRadius: 4 }} />
          <div style={{ flex: 1 }} />
          {[60, 48, 48].map((w, i) => (
            <div key={i} style={{ width: w, height: 8, background: '#f3f3f3', borderRadius: 4 }} />
          ))}
        </div>

        <div style={{
          padding: 20, background: '#f9f9f9', borderRadius: 8,
          marginBottom: 16, border: '1px solid #f0f0f0',
        }}>
          <div style={{ width: '60%', height: 16, background: '#e5e5e5', borderRadius: 4, marginBottom: 10 }} />
          <div style={{ width: '40%', height: 10, background: '#f3f3f3', borderRadius: 4, marginBottom: 16 }} />
          <div style={{ width: 80, height: 28, background: '#e5e5e5', borderRadius: 6 }} />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
          {[0, 1, 2].map(i => (
            <div key={i} style={{
              padding: 14, background: '#f9f9f9', borderRadius: 8,
              border: '1px solid #f0f0f0',
            }}>
              <div style={{ width: '70%', height: 10, background: '#e5e5e5', borderRadius: 3, marginBottom: 8 }} />
              <div style={{ width: '90%', height: 8, background: '#f3f3f3', borderRadius: 3, marginBottom: 6 }} />
              <div style={{ width: '60%', height: 8, background: '#f3f3f3', borderRadius: 3 }} />
            </div>
          ))}
        </div>
      </div>

      <div style={{
        padding: '8px 16px', borderTop: '1px solid #f0f0f0', background: '#fff',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        {stage !== 'failed' && (
          <div style={{
            width: 6, height: 6, borderRadius: '50%',
            background: '#777777', animation: 'pulse 1.5s infinite',
          }} />
        )}
        <span style={{ fontSize: 11, color: '#777777' }}>{statusMsg}</span>
      </div>
    </div>
  );
}
