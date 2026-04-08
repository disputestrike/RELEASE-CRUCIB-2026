import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';

export default function ShellLayout() {
  const link = (to, label) => (
    <NavLink
      to={to}
      style={({ isActive }) => ({
        padding: '6px 12px',
        borderRadius: 8,
        textDecoration: 'none',
        color: isActive ? '#fff' : '#94a3b8',
        background: isActive ? 'rgba(59,130,246,0.35)' : 'transparent',
        border: '1px solid rgba(148,163,184,0.25)',
      })}
    >
      {label}
    </NavLink>
  );

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: '#e2e8f0', fontFamily: 'Inter, system-ui, sans-serif' }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 20px', borderBottom: '1px solid rgba(148,163,184,0.2)' }}>
        <strong style={{ marginRight: 12 }}>CrucibAI App</strong>
        <nav style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {link('/', 'Home')}
          {link('/login', 'Login')}
          {link('/dashboard', 'Dashboard')}
          {link('/team', 'Team')}
          {/* CRUCIB_ROUTE_ANCHOR */}
        </nav>
      </header>
      <main style={{ padding: '28px 20px', maxWidth: 900, margin: '0 auto' }}>
        <Outlet />
      </main>
    </div>
  );
}
