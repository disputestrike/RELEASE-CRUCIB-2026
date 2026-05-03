import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import { X, Plus, Pencil, Trash2, Sparkles, Check, Wand2 } from 'lucide-react';

// ── System skills metadata (mirrors backend SYSTEM_SKILLS) ───────────────────
const SYSTEM_SKILLS = [
  { name: 'web-app-builder', icon: '🌐', color: '#3b82f6', category: 'build', display_name: 'Web App', short_desc: 'Full-stack React + Node.js with auth, database, and API', trigger_prompt: 'Build a full-stack web app with user authentication, dashboard, and REST API' },
  { name: 'mobile-app-builder', icon: '📱', color: '#8b5cf6', category: 'build', display_name: 'Mobile App', short_desc: 'React Native with Expo — iOS and Android ready', trigger_prompt: 'Build a mobile app with navigation, screens, and local storage' },
  { name: 'saas-mvp-builder', icon: '💳', color: '#525252', category: 'build', display_name: 'SaaS MVP', short_desc: 'Auth, PayPal billing, user dashboard, multi-tenant', trigger_prompt: 'Build a SaaS MVP with PayPal billing, user auth, and admin dashboard' },
  { name: 'ecommerce-builder', icon: '🛒', color: '#10b981', category: 'build', display_name: 'E-Commerce', short_desc: 'Product catalog, cart, PayPal checkout, order management', trigger_prompt: 'Build an e-commerce store with product catalog, cart, and PayPal checkout' },
  { name: 'ai-chatbot-builder', icon: '🤖', color: '#ec4899', category: 'build', display_name: 'AI Chatbot', short_desc: 'Multi-agent chat, knowledge base, streaming, embeddable widget', trigger_prompt: 'Build an AI chatbot with multi-agent support and document knowledge base' },
  { name: 'landing-page-builder', icon: '🏠', color: '#06b6d4', category: 'build', display_name: 'Landing Page', short_desc: 'Hero, features, pricing, testimonials, FAQ, email waitlist', trigger_prompt: 'Build a landing page with hero, features grid, pricing table, and FAQ' },
  { name: 'automation-builder', icon: '⚡', color: '#525252', category: 'automate', display_name: 'Automation', short_desc: 'Scheduled agents, webhooks, AI-powered workflows', trigger_prompt: 'Build an automation that runs daily and sends results to Slack or email' },
  { name: 'internal-tool-builder', icon: '🛠️', color: '#64748b', category: 'build', display_name: 'Internal Tool', short_desc: 'Admin tables, forms, CRUD, approval workflows', trigger_prompt: 'Build an internal admin tool with data tables, forms, and user roles' },
  { name: 'data-dashboard-builder', icon: '📊', color: '#6366f1', category: 'build', display_name: 'Data Dashboard', short_desc: 'Interactive charts, KPI cards, filters, analytics', trigger_prompt: 'Build a data analytics dashboard with charts and KPI cards' },
  { name: 'custom-user-skill', icon: '✨', color: '#a855f7', category: 'custom', display_name: 'Custom Skill', short_desc: 'Define your own building patterns and AI instructions', trigger_prompt: '' },
];

const CATEGORY_LABELS = { build: 'Build', automate: 'Automate', custom: 'Custom' };
const CATEGORY_COLORS = {
  build: { bg: 'rgba(59,130,246,0.12)', text: '#3b82f6' },
  automate: { bg: 'rgba(64,64,64,0.12)', text: '#404040' },
  custom: { bg: 'rgba(168,85,247,0.12)', text: '#a855f7' },
};

// ── Drawer for creating/editing user skills ───────────────────────────────────
const SkillDrawer = ({ open, onClose, onSave, initialData }) => {
  const isEdit = !!initialData;
  const [form, setForm] = useState({
    name: '',
    display_name: '',
    icon: '✨',
    color: '#a855f7',
    short_desc: '',
    instructions: '',
    trigger_phrases: [],
  });
  const [tagInput, setTagInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (open) {
      if (initialData) {
        setForm({
          name: initialData.name || '',
          display_name: initialData.display_name || '',
          icon: initialData.icon || '✨',
          color: initialData.color || '#a855f7',
          short_desc: initialData.short_desc || '',
          instructions: initialData.instructions || '',
          trigger_phrases: initialData.trigger_phrases || [],
        });
      } else {
        setForm({ name: '', display_name: '', icon: '✨', color: '#a855f7', short_desc: '', instructions: '', trigger_phrases: [] });
      }
      setTagInput('');
      setError('');
    }
  }, [open, initialData]);

  const set = (field, value) => setForm(f => ({ ...f, [field]: value }));

  const addTag = () => {
    const t = tagInput.trim();
    if (t && !form.trigger_phrases.includes(t)) {
      set('trigger_phrases', [...form.trigger_phrases, t]);
    }
    setTagInput('');
  };

  const removeTag = (tag) => set('trigger_phrases', form.trigger_phrases.filter(t => t !== tag));

  const handleTagKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addTag(); }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.display_name.trim()) { setError('Display name is required'); return; }
    if (!isEdit && !form.name.trim()) { setError('Skill ID is required'); return; }
    setSaving(true);
    setError('');
    try {
      await onSave(form);
      onClose();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to save skill');
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        display: 'flex', justifyContent: 'flex-end',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* Backdrop */}
      <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.35)' }} onClick={onClose} />
      {/* Drawer */}
      <div style={{
        position: 'relative', zIndex: 1, width: '480px', maxWidth: '95vw',
        background: 'var(--theme-bg, #fff)', borderLeft: '1px solid var(--theme-border, #e5e7eb)',
        height: '100vh', overflowY: 'auto', display: 'flex', flexDirection: 'column',
        boxShadow: '-4px 0 24px rgba(0,0,0,0.12)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid var(--theme-border, #e5e7eb)' }}>
          <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: 'var(--theme-text, #111827)' }}>
            {isEdit ? 'Edit Skill' : 'Add Custom Skill'}
          </h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--theme-text-muted, #6b7280)', padding: '4px', borderRadius: '6px', display: 'flex', alignItems: 'center' }}>
            <X size={18} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ flex: 1, padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '80px 1fr', gap: '12px' }}>
            <div>
              <label style={labelStyle}>Icon</label>
              <input
                value={form.icon}
                onChange={e => set('icon', e.target.value)}
                style={{ ...inputStyle, textAlign: 'center', fontSize: '22px' }}
                maxLength={5}
                placeholder="✨"
              />
            </div>
            <div>
              <label style={labelStyle}>Display Name *</label>
              <input
                value={form.display_name}
                onChange={e => set('display_name', e.target.value)}
                style={inputStyle}
                placeholder="My Brand Voice"
                required
              />
            </div>
          </div>

          {!isEdit && (
            <div>
              <label style={labelStyle}>Skill ID *</label>
              <input
                value={form.name}
                onChange={e => set('name', e.target.value.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, ''))}
                style={inputStyle}
                placeholder="my-brand-voice"
                required
              />
              <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--theme-text-muted, #9ca3af)' }}>Letters, numbers, dashes only</p>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px', gap: '12px' }}>
            <div>
              <label style={labelStyle}>Short Description</label>
              <input
                value={form.short_desc}
                onChange={e => set('short_desc', e.target.value)}
                style={inputStyle}
                placeholder="Apply my brand voice to all content"
                maxLength={200}
              />
            </div>
            <div>
              <label style={labelStyle}>Color</label>
              <input
                type="color"
                value={form.color}
                onChange={e => set('color', e.target.value)}
                style={{ ...inputStyle, padding: '4px', cursor: 'pointer', height: '38px' }}
              />
            </div>
          </div>

          <div>
            <label style={labelStyle}>Instructions</label>
            <textarea
              value={form.instructions}
              onChange={e => set('instructions', e.target.value)}
              style={{ ...inputStyle, minHeight: '160px', resize: 'vertical', fontFamily: 'inherit', lineHeight: 1.6 }}
              placeholder={'Always use casual, friendly tone.\nUse "you" not "one".\nAvoid jargon and buzzwords.\nEnd with a clear call to action.'}
            />
            <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--theme-text-muted, #9ca3af)' }}>These instructions are injected into every build when this skill is active</p>
          </div>

          <div>
            <label style={labelStyle}>Trigger Phrases</label>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <input
                value={tagInput}
                onChange={e => setTagInput(e.target.value)}
                onKeyDown={handleTagKeyDown}
                style={{ ...inputStyle, flex: 1 }}
                placeholder="write copy"
              />
              <button type="button" onClick={addTag} style={{ ...secondaryBtnStyle, whiteSpace: 'nowrap' }}>Add</button>
            </div>
            {form.trigger_phrases.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {form.trigger_phrases.map(tag => (
                  <span key={tag} style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '4px 10px', background: 'var(--theme-surface, #f3f4f6)', borderRadius: '20px', fontSize: '12px', color: 'var(--theme-text, #111827)' }}>
                    {tag}
                    <button type="button" onClick={() => removeTag(tag)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, color: 'var(--theme-text-muted, #9ca3af)', lineHeight: 1, display: 'flex', alignItems: 'center' }}>
                      <X size={12} />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {error && (
            <p style={{ margin: 0, color: '#ef4444', fontSize: '13px', padding: '10px 14px', background: 'rgba(239,68,68,0.08)', borderRadius: '8px' }}>{error}</p>
          )}

          <div style={{ display: 'flex', gap: '10px', marginTop: 'auto', paddingTop: '8px' }}>
            <button type="button" onClick={onClose} style={secondaryBtnStyle}>Cancel</button>
            <button type="submit" disabled={saving} style={{ ...primaryBtnStyle, flex: 1, opacity: saving ? 0.7 : 1 }}>
              {saving ? 'Saving…' : isEdit ? 'Save Changes' : 'Create Skill'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ── Skill Card ────────────────────────────────────────────────────────────────
const SkillCard = ({ skill, isActive, onToggle, onEdit, onDelete, isUser }) => {
  const [hovered, setHovered] = useState(false);
  const [toggling, setToggling] = useState(false);
  const catColors = CATEGORY_COLORS[skill.category] || CATEGORY_COLORS.build;

  const handleToggle = async () => {
    if (toggling) return;
    setToggling(true);
    await onToggle(skill.name || skill.id);
    setToggling(false);
  };

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: 'var(--theme-bg, #fff)',
        border: `1px solid ${isActive ? skill.color : 'var(--theme-border, #e5e7eb)'}`,
        borderRadius: '14px',
        padding: '18px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        transition: 'border-color 0.15s, box-shadow 0.15s',
        boxShadow: hovered ? '0 4px 16px rgba(0,0,0,0.08)' : 'none',
        position: 'relative',
        cursor: 'default',
      }}
    >
      {/* Icon + toggle row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{
          width: '44px', height: '44px', borderRadius: '12px',
          background: `${skill.color}20`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '22px', flexShrink: 0,
        }}>
          {skill.icon}
        </div>
        {/* Toggle */}
        <button
          onClick={handleToggle}
          disabled={toggling}
          title={isActive ? 'Deactivate' : 'Activate'}
          style={{
            width: '40px', height: '22px', borderRadius: '11px',
            background: isActive ? skill.color : 'var(--theme-surface, #e5e7eb)',
            border: 'none', cursor: 'pointer', position: 'relative',
            transition: 'background 0.2s',
            flexShrink: 0,
          }}
        >
          <div style={{
            position: 'absolute', top: '3px',
            left: isActive ? '21px' : '3px',
            width: '16px', height: '16px', borderRadius: '50%',
            background: '#fff',
            transition: 'left 0.2s',
            boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
          }} />
        </button>
      </div>

      {/* Name + category */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--theme-text, #111827)' }}>
            {skill.display_name}
          </span>
          <span style={{
            fontSize: '10px', fontWeight: 500, padding: '2px 7px', borderRadius: '10px',
            background: catColors.bg, color: catColors.text, textTransform: 'uppercase', letterSpacing: '0.5px',
          }}>
            {CATEGORY_LABELS[skill.category] || skill.category}
          </span>
        </div>
        <p style={{ margin: 0, fontSize: '12px', color: 'var(--theme-text-muted, #6b7280)', lineHeight: 1.5 }}>
          {skill.short_desc}
        </p>
      </div>

      {/* Trigger phrases — shown on hover */}
      {hovered && skill.trigger_phrases && skill.trigger_phrases.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
          {skill.trigger_phrases.map(tp => (
            <span key={tp} style={{ fontSize: '10px', padding: '2px 8px', background: 'var(--theme-surface, #f3f4f6)', borderRadius: '10px', color: 'var(--theme-text-muted, #6b7280)' }}>
              {tp}
            </span>
          ))}
        </div>
      )}

      {/* Active indicator */}
      {isActive && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px', color: skill.color, fontWeight: 500 }}>
          <Check size={12} />
          Active
        </div>
      )}

      {/* User skill actions */}
      {isUser && (
        <div style={{ display: 'flex', gap: '8px', borderTop: '1px solid var(--theme-border, #e5e7eb)', paddingTop: '10px', marginTop: '2px' }}>
          <button
            onClick={() => onEdit(skill)}
            style={{ flex: 1, ...secondaryBtnStyle, fontSize: '12px', padding: '6px 10px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px' }}
          >
            <Pencil size={12} /> Edit
          </button>
          <button
            onClick={() => onDelete(skill.id)}
            style={{ ...secondaryBtnStyle, fontSize: '12px', padding: '6px 10px', color: '#ef4444', borderColor: 'rgba(239,68,68,0.3)', display: 'flex', alignItems: 'center', gap: '5px' }}
          >
            <Trash2 size={12} /> Delete
          </button>
        </div>
      )}
    </div>
  );
};

// ── Shared styles ─────────────────────────────────────────────────────────────
const labelStyle = {
  display: 'block', fontSize: '12px', fontWeight: 500,
  color: 'var(--theme-text-muted, #6b7280)', marginBottom: '6px',
};

const inputStyle = {
  width: '100%', padding: '8px 12px',
  border: '1px solid var(--theme-border, #e5e7eb)',
  borderRadius: '8px', fontSize: '14px',
  background: 'var(--theme-bg, #fff)',
  color: 'var(--theme-text, #111827)',
  outline: 'none', boxSizing: 'border-box',
};

const primaryBtnStyle = {
  padding: '9px 18px', borderRadius: '8px', border: 'none',
  background: '#111827', color: '#fff', fontSize: '14px',
  fontWeight: 500, cursor: 'pointer',
};

const secondaryBtnStyle = {
  padding: '9px 14px', borderRadius: '8px',
  border: '1px solid var(--theme-border, #e5e7eb)',
  background: 'transparent', color: 'var(--theme-text, #111827)',
  fontSize: '14px', fontWeight: 500, cursor: 'pointer',
};

// ── Main SkillsPage ───────────────────────────────────────────────────────────
const SkillsPage = () => {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [systemSkills, setSystemSkills] = useState(SYSTEM_SKILLS);
  const [userSkills, setUserSkills] = useState([]);
  const [activeIds, setActiveIds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingSkill, setEditingSkill] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [filterCategory, setFilterCategory] = useState('all');
  const [skillAgentPrompt, setSkillAgentPrompt] = useState('');
  const [skillAgentBusy, setSkillAgentBusy] = useState(false);
  const [skillAgentMsg, setSkillAgentMsg] = useState(null);

  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

  const fetchSkills = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    try {
      const res = await axios.get(`${API}/skills`, { headers: authHeaders });
      setSystemSkills(res.data.system_skills || SYSTEM_SKILLS);
      setUserSkills(res.data.user_skills || []);
      setActiveIds(res.data.active_skill_ids || []);
    } catch {
      // Fall back to local data
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => { fetchSkills(); }, [fetchSkills]);

  const handleToggle = async (skillId) => {
    try {
      const res = await axios.post(`${API}/skills/${skillId}/activate`, {}, { headers: authHeaders });
      setActiveIds(res.data.active_skill_ids || []);
    } catch (err) {
      console.error('Toggle skill failed', err);
    }
  };

  const handleCreateSkill = async (formData) => {
    const res = await axios.post(`${API}/skills`, formData, { headers: authHeaders });
    setUserSkills(prev => [...prev, res.data.skill]);
  };

  const handleGenerateSkill = async () => {
    const description = skillAgentPrompt.trim();
    if (!description) return;
    setSkillAgentBusy(true);
    setSkillAgentMsg(null);
    try {
      const res = await axios.post(
        `${API}/skills/generate`,
        { description, auto_create: true, activate: true },
        { headers: authHeaders }
      );
      const skill = res.data?.skill;
      if (skill) setUserSkills(prev => prev.some(s => s.id === skill.id) ? prev : [...prev, skill]);
      if (Array.isArray(res.data?.active_skill_ids) && res.data.active_skill_ids.length > 0) {
        setActiveIds(res.data.active_skill_ids);
      } else if (skill?.id && res.data?.activated) {
        setActiveIds(prev => prev.includes(skill.id) ? prev : [...prev, skill.id]);
      }
      setSkillAgentPrompt('');
      setSkillAgentMsg({ type: 'success', text: res.data?.persisted ? 'Skill Agent created and activated a new skill.' : 'Skill Agent drafted a skill; persistence was not available.' });
    } catch (err) {
      setSkillAgentMsg({ type: 'error', text: err?.response?.data?.detail || 'Skill Agent could not generate this skill.' });
    } finally {
      setSkillAgentBusy(false);
    }
  };

  const handleEditSkill = async (formData) => {
    const skillId = editingSkill.id;
    const res = await axios.put(`${API}/skills/${skillId}`, formData, { headers: authHeaders });
    setUserSkills(prev => prev.map(s => s.id === skillId ? res.data.skill : s));
  };

  const handleDeleteSkill = async (skillId) => {
    await axios.delete(`${API}/skills/${skillId}`, { headers: authHeaders });
    setUserSkills(prev => prev.filter(s => s.id !== skillId));
    setActiveIds(prev => prev.filter(id => id !== skillId));
    setDeleteConfirm(null);
  };

  const openEdit = (skill) => { setEditingSkill(skill); setDrawerOpen(true); };
  const openCreate = () => { setEditingSkill(null); setDrawerOpen(true); };
  const closeDrawer = () => { setDrawerOpen(false); setEditingSkill(null); };

  const allSkills = [...systemSkills, ...userSkills];
  const filteredSkills = filterCategory === 'all' ? allSkills : allSkills.filter(s => s.category === filterCategory);
  const activeCount = activeIds.length;

  return (
    <div style={{ minHeight: '100vh', background: 'var(--theme-bg, #fff)', padding: '0' }}>
      {/* Page header */}
      <div style={{
        borderBottom: '1px solid var(--theme-border, #e5e7eb)',
        padding: '28px 36px 24px',
        background: 'var(--theme-bg, #fff)',
        position: 'sticky', top: 0, zIndex: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', maxWidth: '1100px', margin: '0 auto' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
              <Sparkles size={22} style={{ color: '#a855f7' }} />
              <h1 style={{ margin: 0, fontSize: '22px', fontWeight: 700, color: 'var(--theme-text, #111827)' }}>Skills</h1>
              {activeCount > 0 && (
                <span style={{ fontSize: '12px', padding: '2px 9px', borderRadius: '12px', background: 'rgba(168,85,247,0.12)', color: '#a855f7', fontWeight: 600 }}>
                  {activeCount} active
                </span>
              )}
            </div>
            <p style={{ margin: 0, fontSize: '14px', color: 'var(--theme-text-muted, #6b7280)' }}>
              Extend what CrucibAI can build. Skills apply automatically when matched.
            </p>
          </div>
          <button onClick={openCreate} style={{ ...primaryBtnStyle, display: 'flex', alignItems: 'center', gap: '7px', flexShrink: 0 }}>
            <Plus size={15} /> Add custom skill
          </button>
        </div>

        {/* Category filter */}
        <div style={{ display: 'flex', gap: '8px', marginTop: '16px', maxWidth: '1100px', margin: '16px auto 0' }}>
          {['all', 'build', 'automate', 'custom'].map(cat => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              style={{
                padding: '5px 14px', borderRadius: '20px', fontSize: '13px', fontWeight: 500, cursor: 'pointer',
                border: filterCategory === cat ? 'none' : '1px solid var(--theme-border, #e5e7eb)',
                background: filterCategory === cat ? '#111827' : 'transparent',
                color: filterCategory === cat ? '#fff' : 'var(--theme-text-muted, #6b7280)',
                transition: 'all 0.15s',
              }}
            >
              {cat === 'all' ? `All (${allSkills.length})` : `${CATEGORY_LABELS[cat]} (${allSkills.filter(s => s.category === cat).length})`}
            </button>
          ))}
        </div>
      </div>

      {/* Main content */}
      <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '28px 36px' }}>
        <div style={{
          background: 'var(--theme-surface, #f9fafb)',
          border: '1px solid var(--theme-border, #e5e7eb)',
          borderRadius: '14px',
          padding: '18px',
          marginBottom: '22px',
          display: 'grid',
          gridTemplateColumns: '1fr auto',
          gap: '12px',
          alignItems: 'end',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 7 }}>
              <Wand2 size={15} style={{ color: '#7c3aed' }} />
              <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--theme-text, #111827)' }}>Skill Agent</span>
              <span style={{ fontSize: 11, color: 'var(--theme-text-muted, #6b7280)' }}>
                creates missing capabilities as reusable Skill MD-style instructions
              </span>
            </div>
            <input
              value={skillAgentPrompt}
              onChange={e => setSkillAgentPrompt(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleGenerateSkill(); }}
              placeholder="Example: Create a skill for ingesting PDFs and turning them into app requirements"
              style={{ ...inputStyle, width: '100%' }}
            />
            {skillAgentMsg && (
              <p style={{ margin: '8px 0 0', fontSize: 12, color: skillAgentMsg.type === 'success' ? '#10b981' : '#ef4444' }}>
                {skillAgentMsg.text}
              </p>
            )}
          </div>
          <button
            onClick={handleGenerateSkill}
            disabled={skillAgentBusy || !skillAgentPrompt.trim()}
            style={{ ...primaryBtnStyle, display: 'flex', alignItems: 'center', gap: 7, opacity: (skillAgentBusy || !skillAgentPrompt.trim()) ? 0.65 : 1 }}
          >
            <Wand2 size={14} /> {skillAgentBusy ? 'Creating...' : 'Generate skill'}
          </button>
        </div>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--theme-text-muted, #9ca3af)' }}>Loading skills…</div>
        ) : (
          <>
            {/* Skills grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '16px',
            }} className="skills-page-grid">
              {filteredSkills.map(skill => (
                <SkillCard
                  key={skill.name || skill.id}
                  skill={skill}
                  isActive={activeIds.includes(skill.name || skill.id)}
                  onToggle={handleToggle}
                  onEdit={openEdit}
                  onDelete={(id) => setDeleteConfirm(id)}
                  isUser={!systemSkills.some(s => s.name === (skill.name || skill.id))}
                />
              ))}

              {/* "Add custom skill" CTA card */}
              {(filterCategory === 'all' || filterCategory === 'custom') && (
                <button
                  onClick={openCreate}
                  style={{
                    background: 'transparent',
                    border: '2px dashed var(--theme-border, #e5e7eb)',
                    borderRadius: '14px', padding: '18px',
                    cursor: 'pointer', display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center', gap: '10px',
                    minHeight: '160px', transition: 'border-color 0.15s',
                    color: 'var(--theme-text-muted, #9ca3af)',
                  }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = '#a855f7'}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--theme-border, #e5e7eb)'}
                >
                  <div style={{ width: '40px', height: '40px', borderRadius: '12px', background: 'rgba(168,85,247,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Plus size={20} style={{ color: '#a855f7' }} />
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--theme-text, #111827)', marginBottom: '2px' }}>New Custom Skill</div>
                    <div style={{ fontSize: '12px' }}>Define your own patterns and instructions</div>
                  </div>
                </button>
              )}
            </div>

            {/* Active skills summary */}
            {activeCount > 0 && (
              <div style={{
                marginTop: '32px', padding: '18px 22px',
                background: 'var(--theme-surface, #f9fafb)',
                border: '1px solid var(--theme-border, #e5e7eb)',
                borderRadius: '12px',
              }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--theme-text, #111827)', marginBottom: '8px' }}>
                  Active skills — applied to all new builds
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {activeIds.map(id => {
                    const sk = allSkills.find(s => (s.name || s.id) === id);
                    if (!sk) return null;
                    return (
                      <span key={id} style={{
                        display: 'inline-flex', alignItems: 'center', gap: '5px',
                        padding: '4px 12px', borderRadius: '20px',
                        background: `${sk.color}15`, color: sk.color,
                        fontSize: '12px', fontWeight: 500,
                        border: `1px solid ${sk.color}30`,
                      }}>
                        {sk.icon} {sk.display_name}
                      </span>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Skill drawer */}
      <SkillDrawer
        open={drawerOpen}
        onClose={closeDrawer}
        onSave={editingSkill ? handleEditSkill : handleCreateSkill}
        initialData={editingSkill}
      />

      {/* Delete confirmation */}
      {deleteConfirm && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.4)' }}>
          <div style={{ background: 'var(--theme-bg, #fff)', borderRadius: '16px', padding: '28px', maxWidth: '380px', width: '90%', boxShadow: '0 20px 60px rgba(0,0,0,0.15)' }}>
            <h3 style={{ margin: '0 0 8px', fontSize: '16px', fontWeight: 600, color: 'var(--theme-text, #111827)' }}>Delete skill?</h3>
            <p style={{ margin: '0 0 24px', fontSize: '14px', color: 'var(--theme-text-muted, #6b7280)' }}>This action cannot be undone. The skill will be permanently removed.</p>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button onClick={() => setDeleteConfirm(null)} style={secondaryBtnStyle}>Cancel</button>
              <button onClick={() => handleDeleteSkill(deleteConfirm)} style={{ ...primaryBtnStyle, background: '#ef4444' }}>Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Responsive styles */}
      <style>{`
        @media (max-width: 900px) {
          .skills-page-grid { grid-template-columns: repeat(2, 1fr) !important; }
        }
        @media (max-width: 600px) {
          .skills-page-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
};

export default SkillsPage;
