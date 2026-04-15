import { useState, useEffect } from 'react';
import {
  Radio, Globe, Slack, Smartphone, Webhook, Plus, X, Check,
  Copy, ExternalLink, Settings, CheckCircle, AlertCircle, Clock, Zap
} from 'lucide-react';
import { useAuth } from '../App';
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
  info:    '#3b82f6',
  input:   'var(--theme-input, rgba(255,255,255,0.06))',
};

const CHANNEL_TYPES = [
  { id: 'web_widget', label: 'Web Chat Widget', icon: Globe, color: '#3b82f6', description: 'Embed a chat widget on your website' },
  { id: 'slack', label: 'Slack Bot', icon: Zap, color: '#4a154b', description: 'Connect your AI to a Slack workspace' },
  { id: 'whatsapp', label: 'WhatsApp', icon: Smartphone, color: '#25D366', description: 'Reach customers on WhatsApp via Twilio' },
  { id: 'api_webhook', label: 'API / Webhook', icon: Webhook, color: '#737373', description: 'POST messages directly to the API endpoint' },
];

const Inp = ({ value, onChange, placeholder, type = 'text', readOnly }) => (
  <input type={type} value={value} onChange={onChange} placeholder={placeholder} readOnly={readOnly}
    style={{ width: '100%', boxSizing: 'border-box', padding: '9px 12px', background: readOnly ? 'rgba(255,255,255,0.03)' : T.input, border: `1.5px solid ${T.border}`, borderRadius: 8, color: T.text, fontSize: 13, outline: 'none', fontFamily: readOnly ? 'monospace' : 'inherit', cursor: readOnly ? 'text' : 'auto' }} />
);

const Fld = ({ label, children }) => (
  <div style={{ marginBottom: 14 }}>
    <p style={{ fontSize: 11, fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }}>{label}</p>
    {children}
  </div>
);

const CodeBlock = ({ code }) => {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard?.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div style={{ position: 'relative', marginTop: 8 }}>
      <pre style={{ background: 'rgba(0,0,0,0.4)', borderRadius: 8, padding: '12px 14px', fontSize: 11, color: '#a5f3fc', overflowX: 'auto', margin: 0, lineHeight: 1.6, border: `1px solid ${T.border}`, fontFamily: 'monospace' }}>
        {code}
      </pre>
      <button onClick={copy} style={{ position: 'absolute', top: 8, right: 8, padding: '4px 8px', borderRadius: 6, background: 'rgba(255,255,255,0.1)', border: 'none', color: copied ? T.success : T.muted, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
        {copied ? <Check size={11} /> : <Copy size={11} />} {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
  );
};

const widgetEmbedCode = (cfg) => `<script>
  window.CrucibConfig = {
    title: "${cfg.title || 'Chat with us'}",
    color: "${cfg.color || '#1A1A1A'}",
    position: "${cfg.position || 'bottom-right'}"
  };
</script>
<script src="https://cdn.crucibai.com/widget.js" async></script>`;

export default function ChannelsPage() {
  const { token } = useAuth();
  const headers = { Authorization: 'Bearer ' + token };

  const [channels, setChannels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [configuring, setConfiguring] = useState(null); // channel type id
  const [testing, setTesting] = useState(null);

  // Form state per type
  const [webForm, setWebForm] = useState({ title: 'Chat with us', color: '#1A1A1A', position: 'bottom-right' });
  const [slackForm, setSlackForm] = useState({ webhook_url: '' });
  const [waForm, setWaForm] = useState({ account_sid: '', auth_token: '', phone: '' });
  const [saving, setSaving] = useState(false);

  const fetchChannels = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API}/channels`, { headers });
      setChannels(res.data?.channels || res.data || []);
    } catch (e) {
      setError('Failed to load channels.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchChannels(); }, []);

  const handleSave = async (typeId) => {
    setSaving(true);
    let payload = { type: typeId };
    if (typeId === 'web_widget') payload = { ...payload, config: webForm };
    else if (typeId === 'slack') payload = { ...payload, config: slackForm };
    else if (typeId === 'whatsapp') payload = { ...payload, config: waForm };
    else if (typeId === 'api_webhook') payload = { ...payload, config: {} };
    try {
      await axios.post(`${API}/channels`, payload, { headers });
      setConfiguring(null);
      fetchChannels();
    } catch (e) {
      setError('Failed to save channel configuration.');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (id) => {
    setTesting(id);
    try {
      await axios.post(`${API}/channels/${id}/test`, {}, { headers });
    } catch (e) {
      setError('Test failed.');
    } finally {
      setTimeout(() => setTesting(null), 1500);
    }
  };

  const statusIcon = (status) => {
    if (status === 'active') return <CheckCircle size={14} style={{ color: T.success }} />;
    if (status === 'error') return <AlertCircle size={14} style={{ color: T.danger }} />;
    return <Clock size={14} style={{ color: '#737373' }} />;
  };

  return (
    <div style={{ minHeight: '100vh', background: T.bg, color: T.text }}>
      {/* Header */}
      <div style={{ padding: '28px 32px 0', display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(245,158,11,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Radio size={20} style={{ color: '#737373' }} />
        </div>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Channels</h1>
          <p style={{ fontSize: 13, color: T.muted, margin: 0 }}>Configure where your AI connects</p>
        </div>
      </div>

      {error && (
        <div style={{ margin: '16px 32px', padding: '10px 14px', background: 'rgba(239,68,68,0.1)', border: `1px solid ${T.danger}`, borderRadius: 8, color: T.danger, fontSize: 13 }}>
          {error}
          <button onClick={() => setError('')} style={{ float: 'right', background: 'none', border: 'none', color: T.danger, cursor: 'pointer' }}><X size={14} /></button>
        </div>
      )}

      <div style={{ padding: '24px 32px' }}>
        {/* Channel type cards */}
        <p style={{ fontSize: 11, fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 14 }}>Available Channels</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 14, marginBottom: 32 }}>
          {CHANNEL_TYPES.map(ct => {
            const Icon = ct.icon;
            const isOpen = configuring === ct.id;
            return (
              <div key={ct.id}>
                <button
                  onClick={() => setConfiguring(isOpen ? null : ct.id)}
                  style={{ width: '100%', background: isOpen ? `${ct.color}15` : T.surface, borderRadius: 12, padding: 20, border: `1.5px solid ${isOpen ? ct.color : T.border}`, cursor: 'pointer', textAlign: 'left', transition: 'border-color 0.2s' }}
                >
                  <div style={{ width: 40, height: 40, borderRadius: 10, background: `${ct.color}20`, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}>
                    <Icon size={20} style={{ color: ct.color }} />
                  </div>
                  <p style={{ fontSize: 14, fontWeight: 700, color: T.text, margin: '0 0 4px' }}>{ct.label}</p>
                  <p style={{ fontSize: 12, color: T.muted, margin: 0, lineHeight: 1.4 }}>{ct.description}</p>
                  <p style={{ fontSize: 12, fontWeight: 600, color: ct.color, margin: '10px 0 0', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Settings size={11} /> Configure
                  </p>
                </button>
              </div>
            );
          })}
        </div>

        {/* Config panel */}
        {configuring && (
          <div style={{ background: T.surface, borderRadius: 14, border: `1px solid ${T.border}`, padding: 24, marginBottom: 32 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
              <p style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>
                {CHANNEL_TYPES.find(c => c.id === configuring)?.label} Configuration
              </p>
              <button onClick={() => setConfiguring(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: T.muted }}><X size={16} /></button>
            </div>

            {configuring === 'web_widget' && (
              <>
                <Fld label="Widget Title"><Inp value={webForm.title} onChange={e => setWebForm(p => ({ ...p, title: e.target.value }))} placeholder="Chat with us" /></Fld>
                <Fld label="Accent Color">
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <input type="color" value={webForm.color} onChange={e => setWebForm(p => ({ ...p, color: e.target.value }))}
                      style={{ width: 40, height: 36, borderRadius: 6, border: `1px solid ${T.border}`, padding: 2, background: T.input, cursor: 'pointer' }} />
                    <Inp value={webForm.color} onChange={e => setWebForm(p => ({ ...p, color: e.target.value }))} placeholder="#1A1A1A" />
                  </div>
                </Fld>
                <Fld label="Position">
                  <div style={{ display: 'flex', gap: 8 }}>
                    {['bottom-right', 'bottom-left'].map(pos => (
                      <button key={pos} onClick={() => setWebForm(p => ({ ...p, position: pos }))}
                        style={{ flex: 1, padding: '8px 0', borderRadius: 8, border: `1.5px solid ${webForm.position === pos ? T.accent : T.border}`, background: webForm.position === pos ? 'rgba(224,90,37,0.1)' : 'transparent', color: webForm.position === pos ? T.accent : T.muted, fontWeight: 600, fontSize: 12, cursor: 'pointer' }}>
                        {pos}
                      </button>
                    ))}
                  </div>
                </Fld>
                <Fld label="Embed Code">
                  <CodeBlock code={widgetEmbedCode(webForm)} />
                </Fld>
              </>
            )}

            {configuring === 'slack' && (
              <Fld label="Slack Incoming Webhook URL">
                <Inp value={slackForm.webhook_url} onChange={e => setSlackForm(p => ({ ...p, webhook_url: e.target.value }))} placeholder="https://hooks.slack.com/services/..." />
              </Fld>
            )}

            {configuring === 'whatsapp' && (
              <>
                <Fld label="Twilio Account SID"><Inp value={waForm.account_sid} onChange={e => setWaForm(p => ({ ...p, account_sid: e.target.value }))} placeholder="ACxxxxxxxxxxxxxxxxxx" /></Fld>
                <Fld label="Twilio Auth Token"><Inp value={waForm.auth_token} onChange={e => setWaForm(p => ({ ...p, auth_token: e.target.value }))} type="password" placeholder="••••••••" /></Fld>
                <Fld label="WhatsApp Phone Number"><Inp value={waForm.phone} onChange={e => setWaForm(p => ({ ...p, phone: e.target.value }))} placeholder="+14155238886" /></Fld>
              </>
            )}

            {configuring === 'api_webhook' && (
              <>
                <Fld label="API Endpoint">
                  <CodeBlock code={`POST ${API}/sessions/incoming\nHeaders: { "X-API-Key": "<your-api-key>" }\nBody: { "user_id": "...", "message": "...", "channel": "api" }`} />
                </Fld>
                <p style={{ fontSize: 12, color: T.muted, marginTop: 8 }}>Find your API key in Settings → API Keys.</p>
              </>
            )}

            <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
              <button onClick={() => setConfiguring(null)} style={{ padding: '9px 18px', borderRadius: 8, background: 'transparent', border: `1px solid ${T.border}`, color: T.muted, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>Cancel</button>
              <button onClick={() => handleSave(configuring)} disabled={saving}
                style={{ padding: '9px 18px', borderRadius: 8, background: T.accent, color: '#fff', fontWeight: 600, fontSize: 13, border: 'none', cursor: 'pointer', opacity: saving ? 0.6 : 1 }}>
                {saving ? 'Saving...' : 'Save Channel'}
              </button>
            </div>
          </div>
        )}

        {/* Configured channels */}
        <p style={{ fontSize: 11, fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 14 }}>Configured Channels</p>
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[1, 2].map(i => <div key={i} style={{ background: T.surface, borderRadius: 12, height: 64, opacity: 0.4, border: `1px solid ${T.border}` }} />)}
          </div>
        ) : channels.length === 0 ? (
          <div style={{ padding: '40px 0', textAlign: 'center' }}>
            <p style={{ fontSize: 14, color: T.muted }}>No channels configured yet. Click a channel type above to set one up.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {channels.map(ch => {
              const ct = CHANNEL_TYPES.find(c => c.id === ch.type);
              const Icon = ct?.icon || Radio;
              return (
                <div key={ch.id} style={{ background: T.surface, borderRadius: 12, padding: '14px 16px', border: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 36, height: 36, borderRadius: 8, background: `${ct?.color || T.accent}20`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <Icon size={16} style={{ color: ct?.color || T.accent }} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>{ct?.label || ch.type}</p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
                      {statusIcon(ch.status)}
                      <span style={{ fontSize: 11, color: T.muted }}>{ch.status || 'configured'}</span>
                    </div>
                  </div>
                  <button onClick={() => handleTest(ch.id)} disabled={testing === ch.id}
                    style={{ padding: '6px 14px', borderRadius: 7, background: 'rgba(255,255,255,0.06)', border: `1px solid ${T.border}`, color: testing === ch.id ? T.success : T.muted, fontWeight: 600, fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                    {testing === ch.id ? <><Check size={11} /> Tested</> : 'Test'}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
