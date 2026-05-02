/**
 * UserMemoryPanel.jsx — Phase 6
 * Compact panel for reading/editing user memory context (company, stack, brand color, notes).
 * Mounts in UnifiedWorkspace settings drawer or sidebar.
 */
import { useState, useEffect, useCallback } from 'react';
import { Brain, Palette, Building2, Layers, FileText, Check, Loader2, X } from 'lucide-react';
import './UserMemoryPanel.css';

const STACK_OPTIONS = [
  { value: '',            label: 'Auto-detect from history' },
  { value: 'react_fastapi', label: 'React + FastAPI (Python)' },
  { value: 'react_only',   label: 'React (frontend only)' },
  { value: 'next_js',      label: 'Next.js' },
  { value: 'vue_fastapi',  label: 'Vue + FastAPI' },
];

export default function UserMemoryPanel({ token, apiBase, onClose }) {
  const API = apiBase || '';
  const [profile, setProfile]   = useState(null);
  const [saving, setSaving]     = useState(false);
  const [saved, setSaved]       = useState(false);
  const [loading, setLoading]   = useState(true);
  const [form, setForm]         = useState({
    company_name: '', display_name: '', brand_color: '',
    preferred_stack: '', custom_notes: '',
  });

  const headers = token
    ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
    : { 'Content-Type': 'application/json' };

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    fetch(`${API}/api/users/me/memory`, { headers })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data) {
          setProfile(data);
          setForm({
            company_name:    data.company_name    || '',
            display_name:    data.display_name    || '',
            brand_color:     data.brand_color     || '',
            preferred_stack: data.preferred_stack || '',
            custom_notes:    data.custom_notes    || '',
          });
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [token]); // eslint-disable-line

  const save = useCallback(async () => {
    if (!token) return;
    setSaving(true);
    try {
      const r = await fetch(`${API}/api/users/me/memory`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify(form),
      });
      if (r.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 2200);
      }
    } catch (_) {}
    finally { setSaving(false); }
  }, [token, form]); // eslint-disable-line

  const field = (key, val) => setForm(f => ({ ...f, [key]: val }));

  if (loading) {
    return (
      <div className="ump-root ump-loading">
        <Loader2 size={18} className="ump-spin" />
        <span>Loading profile…</span>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="ump-root ump-empty">
        <Brain size={20} />
        <p>Sign in to enable memory context — CrucibAI will remember your stack, brand color, and project details across every build.</p>
      </div>
    );
  }

  return (
    <div className="ump-root">
      <div className="ump-header">
        <Brain size={15} />
        <span className="ump-title">Build Memory</span>
        <span className="ump-subtitle">Injected into every build prompt</span>
        {onClose && (
          <button className="ump-close" onClick={onClose} aria-label="Close"><X size={14} /></button>
        )}
      </div>

      {profile?.build_count > 0 && (
        <div className="ump-stat-row">
          <span className="ump-stat">{profile.build_count} builds logged</span>
          {profile.inferred_stack && !profile.preferred_stack && (
            <span className="ump-inferred">Auto-detected: {profile.inferred_stack.replace(/_/g,' ')}</span>
          )}
        </div>
      )}

      <div className="ump-fields">
        <label className="ump-field">
          <span className="ump-label"><Building2 size={11} />Company / project name</span>
          <input
            className="ump-input"
            type="text"
            placeholder="Acme Inc."
            value={form.company_name}
            onChange={e => field('company_name', e.target.value)}
          />
        </label>

        <label className="ump-field">
          <span className="ump-label"><Layers size={11} />Preferred stack</span>
          <select
            className="ump-select"
            value={form.preferred_stack}
            onChange={e => field('preferred_stack', e.target.value)}
          >
            {STACK_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>

        <label className="ump-field">
          <span className="ump-label"><Palette size={11} />Brand color</span>
          <div className="ump-color-row">
            <input
              className="ump-input ump-input--color-text"
              type="text"
              placeholder="#6366f1"
              value={form.brand_color}
              onChange={e => field('brand_color', e.target.value)}
            />
            <input
              className="ump-color-swatch"
              type="color"
              value={form.brand_color || '#6366f1'}
              onChange={e => field('brand_color', e.target.value)}
              title="Pick brand color"
            />
          </div>
        </label>

        <label className="ump-field">
          <span className="ump-label"><FileText size={11} />Project notes</span>
          <textarea
            className="ump-textarea"
            placeholder="e.g. multi-tenant SaaS, dark mode only, uses Stripe for billing…"
            value={form.custom_notes}
            onChange={e => field('custom_notes', e.target.value)}
            rows={3}
          />
        </label>
      </div>

      <button
        className={`ump-save ${saved ? 'ump-save--saved' : ''}`}
        onClick={save}
        disabled={saving}
      >
        {saving ? <Loader2 size={13} className="ump-spin" /> : saved ? <Check size={13} /> : null}
        {saved ? 'Saved' : saving ? 'Saving…' : 'Save context'}
      </button>
    </div>
  );
}
