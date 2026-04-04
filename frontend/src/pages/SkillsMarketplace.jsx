import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../App';

const API = process.env.REACT_APP_BACKEND_URL || '';

const CATEGORY_LABELS = {
  build: 'Build',
  automate: 'Automate',
  custom: 'Custom',
  community: 'Community',
};

const CATEGORY_COLORS = {
  build: { bg: 'rgba(59,130,246,0.12)', color: '#93c5fd' },
  automate: { bg: 'rgba(251,146,60,0.12)', color: '#fdba74' },
  custom: { bg: 'rgba(168,85,247,0.12)', color: '#d8b4fe' },
  community: { bg: 'rgba(52,211,153,0.12)', color: '#6ee7b7' },
};

const SkillsMarketplace = () => {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [systemSkills, setSystemSkills] = useState([]);
  const [communitySkills, setCommunitySkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState('all');
  const [forking, setForking] = useState(null);
  const [forkedIds, setForkedIds] = useState(new Set());
  const [message, setMessage] = useState(null);

  useEffect(() => {
    setLoading(true);
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    axios.get(`${API}/api/skills/marketplace`, { headers })
      .then(r => {
        setSystemSkills(r.data?.system_skills || []);
        setCommunitySkills((r.data?.community_skills || []).map(s => ({ ...s, category: 'community' })));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [token]);

  const allSkills = [
    ...systemSkills.filter(s => s.name !== 'custom-user-skill'),
    ...communitySkills,
  ];

  const categories = ['all', ...new Set(allSkills.map(s => s.category || 'build'))];

  const filtered = activeCategory === 'all'
    ? allSkills
    : allSkills.filter(s => (s.category || 'build') === activeCategory);

  const handleFork = async (skill) => {
    if (!token) {
      setMessage({ type: 'error', text: 'Sign in to fork skills' });
      setTimeout(() => setMessage(null), 3000);
      return;
    }
    setForking(skill.name || skill.id);
    try {
      await axios.post(
        `${API}/api/skills/${skill.name || skill.id}/fork`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setForkedIds(prev => new Set([...prev, skill.name || skill.id]));
      setMessage({ type: 'success', text: `"${skill.display_name}" forked to your library!` });
    } catch (e) {
      setMessage({ type: 'error', text: e?.response?.data?.detail || 'Fork failed' });
    } finally {
      setForking(null);
      setTimeout(() => setMessage(null), 3000);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--theme-bg, #0a0a0a)',
        color: 'var(--theme-text, #e4e4e7)',
        fontFamily: "'DM Sans', sans-serif",
      }}
    >
      {/* Header */}
      <div
        style={{
          borderBottom: '1px solid var(--theme-border, rgba(255,255,255,0.08))',
          padding: '24px 32px 20px',
          background: 'var(--theme-surface, #111)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', maxWidth: 1100, margin: '0 auto' }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, letterSpacing: '-0.02em' }}>Skills Marketplace</h1>
            <p style={{ fontSize: 13, color: 'var(--theme-muted, #71717a)', marginTop: 4 }}>
              Plug-in AI building patterns. Fork any skill to your library and customize it.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button
              onClick={() => navigate('/app/skills')}
              style={{
                padding: '7px 16px',
                borderRadius: 8,
                border: '1px solid var(--theme-border, rgba(255,255,255,0.1))',
                background: 'transparent',
                color: 'var(--theme-text)',
                fontSize: 13,
                cursor: 'pointer',
              }}
            >
              My Skills
            </button>
          </div>
        </div>
      </div>

      {/* Toast message */}
      {message && (
        <div
          style={{
            position: 'fixed',
            top: 20,
            right: 20,
            zIndex: 9999,
            padding: '10px 18px',
            borderRadius: 10,
            fontSize: 13,
            fontWeight: 500,
            background: message.type === 'success' ? 'rgba(52,211,153,0.15)' : 'rgba(248,113,113,0.15)',
            color: message.type === 'success' ? '#6ee7b7' : '#fca5a5',
            border: `1px solid ${message.type === 'success' ? 'rgba(52,211,153,0.3)' : 'rgba(248,113,113,0.3)'}`,
          }}
        >
          {message.text}
        </div>
      )}

      {/* Category filter */}
      <div
        style={{
          padding: '16px 32px',
          borderBottom: '1px solid var(--theme-border, rgba(255,255,255,0.06))',
          background: 'var(--theme-surface, #111)',
          display: 'flex',
          gap: 8,
          flexWrap: 'wrap',
          maxWidth: 1164,
          margin: '0 auto',
        }}
      >
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            style={{
              padding: '5px 14px',
              borderRadius: 20,
              border: '1px solid',
              borderColor: activeCategory === cat ? 'var(--theme-accent, #6366f1)' : 'var(--theme-border, rgba(255,255,255,0.1))',
              background: activeCategory === cat ? 'rgba(99,102,241,0.15)' : 'transparent',
              color: activeCategory === cat ? '#a5b4fc' : 'var(--theme-muted, #71717a)',
              fontSize: 12,
              fontWeight: 500,
              cursor: 'pointer',
              textTransform: 'capitalize',
            }}
          >
            {cat === 'all' ? `All (${allSkills.length})` : `${CATEGORY_LABELS[cat] || cat} (${allSkills.filter(s => (s.category || 'build') === cat).length})`}
          </button>
        ))}
      </div>

      {/* Skills grid */}
      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px 32px' }}>
        {loading ? (
          <div style={{ textAlign: 'center', color: 'var(--theme-muted)', padding: '60px 0' }}>Loading skills...</div>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
              gap: 16,
            }}
          >
            {filtered.map((skill) => {
              const cat = skill.category || 'build';
              const catStyle = CATEGORY_COLORS[cat] || CATEGORY_COLORS.build;
              const isCommunity = cat === 'community';
              const skillId = skill.name || skill.id;
              const alreadyForked = forkedIds.has(skillId);

              return (
                <div
                  key={skillId}
                  style={{
                    background: 'var(--theme-surface2, #18181b)',
                    border: '1px solid var(--theme-border, rgba(255,255,255,0.08))',
                    borderRadius: 14,
                    padding: '18px 20px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 12,
                    transition: 'border-color 200ms',
                  }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)'}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--theme-border, rgba(255,255,255,0.08))'}
                >
                  {/* Card header */}
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                    <div
                      style={{
                        width: 42,
                        height: 42,
                        borderRadius: 10,
                        background: `${skill.color || '#6366f1'}20`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 22,
                        flexShrink: 0,
                        border: `1px solid ${skill.color || '#6366f1'}30`,
                      }}
                    >
                      {skill.icon || '⚙️'}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--theme-text)' }}>
                          {skill.display_name || skill.name}
                        </span>
                        <span
                          style={{
                            padding: '2px 8px',
                            borderRadius: 20,
                            fontSize: 10,
                            fontWeight: 600,
                            textTransform: 'uppercase',
                            letterSpacing: '0.04em',
                            background: catStyle.bg,
                            color: catStyle.color,
                          }}
                        >
                          {isCommunity ? 'Community' : CATEGORY_LABELS[cat] || cat}
                        </span>
                      </div>
                      {isCommunity && skill.user_id && (
                        <div style={{ fontSize: 11, color: 'var(--theme-muted)', marginTop: 2 }}>by community</div>
                      )}
                    </div>
                  </div>

                  {/* Description */}
                  <p style={{ fontSize: 12, color: 'var(--theme-muted)', lineHeight: 1.5, margin: 0 }}>
                    {skill.short_desc || 'No description provided.'}
                  </p>

                  {/* Fork button */}
                  <div style={{ marginTop: 'auto', paddingTop: 4 }}>
                    <button
                      onClick={() => handleFork(skill)}
                      disabled={!!forking || alreadyForked}
                      style={{
                        width: '100%',
                        padding: '8px 0',
                        borderRadius: 8,
                        border: '1px solid',
                        borderColor: alreadyForked ? 'rgba(52,211,153,0.3)' : 'var(--theme-border, rgba(255,255,255,0.1))',
                        background: alreadyForked ? 'rgba(52,211,153,0.08)' : 'transparent',
                        color: alreadyForked ? '#6ee7b7' : 'var(--theme-text)',
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: alreadyForked ? 'default' : 'pointer',
                        opacity: forking === skillId ? 0.6 : 1,
                        transition: 'all 150ms',
                      }}
                    >
                      {forking === skillId ? 'Forking...' : alreadyForked ? '✓ Forked to library' : 'Fork to my library'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div style={{ textAlign: 'center', color: 'var(--theme-muted)', padding: '60px 0' }}>
            No skills in this category yet.
          </div>
        )}
      </div>
    </div>
  );
};

export default SkillsMarketplace;
