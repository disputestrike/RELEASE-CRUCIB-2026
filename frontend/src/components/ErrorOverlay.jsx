import React from 'react';

export default function ErrorOverlay({ title = 'Preview issue', message, onRetry }) {
  if (!message) return null;
  return (
    <div style={{
      position: 'absolute', inset: 12, zIndex: 5, borderRadius: 16,
      background: 'rgba(15, 23, 42, 0.88)', color: '#fff', border: '1px solid rgba(255,255,255,0.14)',
      padding: 16, display: 'flex', flexDirection: 'column', gap: 10, justifyContent: 'flex-end'
    }}>
      <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', opacity: 0.7 }}>{title}</div>
      <div style={{ fontSize: 14, lineHeight: 1.5 }}>{message}</div>
      {onRetry ? <div><button type="button" onClick={onRetry} style={{ border: 'none', borderRadius: 10, padding: '8px 12px', cursor: 'pointer' }}>Retry preview</button></div> : null}
    </div>
  );
}
