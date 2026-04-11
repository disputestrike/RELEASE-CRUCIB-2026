import { useState, useEffect } from 'react';
import {
  Users, Plus, X, Mail, Shield, Crown, Edit2, Trash2,
  Clock, CheckCircle, AlertCircle, ChevronDown
} from 'lucide-react';
import { useAuth, API } from '../App';
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
  info:    '#3b82f6',
  warn:    '#737373',
  input:   'var(--theme-input, rgba(255,255,255,0.06))',
};

const ROLES = ['owner', 'admin', 'editor', 'viewer'];

const roleConfig = {
  owner:  { color: '#525252', label: 'Owner',  icon: Crown },
  admin:  { color: '#8b5cf6', label: 'Admin',  icon: Shield },
  editor: { color: '#3b82f6', label: 'Editor', icon: Edit2 },
  viewer: { color: T.muted,   label: 'Viewer', icon: Users },
};

const RoleBadge = ({ role }) => {
  const cfg = roleConfig[role] || roleConfig.viewer;
  const Icon = cfg.icon;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 9px', borderRadius: 20, fontSize: 11, fontWeight: 600, background: `${cfg.color}22`, color: cfg.color }}>
      <Icon size={10} /> {cfg.label}
    </span>
  );
};

const Avatar = ({ name, email, size = 36 }) => {
  const initial = (name || email || '?').charAt(0).toUpperCase();
  const colors = ['#1A1A1A', '#404040', '#737373', '#A3A3A3', '#D4D4D4'];
  const idx = (name || email || '').charCodeAt(0) % colors.length;
  return (
    <div style={{ width: size, height: size, borderRadius: '50%', background: colors[idx], display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: size * 0.38, fontWeight: 700, color: '#fff', flexShrink: 0 }}>
      {initial}
    </div>
  );
};

const Inp = ({ value, onChange, placeholder, type = 'text' }) => (
  <input type={type} value={value} onChange={onChange} placeholder={placeholder}
    style={{ width: '100%', boxSizing: 'border-box', padding: '9px 12px', background: T.input, border: `1.5px solid ${T.border}`, borderRadius: 8, color: T.text, fontSize: 13, outline: 'none' }} />
);

const Sel = ({ value, onChange, options }) => (
  <select value={value} onChange={onChange}
    style={{ width: '100%', boxSizing: 'border-box', padding: '9px 12px', background: T.input, border: `1.5px solid ${T.border}`, borderRadius: 8, color: T.text, fontSize: 13, outline: 'none', cursor: 'pointer' }}>
    {options.map(o => <option key={o} value={o}>{o.charAt(0).toUpperCase() + o.slice(1)}</option>)}
  </select>
);

const Fld = ({ label, children }) => (
  <div style={{ marginBottom: 14 }}>
    <p style={{ fontSize: 11, fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }}>{label}</p>
    {children}
  </div>
);

export default function WorkspaceMembersPage() {
  const { token, user: authUser } = useAuth();
  const headers = { Authorization: 'Bearer ' + token };

  const [workspace, setWorkspace] = useState(null);
  const [members, setMembers] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showInvite, setShowInvite] = useState(false);
  const [inviteForm, setInviteForm] = useState({ email: '', role: 'editor' });
  const [inviting, setSending] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [roleChanging, setRoleChanging] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [wsRes, membersRes, invRes] = await Promise.allSettled([
        axios.get(`${API}/workspace`, { headers }),
        axios.get(`${API}/workspace/members`, { headers }),
        axios.get(`${API}/workspace/members/invitations`, { headers }),
      ]);
      if (wsRes.status === 'fulfilled') setWorkspace(wsRes.value.data?.workspace || wsRes.value.data);
      if (membersRes.status === 'fulfilled') setMembers(membersRes.value.data?.members || membersRes.value.data || []);
      if (invRes.status === 'fulfilled') setInvitations(invRes.value.data?.invitations || invRes.value.data || []);
    } catch (e) {
      setError('Failed to load workspace data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleInvite = async () => {
    if (!inviteForm.email.trim()) return;
    setSending(true);
    try {
      await axios.post(`${API}/workspace/members/invite`, inviteForm, { headers });
      setInviteForm({ email: '', role: 'editor' });
      setShowInvite(false);
      fetchData();
    } catch (e) {
      setError('Failed to send invitation.');
    } finally {
      setSending(false);
    }
  };

  const handleRemove = async (memberId) => {
    try {
      await axios.delete(`${API}/workspace/members/${memberId}`, { headers });
      setMembers(prev => prev.filter(m => m.id !== memberId));
      setDeleteConfirm(null);
    } catch (e) {
      setError('Failed to remove member.');
    }
  };

  const handleRoleChange = async (memberId, newRole) => {
    setRoleChanging(memberId);
    try {
      await axios.put(`${API}/workspace/members/${memberId}/role`, { role: newRole }, { headers });
      setMembers(prev => prev.map(m => m.id === memberId ? { ...m, role: newRole } : m));
    } catch (e) {
      setError('Failed to change role.');
    } finally {
      setRoleChanging(null);
    }
  };

  const canManage = (member) => {
    const myRole = members.find(m => m.user_id === authUser?.id)?.role;
    return (myRole === 'owner' || myRole === 'admin') && member.role !== 'owner';
  };

  return (
    <div style={{ minHeight: '100vh', background: T.bg, color: T.text }}>
      {/* Header */}
      <div style={{ padding: '28px 32px 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(139,92,246,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Users size={20} style={{ color: '#8b5cf6' }} />
          </div>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Members</h1>
            <p style={{ fontSize: 13, color: T.muted, margin: 0 }}>Manage your workspace team</p>
          </div>
        </div>
        <button onClick={() => setShowInvite(v => !v)}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '9px 18px', borderRadius: 10, background: T.accent, color: '#fff', fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer' }}>
          <Plus size={15} /> Invite Member
        </button>
      </div>

      {error && (
        <div style={{ margin: '12px 32px', padding: '10px 14px', background: 'rgba(239,68,68,0.1)', border: `1px solid ${T.danger}`, borderRadius: 8, color: T.danger, fontSize: 13 }}>
          {error}
          <button onClick={() => setError('')} style={{ float: 'right', background: 'none', border: 'none', color: T.danger, cursor: 'pointer' }}><X size={14} /></button>
        </div>
      )}

      <div style={{ padding: '24px 32px' }}>
        {/* Workspace info */}
        {workspace && (
          <div style={{ background: T.surface, borderRadius: 14, border: `1px solid ${T.border}`, padding: '18px 22px', marginBottom: 24 }}>
            <p style={{ fontSize: 16, fontWeight: 700, margin: '0 0 4px' }}>{workspace.name || 'My Workspace'}</p>
            {workspace.description && <p style={{ fontSize: 13, color: T.muted, margin: 0 }}>{workspace.description}</p>}
          </div>
        )}

        {/* Invite form */}
        {showInvite && (
          <div style={{ background: T.surface, borderRadius: 14, border: `1px solid ${T.border}`, padding: 24, marginBottom: 24 }}>
            <p style={{ fontSize: 15, fontWeight: 700, margin: '0 0 18px' }}>Invite Member</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, alignItems: 'end' }}>
              <Fld label="Email Address">
                <div style={{ position: 'relative' }}>
                  <Mail size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: T.muted, pointerEvents: 'none' }} />
                  <input type="email" value={inviteForm.email} onChange={e => setInviteForm(p => ({ ...p, email: e.target.value }))} placeholder="colleague@company.com"
                    style={{ width: '100%', boxSizing: 'border-box', padding: '9px 12px 9px 30px', background: T.input, border: `1.5px solid ${T.border}`, borderRadius: 8, color: T.text, fontSize: 13, outline: 'none' }} />
                </div>
              </Fld>
              <Fld label="Role">
                <select value={inviteForm.role} onChange={e => setInviteForm(p => ({ ...p, role: e.target.value }))}
                  style={{ padding: '9px 12px', background: T.input, border: `1.5px solid ${T.border}`, borderRadius: 8, color: T.text, fontSize: 13, outline: 'none', cursor: 'pointer' }}>
                  {['admin', 'editor', 'viewer'].map(r => <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>)}
                </select>
              </Fld>
            </div>
            <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
              <button onClick={() => setShowInvite(false)} style={{ padding: '9px 18px', borderRadius: 8, background: 'transparent', border: `1px solid ${T.border}`, color: T.muted, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>Cancel</button>
              <button onClick={handleInvite} disabled={inviting || !inviteForm.email.trim()}
                style={{ padding: '9px 18px', borderRadius: 8, background: T.accent, color: '#fff', fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer', opacity: (inviting || !inviteForm.email.trim()) ? 0.6 : 1 }}>
                {inviting ? 'Sending...' : 'Send Invitation'}
              </button>
            </div>
          </div>
        )}

        {/* Members list */}
        <p style={{ fontSize: 11, fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 12 }}>
          Members ({members.length})
        </p>

        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[1, 2, 3].map(i => <div key={i} style={{ background: T.surface, borderRadius: 10, height: 64, opacity: 0.4, border: `1px solid ${T.border}` }} />)}
          </div>
        ) : members.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <Users size={40} style={{ color: T.muted, margin: '0 auto 12px', display: 'block' }} />
            <p style={{ fontSize: 14, color: T.muted, marginBottom: 16 }}>No members yet.</p>
            <button onClick={() => setShowInvite(true)} style={{ padding: '10px 20px', borderRadius: 10, background: T.accent, color: '#fff', fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <Plus size={14} /> Invite your first member
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 28 }}>
            {members.map(member => {
              const isMe = member.user_id === authUser?.id;
              const manageable = canManage(member);
              return (
                <div key={member.id} style={{ background: T.surface, borderRadius: 10, padding: '14px 16px', border: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Avatar name={member.name} email={member.email} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <p style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>{member.name || member.email?.split('@')[0] || 'User'}</p>
                      {isMe && <span style={{ fontSize: 10, color: T.muted, fontWeight: 600 }}>You</span>}
                      <RoleBadge role={member.role} />
                    </div>
                    <div style={{ display: 'flex', gap: 12, marginTop: 2 }}>
                      <p style={{ fontSize: 11, color: T.muted, margin: 0 }}>{member.email}</p>
                      {member.joined_at && <p style={{ fontSize: 11, color: T.muted, margin: 0 }}>Joined {new Date(member.joined_at).toLocaleDateString()}</p>}
                    </div>
                  </div>
                  {manageable && (
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
                      <select
                        value={member.role}
                        onChange={e => handleRoleChange(member.id, e.target.value)}
                        disabled={roleChanging === member.id}
                        style={{ padding: '5px 10px', borderRadius: 7, background: T.input, border: `1px solid ${T.border}`, color: T.text, fontSize: 12, outline: 'none', cursor: 'pointer' }}
                      >
                        {['admin', 'editor', 'viewer'].map(r => <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>)}
                      </select>
                      <button onClick={() => setDeleteConfirm(member.id)}
                        style={{ padding: '5px 8px', borderRadius: 7, background: 'rgba(239,68,68,0.08)', border: `1px solid rgba(239,68,68,0.2)`, color: T.danger, cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                        <Trash2 size={12} />
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Pending invitations */}
        {invitations.length > 0 && (
          <>
            <p style={{ fontSize: 11, fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 12 }}>
              Pending Invitations ({invitations.length})
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {invitations.map(inv => (
                <div key={inv.id} style={{ background: T.surface, borderRadius: 10, padding: '12px 16px', border: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 12, opacity: 0.75 }}>
                  <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <Mail size={14} style={{ color: T.muted }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>{inv.email}</p>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 2 }}>
                      <RoleBadge role={inv.role} />
                      <span style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 11, color: T.warn }}>
                        <Clock size={10} /> Pending
                      </span>
                    </div>
                  </div>
                  {inv.expires_at && (
                    <p style={{ fontSize: 11, color: T.muted, margin: 0, flexShrink: 0 }}>
                      Expires {new Date(inv.expires_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Delete confirmation */}
      {deleteConfirm && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 60, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.6)' }}>
          <div style={{ background: T.surface, borderRadius: 16, padding: 28, width: 360, border: `1px solid ${T.border}` }}>
            <p style={{ fontSize: 16, fontWeight: 700, margin: '0 0 8px' }}>Remove Member?</p>
            <p style={{ fontSize: 13, color: T.muted, margin: '0 0 20px' }}>They will lose access to this workspace.</p>
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => setDeleteConfirm(null)} style={{ flex: 1, padding: '9px 0', borderRadius: 8, background: 'transparent', border: `1px solid ${T.border}`, color: T.muted, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>Cancel</button>
              <button onClick={() => handleRemove(deleteConfirm)} style={{ flex: 1, padding: '9px 0', borderRadius: 8, background: T.danger, color: '#fff', fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer' }}>Remove</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
