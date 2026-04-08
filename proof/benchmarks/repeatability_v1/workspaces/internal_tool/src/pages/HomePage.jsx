import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store/useAppStore';

export default function HomePage() {
  const navigate = useNavigate();
  const theme = useAppStore((s) => s.theme);
  const setTheme = useAppStore((s) => s.setTheme);
  const goal = "Build an internal operations tool with auth, task dashboard, team page, persisted operations notes, and deployment readiness.";

  return (
    <div>
      <h1 style={{ fontSize: '1.75rem', marginBottom: 12 }}>Home</h1>
      <p style={{ color: '#94a3b8', lineHeight: 1.6, marginBottom: 16 }}>{goal}</p>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 20 }}>
        <button
          type="button"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid #475569', background: '#1e293b', color: '#e2e8f0', cursor: 'pointer' }}
        >
          Toggle theme ({theme}) — persisted
        </button>
        <button
          type="button"
          onClick={() => navigate('/dashboard')}
          style={{ padding: '8px 14px', borderRadius: 8, background: '#3b82f6', color: '#fff', border: 'none', cursor: 'pointer' }}
        >
          Go to Dashboard
        </button>
      </div>
      <p style={{ fontSize: 13, color: '#64748b' }}>Theme and routes sync to localStorage via Zustand persist.</p>
    </div>
  );
}
