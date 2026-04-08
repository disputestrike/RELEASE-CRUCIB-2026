import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useAppStore } from '../store/useAppStore';

export default function DashboardPage() {
  const { isAuthenticated, token, logout } = useAuth();
  const notes = useAppStore((s) => s.notes);
  const setNotes = useAppStore((s) => s.setNotes);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>Dashboard</h1>
      <p style={{ color: '#94a3b8', marginBottom: 16, wordBreak: 'break-all' }}>Token: {token.slice(0, 48)}…</p>
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Notes (persisted)"
        rows={4}
        style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #475569', background: '#1e293b', color: '#e2e8f0' }}
      />
      <button type="button" onClick={logout} style={{ marginTop: 12, padding: '8px 14px', borderRadius: 8, background: '#ef4444', color: '#fff', border: 'none', cursor: 'pointer' }}>
        Log out
      </button>
    </div>
  );
}
