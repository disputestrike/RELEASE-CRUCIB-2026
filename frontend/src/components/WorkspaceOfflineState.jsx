/**
 * WorkspaceOfflineState — shown when engine is disconnected
 * Never shows blank right pane or fake "System initializing..."
 * Shows truthful state with auto-retry countdown
 */
import React, { useState, useEffect } from 'react';

export default function WorkspaceOfflineState({ onRetry, lastEvent = null, retryAfterSecs = 5 }) {
  const [countdown, setCountdown] = useState(retryAfterSecs);
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    if (countdown <= 0) {
      setRetrying(true);
      setTimeout(() => {
        onRetry?.();
        setCountdown(retryAfterSecs);
        setRetrying(false);
      }, 1000);
      return;
    }
    const t = setTimeout(() => setCountdown(c => c - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  return (
    <div style={{
      height: '100%', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      background: '#fafafa', padding: 32, textAlign: 'center',
    }}>
      {/* Status indicator */}
      <div style={{
        width: 44, height: 44, borderRadius: 12, background: '#f3f4f6',
        border: '1px solid #e5e7eb', display: 'flex', alignItems: 'center',
        justifyContent: 'center', fontSize: 20, marginBottom: 16,
      }}>
        {retrying ? '⟳' : '⊘'}
      </div>

      <div style={{ fontSize: 14, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
        {retrying ? 'Reconnecting…' : 'Engine disconnected'}
      </div>

      <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 16, lineHeight: 1.6 }}>
        {retrying
          ? 'Attempting to reconnect to the build engine'
          : `Retrying in ${countdown}s — your work is saved`}
      </div>

      {lastEvent && (
        <div style={{
          fontSize: 11, color: '#6b7280', marginBottom: 16,
          background: '#f9fafb', border: '1px solid #e5e7eb',
          borderRadius: 8, padding: '6px 12px',
        }}>
          Last event: {lastEvent}
        </div>
      )}

      <button
        onClick={() => { setCountdown(0); }}
        style={{
          padding: '8px 20px', background: '#fff', color: '#374151',
          border: '1px solid #d1d5db', borderRadius: 8, fontSize: 12,
          cursor: 'pointer', fontWeight: 500,
        }}
      >
        Retry now
      </button>
    </div>
  );
}
