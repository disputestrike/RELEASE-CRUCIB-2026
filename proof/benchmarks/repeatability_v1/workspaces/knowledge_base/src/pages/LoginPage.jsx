import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');

  if (isAuthenticated) {
    navigate('/dashboard', { replace: true });
    return null;
  }

  return (
    <div style={{ maxWidth: 400 }}>
      <h1 style={{ marginBottom: 12 }}>Login (demo)</h1>
      <p style={{ color: '#94a3b8', fontSize: 14, marginBottom: 16 }}>
        Client-only token stored in localStorage. CRUCIB_INCOMPLETE: call your API.
      </p>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Display name"
        style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #475569', background: '#1e293b', color: '#fff', marginBottom: 12 }}
      />
      <button
        type="button"
        onClick={() => { login(name || 'builder'); navigate('/dashboard'); }}
        style={{ padding: '10px 18px', borderRadius: 8, background: '#22c55e', color: '#0f172a', border: 'none', fontWeight: 600, cursor: 'pointer' }}
      >
        Sign in (demo)
      </button>
    </div>
  );
}
