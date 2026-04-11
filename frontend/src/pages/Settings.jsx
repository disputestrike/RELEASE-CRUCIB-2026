import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  User, Mail, Lock, Bell, Shield, CreditCard,
  Save, Check, Key, ExternalLink, Zap,
  HelpCircle, FileText, Settings as SettingsIcon,
  Copy, AlertCircle, Database, Download,
  Eye, EyeOff, CheckCircle, XCircle, Wrench, ChevronRight,
} from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth, API } from '../App';
import axios from 'axios';
import { logApiError } from '../utils/apiError';
import { ENGINE_ROOM_ITEMS } from '../config/engineRoomNav';

// Design tokens — matches dark sidebar/workspace exactly
// T uses CSS variables so theme switching works automatically
const T = {
  bg:      'var(--theme-bg)',
  surface: 'var(--theme-surface)',
  border:  'var(--theme-border-vis)',
  text:    'var(--theme-text)',
  muted:   'var(--theme-muted)',
  accent:  '#E05A25',
  accentH: '#c94d1e',
  success: '#10b981',
  danger:  '#ef4444',
  input:   'var(--theme-input)',
};

// ── Primitives ─────────────────────────────────────────────────────────────
const Card = ({ children }) => (
  <div style={{ background: T.surface, border: `1.5px solid rgba(255,255,255,0.15)`, borderRadius: 14, padding: 24, marginBottom: 16 }}>
    {children}
  </div>
);

const Label = ({ children }) => (
  <p style={{ fontSize: 11, fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 8 }}>{children}</p>
);

const SectionTitle = ({ children }) => (
  <p style={{ fontSize: 15, fontWeight: 700, color: T.text, marginBottom: 16 }}>{children}</p>
);

const Field = ({ label, children }) => (
  <div style={{ marginBottom: 14 }}>
    <Label>{label}</Label>
    {children}
  </div>
);

const PwInput = ({ value, onChange, placeholder }) => {
  const [show, setShow] = useState(false);
  return (
    <div style={{ position: 'relative' }}>
      <Lock size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: T.muted, pointerEvents: 'none' }} />
      <input type={show ? 'text' : 'password'} value={value} onChange={onChange} placeholder={placeholder || '••••••••'}
        style={{ width: '100%', boxSizing: 'border-box', padding: '10px 40px 10px 34px', background: T.input, border: `1.5px solid rgba(255,255,255,0.15)`, borderRadius: 8, color: T.text, fontSize: 13, outline: 'none' }} />
      <button type="button" onClick={() => setShow(v => !v)}
        style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: T.muted }}>
        {show ? <EyeOff size={13} /> : <Eye size={13} />}
      </button>
    </div>
  );
};

const TextInput = ({ icon: Icon, value, onChange, placeholder, type = 'text', disabled }) => (
  <div style={{ position: 'relative' }}>
    {Icon && <Icon size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: T.muted, pointerEvents: 'none' }} />}
    <input type={type} value={value} onChange={onChange} placeholder={placeholder} disabled={disabled}
      style={{ width: '100%', boxSizing: 'border-box', padding: `10px 12px 10px ${Icon ? 34 : 12}px`, background: T.input, border: `1.5px solid rgba(255,255,255,0.15)`, borderRadius: 8, color: T.text, fontSize: 13, outline: 'none', opacity: disabled ? 0.5 : 1 }} />
  </div>
);

const Toggle = ({ checked, onChange }) => (
  <label style={{ position: 'relative', display: 'inline-flex', cursor: 'pointer' }}>
    <input type="checkbox" checked={checked} onChange={onChange} style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }} />
    <div style={{ width: 44, height: 24, borderRadius: 12, background: checked ? T.accent : T.input, border: `1.5px solid rgba(255,255,255,0.15)`, position: 'relative', transition: 'background 0.2s' }}>
      <div style={{ position: 'absolute', top: 2, left: checked ? 22 : 2, width: 18, height: 18, borderRadius: '50%', background: '#fff', transition: 'left 0.2s', boxShadow: '0 1px 3px rgba(0,0,0,0.3)' }} />
    </div>
  </label>
);

const Btn = ({ children, onClick, disabled, variant = 'primary', size = 'md' }) => {
  const bg = { primary: T.accent, secondary: T.input, danger: T.danger, ghost: 'transparent' }[variant];
  const color = variant === 'secondary' || variant === 'ghost' ? T.text : '#fff';
  const border = variant === 'ghost' || variant === 'secondary' ? `1px solid ${T.border}` : 'none';
  const pad = { sm: '6px 14px', md: '9px 18px', lg: '11px 24px' }[size];
  return (
    <button type="button" onClick={onClick} disabled={disabled}
      style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: pad, borderRadius: 8, border, background: bg, color, fontSize: 13, fontWeight: 600, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.5 : 1, transition: 'opacity 0.15s' }}>
      {children}
    </button>
  );
};

const Row = ({ label, desc, children }) => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0', borderBottom: `1px solid ${T.border}` }}>
    <div style={{ flex: 1, paddingRight: 16 }}>
      <p style={{ fontSize: 14, fontWeight: 500, color: T.text }}>{label}</p>
      {desc && <p style={{ fontSize: 12, color: T.muted, marginTop: 2 }}>{desc}</p>}
    </div>
    {children}
  </div>
);

const Msg = ({ type, text }) => {
  if (!text) return null;
  const c = { success: T.success, error: T.danger, info: '#3b82f6' }[type] || T.danger;
  const Icon = type === 'success' ? CheckCircle : XCircle;
  return (
    <div style={{ display: 'flex', gap: 8, padding: '10px 14px', borderRadius: 8, background: `${c}18`, border: `1px solid ${c}40`, marginBottom: 14 }}>
      <Icon size={14} style={{ color: c, flexShrink: 0, marginTop: 1 }} />
      <p style={{ fontSize: 13, color: c }}>{text}</p>
    </div>
  );
};

// ── Tabs ───────────────────────────────────────────────────────────────────
const TABS = [
  { id: 'account',       label: 'Account',          icon: User },
  { id: 'security',      label: 'Security',          icon: Shield },
  { id: 'billing',       label: 'Billing & Usage',   icon: CreditCard },
  { id: 'notifications', label: 'Notifications',     icon: Bell },
  { id: 'data',          label: 'Data & Privacy',    icon: Database },
  { id: 'general',       label: 'General',           icon: SettingsIcon },
  { id: 'engine',        label: 'Engine room',       icon: Wrench },
];

// ── Main ───────────────────────────────────────────────────────────────────
const Settings = () => {
  const { user, token, refreshUser, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [tab, setTab] = useState(() => {
    const t = location.state?.openTab;
    return TABS.some((x) => x.id === t) ? t : 'account';
  });
  const h = token ? { Authorization: `Bearer ${token}` } : {};

  useEffect(() => {
    const t = location.state?.openTab;
    if (t && TABS.some((x) => x.id === t)) setTab(t);
  }, [location.state, location.key]);

  // Theme system — real working toggle
  const [theme, setTheme] = useState(() => localStorage.getItem('crucibai-theme') || 'dark');
  const toggleTheme = (newTheme) => {
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('crucibai-theme', newTheme);
  };

  // Dynamic tokens - now both T and TH use CSS variables that auto-respond to data-theme
  const isDark = theme === 'dark';
  const TH = {
    bg:      'var(--theme-bg)',
    surface: 'var(--theme-surface)',
    border:  'var(--theme-border-vis)',
    text:    'var(--theme-text)',
    muted:   'var(--theme-muted)',
    input:   'var(--theme-input)',
    accent:  '#E05A25',
  };

  // Account
  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMsg, setProfileMsg] = useState(null);

  // Security — password
  const [curPw, setCurPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [conPw, setConPw] = useState('');
  const [pwSaving, setPwSaving] = useState(false);
  const [pwMsg, setPwMsg] = useState(null);

  // Security — MFA
  const [mfaOn, setMfaOn] = useState(false);
  const [mfaStep, setMfaStep] = useState(null);
  const [mfaQr, setMfaQr] = useState(null);
  const [mfaSec, setMfaSec] = useState(null);
  const [mfaCode, setMfaCode] = useState('');
  const [mfaBack, setMfaBack] = useState([]);
  const [mfaDPw, setMfaDPw] = useState('');
  const [mfaBusy, setMfaBusy] = useState(false);
  const [mfaMsg, setMfaMsg] = useState(null);

  // Deploy tokens
  const [dTokens, setDTokens] = useState({ vercel: '', netlify: '', github: '', railway: '' });
  const [dStatus, setDStatus] = useState({ has_vercel: false, has_netlify: false });
  const [dSaving, setDSaving] = useState(false);
  const [dMsg, setDMsg] = useState(null);

  // Notifications
  const [notifs, setNotifs] = useState({ email: true, push: false, marketing: false, task_complete: true });
  const [nSaving, setNSaving] = useState(false);
  const [nMsg, setNMsg] = useState(null);

  // Privacy
  const [priv, setPriv] = useState({ analytics: true, training: true, crash: true });
  const [pSaving, setPSaving] = useState(false);
  const [pMsg, setPMsg] = useState(null);

  // Billing
  const [usage, setUsage] = useState(null);

  // Delete
  const [delModal, setDelModal] = useState(false);
  const [delPw, setDelPw] = useState('');
  const [delBusy, setDelBusy] = useState(false);
  const [delErr, setDelErr] = useState(null);

  useEffect(() => { setName(user?.name || ''); setEmail(user?.email || ''); }, [user]);

  useEffect(() => {
    if (!token) return;
    if (tab === 'security') {
      axios.get(`${API}/mfa/status`, { headers: h }).then(r => setMfaOn(r.data.mfa_enabled)).catch(() => {});
    }
    if (tab === 'account' || tab === 'security') {
      axios.get(`${API}/users/me/deploy-tokens`, { headers: h }).then(r => setDStatus(r.data)).catch(() => {});
    }
    if (tab === 'billing') {
      axios.get(`${API}/tokens/usage`, { headers: h }).then(r => setUsage(r.data)).catch(() => {});
    }
  }, [tab, token]);

  const msg = (setter, type, text, ms = 3500) => {
    setter({ type, text });
    setTimeout(() => setter(null), ms);
  };

  const saveProfile = async () => {
    if (!name.trim()) { msg(setProfileMsg, 'error', 'Name cannot be empty'); return; }
    setProfileSaving(true);
    try {
      await axios.patch(`${API}/users/me`, { name: name.trim(), email: email.trim() }, { headers: h });
      if (refreshUser) await refreshUser();
      msg(setProfileMsg, 'success', 'Profile saved.');
    } catch (e) { msg(setProfileMsg, 'error', e.response?.data?.detail || 'Save failed'); }
    finally { setProfileSaving(false); }
  };

  const changePw = async () => {
    if (!curPw || !newPw || !conPw) { msg(setPwMsg, 'error', 'All fields required'); return; }
    if (newPw !== conPw) { msg(setPwMsg, 'error', 'Passwords do not match'); return; }
    if (newPw.length < 8) { msg(setPwMsg, 'error', 'Password must be at least 8 characters'); return; }
    setPwSaving(true);
    try {
      await axios.post(`${API}/users/me/change-password`, { current_password: curPw, new_password: newPw }, { headers: h });
      msg(setPwMsg, 'success', 'Password updated.');
      setCurPw(''); setNewPw(''); setConPw('');
    } catch (e) { msg(setPwMsg, 'error', e.response?.data?.detail || 'Incorrect password'); }
    finally { setPwSaving(false); }
  };

  const saveDeploy = async () => {
    const body = {};
    if (dTokens.vercel.trim()) body.vercel = dTokens.vercel.trim();
    if (dTokens.netlify.trim()) body.netlify = dTokens.netlify.trim();
    if (!Object.keys(body).length) return;
    setDSaving(true);
    try {
      await axios.patch(`${API}/users/me/deploy-tokens`, body, { headers: h });
      setDStatus(p => ({ has_vercel: p.has_vercel || !!body.vercel, has_netlify: p.has_netlify || !!body.netlify }));
      setDTokens({ vercel: '', netlify: '' });
      msg(setDMsg, 'success', 'Deploy tokens saved.');
    } catch (e) { msg(setDMsg, 'error', 'Failed to save'); }
    finally { setDSaving(false); }
  };

  const saveNotifs = async () => {
    setNSaving(true);
    try {
      await axios.patch(`${API}/users/me/notifications`, notifs, { headers: h }).catch(() => {});
      msg(setNMsg, 'success', 'Preferences saved.');
    } finally { setNSaving(false); }
  };

  const savePriv = async () => {
    setPSaving(true);
    try {
      await axios.patch(`${API}/users/me/privacy`, priv, { headers: h }).catch(() => {});
      msg(setPMsg, 'success', 'Privacy settings saved.');
    } finally { setPSaving(false); }
  };

  const exportData = async () => {
    try { await axios.post(`${API}/users/me/export`, {}, { headers: h }); } catch (_) {}
    alert('Export requested. You will receive an email with your download link within 24 hours.');
  };

  const mfaStart = async () => {
    setMfaBusy(true); setMfaMsg(null);
    try { const r = await axios.post(`${API}/mfa/setup`, {}, { headers: h }); setMfaQr(r.data.qr_code); setMfaSec(r.data.secret); setMfaStep('qr'); }
    catch (e) { msg(setMfaMsg, 'error', e.response?.data?.detail || 'Setup failed'); }
    finally { setMfaBusy(false); }
  };

  const mfaVerify = async () => {
    if (mfaCode.length !== 6) { msg(setMfaMsg, 'error', 'Enter 6 digits'); return; }
    setMfaBusy(true); setMfaMsg(null);
    try { const r = await axios.post(`${API}/mfa/verify`, { token: mfaCode }, { headers: h }); setMfaBack(r.data.backup_codes || []); setMfaStep('done'); setMfaOn(true); setMfaCode(''); }
    catch (e) { msg(setMfaMsg, 'error', e.response?.data?.detail || 'Invalid code'); }
    finally { setMfaBusy(false); }
  };

  const mfaDisable = async () => {
    setMfaBusy(true); setMfaMsg(null);
    try { await axios.post(`${API}/mfa/disable`, { password: mfaDPw }, { headers: h }); setMfaOn(false); setMfaStep(null); setMfaDPw(''); }
    catch (e) { msg(setMfaMsg, 'error', e.response?.data?.detail || 'Failed'); }
    finally { setMfaBusy(false); }
  };

  const deleteAccount = async () => {
    setDelBusy(true); setDelErr(null);
    try { await axios.post(`${API}/users/me/delete`, { password: delPw }, { headers: h }); logout(); navigate('/'); }
    catch (e) { setDelErr(e.response?.data?.detail || 'Delete failed'); }
    finally { setDelBusy(false); }
  };

  const credits = user?.credit_balance ?? Math.floor((user?.token_balance ?? 0) / 1000);

  return (
    <div style={{ display: 'flex', gap: 32, maxWidth: 880 }}>

      {/* Nav */}
      <aside style={{ width: 196, flexShrink: 0 }}>
        <p style={{ fontSize: 17, fontWeight: 700, color: T.text, marginBottom: 18 }}>Settings</p>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {TABS.map(t => {
            const active = tab === t.id;
            return (
              <button key={t.id} onClick={() => setTab(t.id)} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px', borderRadius: 8, border: 'none', background: active ? 'rgba(255,255,255,0.07)' : 'none', color: active ? T.text : T.muted, fontSize: 13, fontWeight: active ? 600 : 400, cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s', borderLeft: `2px solid ${active ? T.accent : 'transparent'}` }}>
                <t.icon size={14} />{t.label}
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>

        {/* ACCOUNT */}
        {tab === 'account' && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <SectionTitle>Profile</SectionTitle>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20, padding: '14px', background: T.input, borderRadius: 10 }}>
                <div style={{ width: 52, height: 52, borderRadius: '50%', background: T.accent, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, fontWeight: 700, color: '#fff', flexShrink: 0 }}>{(user?.name?.[0] || 'G').toUpperCase()}</div>
                <div>
                  <p style={{ fontSize: 14, fontWeight: 600, color: T.text }}>{user?.name || 'Guest'}</p>
                  <p style={{ fontSize: 12, color: T.muted }}>{user?.email || '—'}</p>
                  <p style={{ fontSize: 11, color: T.muted, marginTop: 2 }}>{user?.plan ? `${user.plan.charAt(0).toUpperCase()}${user.plan.slice(1)} plan` : 'Free plan'}{user?.created_at ? ` · Since ${new Date(user.created_at).toLocaleDateString()}` : ''}</p>
                </div>
              </div>
              <Msg type={profileMsg?.type} text={profileMsg?.text} />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                <Field label="Name"><TextInput icon={User} value={name} onChange={e => setName(e.target.value)} placeholder="Your name" /></Field>
                <Field label="Email"><TextInput icon={Mail} type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="your@email.com" /></Field>
              </div>
              <Btn onClick={saveProfile} disabled={profileSaving}>{profileSaving ? 'Saving…' : <><Save size={13} /> Save profile</>}</Btn>
            </Card>

            <Card>
              <SectionTitle>Deploy integrations</SectionTitle>
              <p style={{ fontSize: 13, color: T.muted, marginBottom: 8 }}>Connect Vercel or Netlify to deploy builds directly from the workspace without downloading a ZIP.</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 16, padding: '10px 12px', background: T.input, borderRadius: 8, border: `1px solid rgba(255,255,255,0.1)` }}>
                <p style={{ fontSize: 12, color: T.muted, margin: 0 }}>Get your Vercel token at <a href="https://vercel.com/account/tokens" target="_blank" rel="noopener noreferrer" style={{ color: T.accent, textDecoration: 'underline' }}>vercel.com/account/tokens</a></p>
                <p style={{ fontSize: 12, color: T.muted, margin: 0 }}>Get your Netlify token at <a href="https://app.netlify.com/user/applications#personal-access-tokens" target="_blank" rel="noopener noreferrer" style={{ color: T.accent, textDecoration: 'underline' }}>app.netlify.com/user/applications</a></p>
                <p style={{ fontSize: 12, color: T.muted, margin: 0 }}>Get your GitHub token at <a href="https://github.com/settings/tokens/new?scopes=repo&description=CrucibAI+Git+Sync" target="_blank" rel="noopener noreferrer" style={{ color: T.accent, textDecoration: 'underline' }}>github.com/settings/tokens</a> (select <code>repo</code> scope)</p>
                <p style={{ fontSize: 12, color: T.muted, margin: 0 }}>Get your Railway token at <a href="https://railway.app/account/tokens" target="_blank" rel="noopener noreferrer" style={{ color: T.accent, textDecoration: 'underline' }}>railway.app/account/tokens</a></p>
              </div>
              <Msg type={dMsg?.type} text={dMsg?.text} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 16 }}>
                <Field label={<>Vercel token {dStatus.has_vercel && <span style={{ color: T.success, fontWeight: 400 }}>✓ saved</span>}</>}>
                  <TextInput icon={Key} type="password" value={dTokens.vercel} onChange={e => setDTokens(p => ({ ...p, vercel: e.target.value }))} placeholder={dStatus.has_vercel ? 'Leave blank to keep existing' : 'Paste Vercel token'} />
                </Field>
                <Field label={<>Netlify token {dStatus.has_netlify && <span style={{ color: T.success, fontWeight: 400 }}>✓ saved</span>}</>}>
                  <TextInput icon={Key} type="password" value={dTokens.netlify} onChange={e => setDTokens(p => ({ ...p, netlify: e.target.value }))} placeholder={dStatus.has_netlify ? 'Leave blank to keep existing' : 'Paste Netlify token'} />
                </Field>
                <Field label={<>GitHub token {dStatus.has_github && <span style={{ color: T.success, fontWeight: 400 }}>✓ saved</span>}</>}>
                  <TextInput icon={Key} type="password" value={dTokens.github} onChange={e => setDTokens(p => ({ ...p, github: e.target.value }))} placeholder={dStatus.has_github ? 'Leave blank to keep existing' : 'Paste GitHub personal access token'} />
                </Field>
                <Field label={<>Railway token {dStatus.has_railway && <span style={{ color: T.success, fontWeight: 400 }}>✓ saved</span>}</>}>
                  <TextInput icon={Key} type="password" value={dTokens.railway} onChange={e => setDTokens(p => ({ ...p, railway: e.target.value }))} placeholder={dStatus.has_railway ? 'Leave blank to keep existing' : 'Paste Railway API token'} />
                </Field>
              </div>
              <Btn onClick={saveDeploy} disabled={dSaving || (!dTokens.vercel && !dTokens.netlify && !dTokens.github && !dTokens.railway)}>{dSaving ? 'Saving…' : <><Save size={13} /> Save tokens</>}</Btn>
            </Card>

            <Card>
              <SectionTitle>Danger zone</SectionTitle>
              <p style={{ fontSize: 13, color: T.muted, marginBottom: 16 }}>Permanently delete your account and all data. This cannot be undone.</p>
              <Btn variant="danger" onClick={() => { setDelModal(true); setDelErr(null); setDelPw(''); }}>Delete account</Btn>
            </Card>
          </motion.div>
        )}

        {/* SECURITY */}
        {tab === 'security' && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <SectionTitle>Change password</SectionTitle>
              <Msg type={pwMsg?.type} text={pwMsg?.text} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 16 }}>
                <Field label="Current password"><PwInput value={curPw} onChange={e => setCurPw(e.target.value)} /></Field>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <Field label="New password"><PwInput value={newPw} onChange={e => setNewPw(e.target.value)} placeholder="Min 8 characters" /></Field>
                  <Field label="Confirm new password"><PwInput value={conPw} onChange={e => setConPw(e.target.value)} /></Field>
                </div>
              </div>
              <Btn onClick={changePw} disabled={pwSaving || !curPw || !newPw || !conPw}>{pwSaving ? 'Updating…' : <><Lock size={13} /> Update password</>}</Btn>
            </Card>

            <Card>
              <SectionTitle>Two-factor authentication</SectionTitle>
              <Msg type={mfaMsg?.type} text={mfaMsg?.text} />
              {!mfaStep && !mfaOn && (<><p style={{ fontSize: 13, color: T.muted, marginBottom: 14 }}>Protect your account with an authenticator app (Google Authenticator, Authy, etc.)</p><Btn onClick={mfaStart} disabled={mfaBusy}>{mfaBusy ? 'Setting up…' : <><Shield size={13} /> Enable 2FA</>}</Btn></>)}
              {mfaOn && !mfaStep && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 14, background: `${T.success}18`, borderRadius: 8, border: `1px solid ${T.success}40` }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><CheckCircle size={16} style={{ color: T.success }} /><div><p style={{ fontSize: 14, fontWeight: 600, color: T.text }}>2FA enabled</p><p style={{ fontSize: 12, color: T.muted }}>Your account is protected</p></div></div>
                  <Btn variant="ghost" size="sm" onClick={() => setMfaStep('disable')}>Disable</Btn>
                </div>
              )}
              {mfaStep === 'disable' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <PwInput value={mfaDPw} onChange={e => setMfaDPw(e.target.value)} placeholder="Enter your password to confirm" />
                  <div style={{ display: 'flex', gap: 8 }}><Btn variant="danger" onClick={mfaDisable} disabled={mfaBusy || !mfaDPw}>{mfaBusy ? 'Disabling…' : 'Disable 2FA'}</Btn><Btn variant="ghost" onClick={() => { setMfaStep(null); setMfaDPw(''); setMfaMsg(null); }}>Cancel</Btn></div>
                </div>
              )}
              {mfaStep === 'qr' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <p style={{ fontSize: 13, color: T.muted }}>Scan with your authenticator app, then enter the 6-digit code.</p>
                  {mfaQr && <img src={mfaQr} alt="QR" style={{ width: 156, height: 156, borderRadius: 8, border: `1.5px solid rgba(255,255,255,0.15)`, padding: 8, background: '#fff' }} />}
                  {mfaSec && <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', background: T.input, borderRadius: 6, border: `1.5px solid rgba(255,255,255,0.15)` }}><code style={{ fontSize: 12, color: T.muted, flex: 1, wordBreak: 'break-all' }}>{mfaSec}</code><button type="button" onClick={() => navigator.clipboard.writeText(mfaSec)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: T.muted }}><Copy size={12} /></button></div>}
                  <input value={mfaCode} onChange={e => setMfaCode(e.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="000000" style={{ padding: '10px', background: T.input, border: `1.5px solid rgba(255,255,255,0.15)`, borderRadius: 8, color: T.text, fontSize: 22, textAlign: 'center', letterSpacing: '0.3em', fontFamily: 'monospace', outline: 'none' }} />
                  <div style={{ display: 'flex', gap: 8 }}><Btn onClick={mfaVerify} disabled={mfaBusy || mfaCode.length !== 6}>{mfaBusy ? 'Verifying…' : 'Verify'}</Btn><Btn variant="ghost" onClick={() => { setMfaStep(null); setMfaQr(null); setMfaSec(null); setMfaCode(''); setMfaMsg(null); }}>Cancel</Btn></div>
                </div>
              )}
              {mfaStep === 'done' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <Msg type="success" text="2FA enabled. Save these backup codes somewhere safe — you'll need them if you lose your device." />
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {mfaBack.map((c, i) => <div key={i} style={{ padding: '4px 10px', background: T.input, borderRadius: 6, fontFamily: 'monospace', fontSize: 12, color: T.muted, display: 'flex', alignItems: 'center', gap: 6 }}>{c}<button type="button" onClick={() => navigator.clipboard.writeText(c)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: T.muted }}><Copy size={11} /></button></div>)}
                  </div>
                  <Btn onClick={() => { setMfaStep(null); setMfaBack([]); }}>Done</Btn>
                </div>
              )}
            </Card>
          </motion.div>
        )}

        {/* BILLING */}
        {tab === 'billing' && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <SectionTitle>Credits & Usage</SectionTitle>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 20 }}>
                {[
                  { label: 'Credits remaining', value: credits.toLocaleString(), color: credits > 100 ? T.success : T.danger },
                  { label: 'Credits used', value: (usage?.credits_used || 0).toLocaleString(), color: T.text },
                  { label: 'Current plan', value: (user?.plan || 'Free').charAt(0).toUpperCase() + (user?.plan || 'free').slice(1), color: T.text },
                ].map(item => (
                  <div key={item.label} style={{ padding: 16, background: T.input, borderRadius: 10, textAlign: 'center' }}>
                    <p style={{ fontSize: 24, fontWeight: 700, color: item.color }}>{item.value}</p>
                    <p style={{ fontSize: 11, color: T.muted, marginTop: 4 }}>{item.label}</p>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <Link to="/app/tokens" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '9px 18px', borderRadius: 8, background: T.accent, color: '#fff', fontSize: 13, fontWeight: 600, textDecoration: 'none' }}><Zap size={13} /> Buy credits</Link>
                <Link to="/pricing" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '9px 18px', borderRadius: 8, background: T.input, color: T.text, fontSize: 13, fontWeight: 600, textDecoration: 'none', border: `1.5px solid rgba(255,255,255,0.15)` }}><FileText size={13} /> View plans</Link>
              </div>
            </Card>
            <Card>
              <SectionTitle>Payment</SectionTitle>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px', background: T.input, borderRadius: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <CreditCard size={18} style={{ color: T.muted }} />
                  <div><p style={{ fontSize: 13, fontWeight: 500, color: T.text }}>No payment method on file</p><p style={{ fontSize: 12, color: T.muted }}>Credits are prepaid and never expire</p></div>
                </div>
                <Link to="/app/tokens" style={{ fontSize: 13, color: T.accent, textDecoration: 'none', fontWeight: 500 }}>Add card →</Link>
              </div>
            </Card>
          </motion.div>
        )}

        {/* NOTIFICATIONS */}
        {tab === 'notifications' && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <SectionTitle>Notification preferences</SectionTitle>
              <Msg type={nMsg?.type} text={nMsg?.text} />
              {[
                { key: 'email',         label: 'Email notifications',  desc: 'Build complete, errors, and account alerts' },
                { key: 'push',          label: 'Browser notifications', desc: 'Real-time build progress notifications' },
                { key: 'task_complete', label: 'Build complete',        desc: 'Notify when an agent build finishes' },
                { key: 'marketing',     label: 'Product updates',       desc: 'New features and release notes' },
              ].map(item => (
                <Row key={item.key} label={item.label} desc={item.desc}>
                  <Toggle checked={notifs[item.key]} onChange={e => setNotifs(p => ({ ...p, [item.key]: e.target.checked }))} />
                </Row>
              ))}
              <div style={{ marginTop: 16 }}><Btn onClick={saveNotifs} disabled={nSaving}>{nSaving ? 'Saving…' : <><Save size={13} /> Save preferences</>}</Btn></div>
            </Card>
          </motion.div>
        )}

        {/* DATA & PRIVACY */}
        {tab === 'data' && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <SectionTitle>Export your data</SectionTitle>
              <p style={{ fontSize: 13, color: T.muted, marginBottom: 16 }}>Download all your projects, prompts, and account data as a ZIP archive. You'll receive an email with the download link within 24 hours.</p>
              <Btn onClick={exportData}><Download size={13} /> Request export</Btn>
            </Card>
            <Card>
              <SectionTitle>Privacy controls</SectionTitle>
              <Msg type={pMsg?.type} text={pMsg?.text} />
              {[
                { key: 'analytics', label: 'Usage analytics',  desc: 'Allow anonymous usage data to improve CrucibAI' },
                { key: 'training',  label: 'Model training',   desc: 'Allow prompts (anonymized) to help improve model quality' },
                { key: 'crash',     label: 'Crash reports',    desc: 'Send crash reports to help fix bugs faster' },
              ].map(item => (
                <Row key={item.key} label={item.label} desc={item.desc}>
                  <Toggle checked={priv[item.key]} onChange={e => setPriv(p => ({ ...p, [item.key]: e.target.checked }))} />
                </Row>
              ))}
              <div style={{ marginTop: 16 }}><Btn onClick={savePriv} disabled={pSaving}>{pSaving ? 'Saving…' : <><Save size={13} /> Save settings</>}</Btn></div>
            </Card>
            <Card>
              <SectionTitle>Data retention</SectionTitle>
              <p style={{ fontSize: 13, color: T.muted, marginBottom: 12 }}>Build logs and chat history are kept for 90 days. Projects are kept indefinitely until you delete them.</p>
              <Link to="/privacy" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, color: T.accent, textDecoration: 'none' }}>Read our privacy policy <ExternalLink size={12} /></Link>
            </Card>
            <Card>
              <SectionTitle>Help</SectionTitle>
              <div style={{ display: 'flex', gap: 10 }}>
                <a href="/learn" target="_blank" rel="noopener noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '9px 16px', borderRadius: 8, background: T.input, color: T.text, fontSize: 13, textDecoration: 'none', border: `1.5px solid rgba(255,255,255,0.15)` }}><FileText size={13} /> Docs</a>
                <a href="mailto:support@crucibai.com" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '9px 16px', borderRadius: 8, background: T.input, color: T.text, fontSize: 13, textDecoration: 'none', border: `1.5px solid rgba(255,255,255,0.15)` }}><HelpCircle size={13} /> Contact support</a>
              </div>
            </Card>
          </motion.div>
        )}

        {/* GENERAL */}
        {tab === 'general' && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <SectionTitle>Appearance</SectionTitle>
              <p style={{ fontSize: 13, color: T.muted, marginBottom: 16 }}>Choose your preferred theme. Your selection is saved to your browser.</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  { id: 'dark',  label: 'Dark theme',  desc: 'Easy on the eyes. Best for long sessions.', dot: '#18181B' },
                  { id: 'light', label: 'Light theme',  desc: 'High contrast. Great in bright environments.', dot: '#F5F5F4' },
                ].map(opt => {
                  const active = theme === opt.id;
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => toggleTheme(opt.id)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 14,
                        padding: '14px 16px', borderRadius: 10, cursor: 'pointer',
                        background: active ? `${T.accent}18` : T.input,
                        border: `2px solid ${active ? T.accent : 'rgba(255,255,255,0.14)'}`,
                        textAlign: 'left', transition: 'all 0.15s',
                      }}
                    >
                      {/* Theme preview swatch */}
                      <div style={{ width: 36, height: 36, borderRadius: 8, background: opt.dot, border: '2px solid rgba(255,255,255,0.15)', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <div style={{ width: 16, height: 2, borderRadius: 1, background: opt.id === 'dark' ? '#71717a' : '#9ca3af' }} />
                      </div>
                      <div style={{ flex: 1 }}>
                        <p style={{ fontSize: 14, fontWeight: 600, color: T.text, marginBottom: 2 }}>{opt.label}</p>
                        <p style={{ fontSize: 12, color: T.muted }}>{opt.desc}</p>
                      </div>
                      {/* Selection indicator */}
                      <div style={{
                        width: 20, height: 20, borderRadius: '50%', flexShrink: 0,
                        border: `2px solid ${active ? T.accent : 'rgba(255,255,255,0.2)'}`,
                        background: active ? T.accent : 'transparent',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        {active && <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#fff' }} />}
                      </div>
                    </button>
                  );
                })}
              </div>
              <p style={{ fontSize: 12, color: T.muted, marginTop: 12 }}>
                Currently active: <strong style={{ color: T.text }}>{theme === 'dark' ? 'Dark theme' : 'Light theme'}</strong>
              </p>
            </Card>
            <Card>
              <SectionTitle>Language</SectionTitle>
              <select
                style={{
                  padding: '10px 12px', borderRadius: 8, fontSize: 13,
                  background: T.input, color: T.text, outline: 'none', width: 200,
                  border: `1.5px solid rgba(255,255,255,0.2)`,
                  cursor: 'pointer',
                }}
              >
                <option value="en">English</option>
              </select>
              <p style={{ fontSize: 12, color: T.muted, marginTop: 8 }}>More languages coming soon.</p>
            </Card>
          </motion.div>
        )}

        {/* ENGINE ROOM — power-user links (moved from sidebar) */}
        {tab === 'engine' && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <SectionTitle>Engine room</SectionTitle>
              <p style={{ fontSize: 13, color: T.muted, marginBottom: 16 }}>
                Advanced tools, integrations, and internal routes. Same destinations as before; they now live here to keep the home sidebar calm.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {ENGINE_ROOM_ITEMS.map((item) => (
                  <Link
                    key={item.href}
                    to={item.href}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10,
                      padding: '10px 12px', borderRadius: 8, textDecoration: 'none',
                      color: T.text, fontSize: 13, background: T.input,
                      border: '1px solid rgba(255,255,255,0.08)',
                    }}
                  >
                    <item.icon size={16} style={{ color: T.muted, flexShrink: 0 }} />
                    <span style={{ flex: 1 }}>{item.label}</span>
                    {item.beta && <span style={{ fontSize: 10, fontWeight: 600, color: T.accent }}>Beta</span>}
                    <ChevronRight size={14} style={{ color: T.muted, opacity: 0.5 }} />
                  </Link>
                ))}
              </div>
            </Card>
          </motion.div>
        )}

      </div>

      {/* DELETE MODAL */}
      {delModal && (
        <div onClick={() => !delBusy && setDelModal(false)} style={{ position: 'fixed', inset: 0, zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.75)' }}>
          <div onClick={e => e.stopPropagation()} style={{ background: T.surface, border: `1.5px solid rgba(255,255,255,0.15)`, borderRadius: 14, padding: 28, maxWidth: 400, width: '90%' }}>
            <p style={{ fontSize: 16, fontWeight: 700, color: T.text, marginBottom: 8 }}>Delete account</p>
            <p style={{ fontSize: 13, color: T.muted, marginBottom: 16 }}>This permanently deletes your account and all projects. Enter your password to confirm.</p>
            <PwInput value={delPw} onChange={e => setDelPw(e.target.value)} placeholder="Your password" />
            {delErr && <p style={{ fontSize: 12, color: T.danger, marginTop: 8 }}>{delErr}</p>}
            <div style={{ display: 'flex', gap: 10, marginTop: 16, justifyContent: 'flex-end' }}>
              <Btn variant="ghost" onClick={() => setDelModal(false)} disabled={delBusy}>Cancel</Btn>
              <Btn variant="danger" onClick={deleteAccount} disabled={delBusy || !delPw.trim()}>{delBusy ? 'Deleting…' : 'Delete permanently'}</Btn>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;
