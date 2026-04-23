import { useState, useEffect } from 'react';
import {
  Bot, Plus, Trash2, CheckCircle, Edit2, X, Save, Mic,
  Globe, MessageSquare, User, Sparkles, ChevronDown
} from 'lucide-react';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import axios from 'axios';

const T = {
  bg:      'var(--theme-bg)',
  surface: 'var(--theme-surface)',
  border:  'rgba(255,255,255,0.12)',
  text:    'var(--theme-text)',
  muted:   'var(--theme-muted)',
  accent:  '#1A1A1A',
  success: '#10b981',
  danger:  '#ef4444',
  input:   'var(--theme-input, rgba(255,255,255,0.06))',
};

const TONES = ['Professional', 'Friendly', 'Casual', 'Expert', 'Custom'];
const VOICES = ['Default', 'Formal', 'Conversational'];
const LANGUAGES = ['English', 'Spanish', 'French', 'German', 'Portuguese'];

const emptyForm = {
  name: '', description: '', tone: 'Professional',
  system_prompt: '', voice: 'Default', language: 'English', avatar_url: ''
};

const Badge = ({ children, color }) => (
  <span style={{
    display: 'inline-block',
    padding: '2px 10px',
    borderRadius: 20,
    fontSize: 11,
    fontWeight: 600,
    background: color || 'rgba(255,255,255,0.08)',
    color: T.text,
  }}>{children}</span>
);

const toneColor = (tone) => {
  const map = { Professional: '#404040', Friendly: '#525252', Casual: '#737373', Expert: '#A3A3A3', Custom: '#1A1A1A' };
  return map[tone] || T.accent;
};

const Inp = ({ value, onChange, placeholder, type = 'text' }) => (
  <input
    type={type}
    value={value}
    onChange={onChange}
    placeholder={placeholder}
    style={{
      width: '100%', boxSizing: 'border-box',
      padding: '9px 12px',
      background: T.input,
      border: `1.5px solid ${T.border}`,
      borderRadius: 8,
      color: T.text,
      fontSize: 13,
      outline: 'none',
    }}
  />
);

const Sel = ({ value, onChange, options }) => (
  <select
    value={value}
    onChange={onChange}
    style={{
      width: '100%', boxSizing: 'border-box',
      padding: '9px 12px',
      background: T.input,
      border: `1.5px solid ${T.border}`,
      borderRadius: 8,
      color: T.text,
      fontSize: 13,
      outline: 'none',
      cursor: 'pointer',
    }}
  >
    {options.map(o => <option key={o} value={o}>{o}</option>)}
  </select>
);

const Fld = ({ label, children }) => (
  <div style={{ marginBottom: 14 }}>
    <p style={{ fontSize: 11, fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }}>{label}</p>
    {children}
  </div>
);

export default function StudioPage() {
  const { token } = useAuth();
  const [personas, setPersonas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [panelOpen, setPanelOpen] = useState(false);
  const [editing, setEditing] = useState(null); // persona id or null
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [activating, setActivating] = useState(null);

  const headers = { Authorization: 'Bearer ' + token };

  const fetchPersonas = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API}/personas`, { headers });
      setPersonas(res.data?.personas || res.data || []);
    } catch (e) {
      setError('Failed to load personas.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchPersonas(); }, []);

  const openNew = () => {
    setEditing(null);
    setForm(emptyForm);
    setPanelOpen(true);
  };

  const openEdit = (persona) => {
    setEditing(persona.id);
    setForm({
      name: persona.name || '',
      description: persona.description || '',
      tone: persona.tone || 'Professional',
      system_prompt: persona.system_prompt || '',
      voice: persona.voice || 'Default',
      language: persona.language || 'English',
      avatar_url: persona.avatar_url || '',
    });
    setPanelOpen(true);
  };

  const handleSave = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      if (editing) {
        await axios.put(`${API}/personas/${editing}`, form, { headers });
      } else {
        await axios.post(`${API}/personas`, form, { headers });
      }
      setPanelOpen(false);
      setEditing(null);
      setForm(emptyForm);
      fetchPersonas();
    } catch (e) {
      setError('Failed to save persona.');
    } finally {
      setSaving(false);
    }
  };

  const handleActivate = async (id) => {
    setActivating(id);
    try {
      await axios.post(`${API}/personas/${id}/activate`, {}, { headers });
      setPersonas(prev => prev.map(p => ({ ...p, is_active: p.id === id })));
    } catch (e) {
      setError('Failed to activate persona.');
    } finally {
      setActivating(null);
    }
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`${API}/personas/${id}`, { headers });
      setPersonas(prev => prev.filter(p => p.id !== id));
      setDeleteConfirm(null);
    } catch (e) {
      setError('Failed to delete persona.');
    }
  };

  const f = (key) => (e) => setForm(prev => ({ ...prev, [key]: e.target.value }));

  return (
    <div style={{ minHeight: '100vh', background: T.bg, color: T.text, fontFamily: 'inherit' }}>
      {/* Header */}
      <div style={{ padding: '28px 32px 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(224,90,37,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Bot size={20} style={{ color: T.accent }} />
          </div>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Studio</h1>
            <p style={{ fontSize: 13, color: T.muted, margin: 0 }}>Create and manage AI personas</p>
          </div>
        </div>
        <button
          onClick={openNew}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '9px 18px', borderRadius: 10, background: T.accent, color: '#fff', fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer' }}
        >
          <Plus size={15} /> New Persona
        </button>
      </div>

      {error && (
        <div style={{ margin: '16px 32px', padding: '10px 14px', background: 'rgba(239,68,68,0.1)', border: `1px solid ${T.danger}`, borderRadius: 8, color: T.danger, fontSize: 13 }}>
          {error}
          <button onClick={() => setError('')} style={{ float: 'right', background: 'none', border: 'none', color: T.danger, cursor: 'pointer' }}><X size={14} /></button>
        </div>
      )}

      {/* Content */}
      <div style={{ padding: '24px 32px' }}>
        {loading ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
            {[1, 2, 3].map(i => (
              <div key={i} style={{ background: T.surface, borderRadius: 14, padding: 24, border: `1px solid ${T.border}`, opacity: 0.4, height: 160 }} />
            ))}
          </div>
        ) : personas.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '80px 0' }}>
            <Bot size={48} style={{ color: T.muted, margin: '0 auto 16px', display: 'block' }} />
            <p style={{ fontSize: 16, fontWeight: 600, color: T.muted, marginBottom: 8 }}>No personas yet</p>
            <p style={{ fontSize: 13, color: T.muted, marginBottom: 20 }}>Create your first AI persona.</p>
            <button onClick={openNew} style={{ padding: '10px 20px', borderRadius: 10, background: T.accent, color: '#fff', fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <Plus size={14} /> Create Persona
            </button>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
            {personas.map(persona => (
              <div key={persona.id} style={{ background: T.surface, borderRadius: 14, padding: 20, border: `1.5px solid ${persona.is_active ? T.accent : T.border}`, position: 'relative' }}>
                {persona.is_active && (
                  <span style={{ position: 'absolute', top: 14, right: 14, display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 600, color: T.accent, background: 'rgba(224,90,37,0.1)', padding: '2px 8px', borderRadius: 20 }}>
                    <CheckCircle size={11} /> Active
                  </span>
                )}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                  <div style={{ width: 44, height: 44, borderRadius: 12, background: `${toneColor(persona.tone)}22`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>
                    {persona.avatar_url ? (
                      <img src={persona.avatar_url} alt={persona.name} style={{ width: 44, height: 44, borderRadius: 12, objectFit: 'cover' }} />
                    ) : (
                      <Bot size={20} style={{ color: toneColor(persona.tone) }} />
                    )}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 15, fontWeight: 700, margin: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{persona.name}</p>
                    <div style={{ marginTop: 4 }}>
                      <Badge color={`${toneColor(persona.tone)}22`}>{persona.tone || 'Professional'}</Badge>
                    </div>
                  </div>
                </div>
                {persona.description && (
                  <p style={{ fontSize: 12, color: T.muted, margin: '0 0 12px', lineHeight: 1.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                    {persona.description}
                  </p>
                )}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
                  {persona.voice && persona.voice !== 'Default' && <Badge><Mic size={10} style={{ marginRight: 3 }} />{persona.voice}</Badge>}
                  {persona.language && <Badge><Globe size={10} style={{ marginRight: 3 }} />{persona.language}</Badge>}
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  {!persona.is_active && (
                    <button
                      onClick={() => handleActivate(persona.id)}
                      disabled={activating === persona.id}
                      style={{ flex: 1, padding: '7px 0', borderRadius: 8, background: T.accent, color: '#fff', fontWeight: 600, fontSize: 12, border: 'none', cursor: 'pointer', opacity: activating === persona.id ? 0.6 : 1 }}
                    >
                      {activating === persona.id ? 'Activating...' : 'Activate'}
                    </button>
                  )}
                  <button
                    onClick={() => openEdit(persona)}
                    style={{ padding: '7px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.06)', color: T.muted, border: `1px solid ${T.border}`, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}
                  >
                    <Edit2 size={12} /> Edit
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(persona.id)}
                    style={{ padding: '7px 10px', borderRadius: 8, background: 'rgba(239,68,68,0.08)', color: T.danger, border: `1px solid rgba(239,68,68,0.2)`, cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Slide-in Panel */}
      {panelOpen && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', justifyContent: 'flex-end' }}>
          <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.5)' }} onClick={() => setPanelOpen(false)} />
          <div style={{ position: 'relative', width: 440, background: 'var(--theme-surface, #1C1C1E)', borderLeft: `1px solid ${T.border}`, overflowY: 'auto', display: 'flex', flexDirection: 'column', zIndex: 10 }}>
            <div style={{ padding: '20px 24px 16px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <p style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>{editing ? 'Edit Persona' : 'New Persona'}</p>
              <button onClick={() => setPanelOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: T.muted, display: 'flex' }}><X size={18} /></button>
            </div>
            <div style={{ padding: 24, flex: 1 }}>
              <Fld label="Name *">
                <Inp value={form.name} onChange={f('name')} placeholder="e.g. Sales Assistant" />
              </Fld>
              <Fld label="Description">
                <Inp value={form.description} onChange={f('description')} placeholder="What does this persona do?" />
              </Fld>
              <Fld label="Tone">
                <Sel value={form.tone} onChange={f('tone')} options={TONES} />
              </Fld>
              <Fld label="Voice">
                <Sel value={form.voice} onChange={f('voice')} options={VOICES} />
              </Fld>
              <Fld label="Language">
                <Sel value={form.language} onChange={f('language')} options={LANGUAGES} />
              </Fld>
              <Fld label="Avatar URL">
                <Inp value={form.avatar_url} onChange={f('avatar_url')} placeholder="https://..." />
              </Fld>
              <Fld label="System Prompt">
                <textarea
                  value={form.system_prompt}
                  onChange={f('system_prompt')}
                  placeholder="You are a helpful assistant that..."
                  rows={5}
                  style={{ width: '100%', boxSizing: 'border-box', padding: '9px 12px', background: T.input, border: `1.5px solid ${T.border}`, borderRadius: 8, color: T.text, fontSize: 13, outline: 'none', resize: 'vertical', fontFamily: 'inherit', lineHeight: 1.5 }}
                />
              </Fld>
            </div>
            <div style={{ padding: '16px 24px', borderTop: `1px solid ${T.border}`, display: 'flex', gap: 10 }}>
              <button
                onClick={() => setPanelOpen(false)}
                style={{ flex: 1, padding: '10px 0', borderRadius: 8, background: 'transparent', border: `1px solid ${T.border}`, color: T.muted, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !form.name.trim()}
                style={{ flex: 2, padding: '10px 0', borderRadius: 8, background: T.accent, color: '#fff', fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer', opacity: (saving || !form.name.trim()) ? 0.6 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
              >
                <Save size={14} /> {saving ? 'Saving...' : (editing ? 'Update' : 'Create Persona')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirmation */}
      {deleteConfirm && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 60, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.6)' }}>
          <div style={{ background: T.surface, borderRadius: 16, padding: 28, width: 360, border: `1px solid ${T.border}` }}>
            <p style={{ fontSize: 16, fontWeight: 700, margin: '0 0 8px' }}>Delete Persona?</p>
            <p style={{ fontSize: 13, color: T.muted, margin: '0 0 20px' }}>This action cannot be undone.</p>
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => setDeleteConfirm(null)} style={{ flex: 1, padding: '9px 0', borderRadius: 8, background: 'transparent', border: `1px solid ${T.border}`, color: T.muted, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>Cancel</button>
              <button onClick={() => handleDelete(deleteConfirm)} style={{ flex: 1, padding: '9px 0', borderRadius: 8, background: T.danger, color: '#fff', fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer' }}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
