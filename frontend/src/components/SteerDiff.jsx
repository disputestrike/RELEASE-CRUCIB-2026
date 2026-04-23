/**
 * SteerDiff — shows before/after plan when user steers mid-build
 * This is the "I'm controlling a live system" moment
 */
import React from 'react';

export default function SteerDiff({ before = [], after = [], message = '', onDismiss }) {
  if (!message && !before.length && !after.length) return null;

  return (
    <div style={{
      margin: '8px 0', padding: '10px 14px',
      background: '#f0fdf4', border: '1px solid #bbf7d0',
      borderRadius: 8, fontSize: 12,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ color: '#16a34a', fontWeight: 600 }}>✓ Build updated</span>
        </div>
        {onDismiss && (
          <button onClick={onDismiss} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', fontSize: 14 }}>×</button>
        )}
      </div>

      {message && (
        <div style={{ color: '#374151', marginBottom: before.length ? 8 : 0 }}>{message}</div>
      )}

      {(before.length > 0 || after.length > 0) && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          {before.length > 0 && (
            <div>
              <div style={{ fontSize: 10, color: '#9ca3af', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>Before</div>
              {before.map((item, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#9ca3af', marginBottom: 2, textDecoration: 'line-through' }}>
                  <span>{i + 1}.</span><span>{item}</span>
                </div>
              ))}
            </div>
          )}
          {after.length > 0 && (
            <div>
              <div style={{ fontSize: 10, color: '#9ca3af', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>After</div>
              {after.map((item, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#16a34a', marginBottom: 2 }}>
                  <span>{i + 1}.</span><span>{item}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
