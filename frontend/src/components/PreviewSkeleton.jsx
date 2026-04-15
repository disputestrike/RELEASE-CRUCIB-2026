/**
 * PreviewSkeleton — preview never blank
 * Shows skeleton UI while app is building, specific status messages from real events
 */
import React, { useState, useEffect } from 'react';

const STATUS_MESSAGES = {
  queued:    'Preparing build environment…',
  planning:  'Planning your app structure…',
  running:   'Building frontend bundle…',
  frontend:  'Rendering UI components…',
  backend:   'Starting API server…',
  database:  'Connecting database…',
  testing:   'Running quality checks…',
  deploying: 'Starting preview server…',
  live:      'Preview ready',
  failed:    'Preview unavailable — build failed',
};

export default function PreviewSkeleton({ stage = 'running', currentPhase = '', previewUrl = null }) {
  const [dots, setDots] = useState('');
  const statusMsg = STATUS_MESSAGES[currentPhase?.toLowerCase()] ||
                    STATUS_MESSAGES[stage] ||
                    'Building your app…';
  const isLive = stage === 'completed' && previewUrl;

  useEffect(() => {
    if (isLive) return;
    const t = setInterval(() => setDots(d => d.length >= 3 ? '' : d + '.'), 500);
    return () => clearInterval(t);
  }, [isLive]);

  if (isLive) return null; // Let real iframe take over

  return (
    <div style={{
      width: '100%', height: '100%', background: '#fff',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      {/* Fake browser chrome */}
      <div style={{
        padding: '8px 12px', background: '#f9fafb', borderBottom: '1px solid #e5e7eb',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <div style={{ display: 'flex', gap: 4 }}>
          {['#ff5f57','#ffbd2e','#28c840'].map(c => (
            <div key={c} style={{ width: 10, height: 10, borderRadius: '50%', background: c, opacity: 0.4 }} />
          ))}
        </div>
        <div style={{
          flex: 1, height: 22, background: '#f3f4f6', borderRadius: 4,
          display: 'flex', alignItems: 'center', paddingLeft: 10,
        }}>
          <span style={{ fontSize: 11, color: '#9ca3af' }}>
            {stage === 'failed' ? 'Build failed' : 'Building your app' + dots}
          </span>
        </div>
      </div>

      {/* Skeleton content */}
      <div style={{ flex: 1, padding: 16, overflow: 'hidden' }}>
        {/* Nav skeleton */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
          <div style={{ width: 80, height: 12, background: '#f3f4f6', borderRadius: 4 }} />
          <div style={{ flex: 1 }} />
          {[60,48,48].map((w,i) => (
            <div key={i} style={{ width: w, height: 8, background: '#f3f4f6', borderRadius: 4 }} />
          ))}
        </div>

        {/* Hero skeleton */}
        <div style={{
          padding: 20, background: '#f9fafb', borderRadius: 8,
          marginBottom: 16, border: '1px solid #f3f4f6',
        }}>
          <div style={{ width: '60%', height: 16, background: '#e5e7eb', borderRadius: 4, marginBottom: 10 }} />
          <div style={{ width: '40%', height: 10, background: '#f3f4f6', borderRadius: 4, marginBottom: 16 }} />
          <div style={{ width: 80, height: 28, background: '#e5e7eb', borderRadius: 6 }} />
        </div>

        {/* Cards skeleton */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
          {[0,1,2].map(i => (
            <div key={i} style={{
              padding: 14, background: '#f9fafb', borderRadius: 8,
              border: '1px solid #f3f4f6',
            }}>
              <div style={{ width: '70%', height: 10, background: '#e5e7eb', borderRadius: 3, marginBottom: 8 }} />
              <div style={{ width: '90%', height: 8, background: '#f3f4f6', borderRadius: 3, marginBottom: 6 }} />
              <div style={{ width: '60%', height: 8, background: '#f3f4f6', borderRadius: 3 }} />
            </div>
          ))}
        </div>
      </div>

      {/* Status bar */}
      <div style={{
        padding: '8px 16px', borderTop: '1px solid #f3f4f6', background: '#fff',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        {stage !== 'failed' && (
          <div style={{
            width: 6, height: 6, borderRadius: '50%',
            background: '#10b981', animation: 'pulse 1.5s infinite',
          }} />
        )}
        <span style={{ fontSize: 11, color: '#9ca3af' }}>
          {statusMsg}{stage !== 'failed' && dots}
        </span>
      </div>
    </div>
  );
}
