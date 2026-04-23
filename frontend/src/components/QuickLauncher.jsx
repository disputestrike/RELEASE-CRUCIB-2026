/** CF28 — QuickLauncher: global Cmd/Ctrl+K palette for navigation + actions. */
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const COMMANDS = [
  { id: 'go-workspace',   label: 'Go to Workspace',         path: '/app/workspace' },
  { id: 'go-projects',    label: 'Go to Projects',          path: '/app/dashboard' },
  { id: 'go-agents',      label: 'Go to Agents',            path: '/app/agents' },
  { id: 'go-skills',      label: 'Go to Skills',            path: '/app/skills' },
  { id: 'go-marketplace', label: 'Go to Marketplace',       path: '/app/marketplace' },
  { id: 'go-benchmarks',  label: 'Go to Benchmarks',        path: '/app/benchmarks' },
  { id: 'go-changelog',   label: 'Go to Changelog',         path: '/app/changelog' },
  { id: 'go-cost',        label: 'Go to Cost Center',       path: '/app/cost' },
  { id: 'go-doctor',      label: 'Run Doctor diagnostics',  path: '/app/doctor' },
  { id: 'go-developer',   label: 'Go to Developer Portal',  path: '/app/developer' },
  { id: 'go-settings',    label: 'Open Settings',           path: '/app/settings' },
];

export default function QuickLauncher() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const [hoverIdx, setHoverIdx] = useState(0);

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        setOpen((v) => !v);
        setQ(''); setHoverIdx(0);
      } else if (open && e.key === 'Escape') {
        setOpen(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const filtered = useMemo(() => {
    const needle = q.toLowerCase().trim();
    if (!needle) return COMMANDS;
    return COMMANDS.filter((c) => c.label.toLowerCase().includes(needle) || c.id.includes(needle));
  }, [q]);

  const activate = (cmd) => { setOpen(false); if (cmd?.path) navigate(cmd.path); };

  const onInputKey = (e) => {
    if (!filtered.length) return;
    if (e.key === 'Enter')      activate(filtered[hoverIdx] || filtered[0]);
    else if (e.key === 'ArrowDown') { e.preventDefault(); setHoverIdx((i) => Math.min(filtered.length - 1, i + 1)); }
    else if (e.key === 'ArrowUp')   { e.preventDefault(); setHoverIdx((i) => Math.max(0, i - 1)); }
  };

  if (!open) return null;
  return (
    <div
      data-testid="quick-launcher"
      role="dialog"
      aria-modal="true"
      aria-label="Quick launcher"
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: 96, zIndex: 9999,
      }}
      onClick={() => setOpen(false)}
    >
      <div onClick={(e) => e.stopPropagation()} style={{
        background: '#fff', borderRadius: 12, width: 'min(560px, 92vw)',
        boxShadow: '0 30px 60px rgba(0,0,0,0.3)', overflow: 'hidden',
        fontFamily: '-apple-system, system-ui, sans-serif',
      }}>
        <input
          autoFocus
          type="text"
          value={q}
          onChange={(e) => { setQ(e.target.value); setHoverIdx(0); }}
          onKeyDown={onInputKey}
          placeholder="Jump to anywhere…"
          style={{ width: '100%', border: 0, outline: 0, padding: '16px 20px', fontSize: 16 }}
        />
        <div style={{ borderTop: '1px solid #e4e4e7', maxHeight: 400, overflowY: 'auto' }}>
          {filtered.length === 0 ? (
            <div style={{ padding: 20, color: '#a1a1aa', fontSize: 14 }}>No matches.</div>
          ) : filtered.map((cmd, i) => (
            <button
              key={cmd.id}
              type="button"
              onClick={() => activate(cmd)}
              onMouseEnter={() => setHoverIdx(i)}
              style={{
                display: 'block', width: '100%', textAlign: 'left',
                padding: '10px 20px', border: 0, background: hoverIdx === i ? '#f4f4f5' : '#fff',
                color: '#1a1a1a', fontSize: 14, cursor: 'pointer',
              }}
            >{cmd.label}</button>
          ))}
        </div>
        <div style={{ borderTop: '1px solid #e4e4e7', padding: '8px 16px', fontSize: 12, color: '#71717a' }}>
          ⌘/Ctrl+K to toggle · ↵ select · ESC close
        </div>
      </div>
    </div>
  );
}
