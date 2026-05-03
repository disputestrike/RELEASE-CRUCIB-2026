/**
 * WorkspaceOnboarding — first-run experience
 * User sees power BEFORE typing — shows what CrucibAI does
 * Animated demo of building, not just a text prompt
 */
import React, { useState, useEffect } from 'react';

const DEMO_MESSAGES = [
  { text: 'Mapping product structure…', delay: 0 },
  { text: 'Choosing stack: React + FastAPI + Postgres', delay: 1200 },
  { text: 'Building dashboard with analytics…', delay: 2400 },
  { text: 'Connecting authentication…', delay: 3400 },
  { text: '✓ Auth ready — 12 tables created', delay: 4400 },
  { text: 'Wiring PayPal billing integration...', delay: 5200 },
  { text: '✓ Build complete — quality 88/100', delay: 6200 },
];

const SUGGESTIONS = [
  'Build a SaaS dashboard with PayPal billing',
  'Create a project management tool with teams',
  'Build a CRM with email automation',
  'Create a mobile app with auth and notifications',
];

export default function WorkspaceOnboarding({ onStart }) {
  const [visibleMessages, setVisibleMessages] = useState([]);
  const [activeSuggestion, setActiveSuggestion] = useState(null);

  useEffect(() => {
    let active = true;
    DEMO_MESSAGES.forEach(msg => {
      setTimeout(() => {
        if (!active) return;
        setVisibleMessages(prev => [...prev, msg.text]);
      }, msg.delay + 400);
    });
    return () => { active = false; };
  }, []);

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', padding: '40px 24px', maxWidth: 600, margin: '0 auto',
      minHeight: '60vh',
    }}>
      {/* Brand */}
      <div style={{ marginBottom: 32, textAlign: 'center' }}>
        <div style={{
          width: 48, height: 48, borderRadius: 12, background: '#f0fdf4',
          border: '1px solid #bbf7d0', display: 'flex', alignItems: 'center',
          justifyContent: 'center', margin: '0 auto 16px', fontSize: 22,
        }}>⬡</div>
        <div style={{ fontSize: 22, fontWeight: 700, color: '#111', marginBottom: 6 }}>
          What do you want to build?
        </div>
        <div style={{ fontSize: 13, color: '#9ca3af' }}>
          Describe your app — CrucibAI builds, runs, and automates it
        </div>
      </div>

      {/* Live demo strip */}
      <div style={{
        width: '100%', background: '#fafafa', border: '1px solid #e5e7eb',
        borderRadius: 10, padding: 14, marginBottom: 24, minHeight: 88,
        fontFamily: 'monospace',
      }}>
        <div style={{ fontSize: 10, color: '#9ca3af', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>
          Example — SaaS Dashboard
        </div>
        {visibleMessages.map((msg, i) => (
          <div key={i} style={{
            fontSize: 11, color: i === visibleMessages.length - 1 ? '#111' : '#6b7280',
            marginBottom: 3, animation: 'fadeIn 0.3s ease',
          }}>
            {msg}
          </div>
        ))}
        {visibleMessages.length < DEMO_MESSAGES.length && (
          <div style={{ display: 'flex', gap: 3, marginTop: 4 }}>
            {[0,1,2].map(i => (
              <div key={i} style={{
                width: 4, height: 4, borderRadius: '50%', background: '#10b981',
                animation: `bounce 1s ${i * 0.2}s infinite`,
              }} />
            ))}
          </div>
        )}
      </div>

      {/* Suggestion chips */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, width: '100%', marginBottom: 8 }}>
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            onClick={() => { setActiveSuggestion(i); onStart?.(s); }}
            style={{
              padding: '10px 14px', background: '#fff', textAlign: 'left',
              border: `1px solid ${activeSuggestion === i ? '#10b981' : '#e5e7eb'}`,
              borderRadius: 8, fontSize: 12, color: '#374151', cursor: 'pointer',
              transition: 'all 0.15s', lineHeight: 1.4,
            }}
          >
            {s}
          </button>
        ))}
      </div>

      <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 8 }}>
        Or describe your own below ↓
      </div>
    </div>
  );
}
