/**
 * DeveloperPortal.jsx — Wave 5: Growth & Ecosystem
 *
 * API key CRUD UI: list keys, create (with copy-modal), revoke, show usage.
 * Also shows SDK install snippets for Python and TypeScript.
 */

import { useEffect, useState } from 'react';

const S = {
  page: {
    background: '#0f1117',
    minHeight: '100vh',
    color: '#e2e8f0',
    fontFamily: 'system-ui, sans-serif',
    padding: '32px',
    maxWidth: '900px',
    margin: '0 auto',
  },
  h1: { fontSize: '26px', fontWeight: 700, color: '#f8fafc', margin: '0 0 4px' },
  subtitle: { color: '#64748b', fontSize: '13px', marginBottom: '32px' },
  section: { marginBottom: '40px' },
  h2: { fontSize: '17px', fontWeight: 600, color: '#e2e8f0', margin: '0 0 16px' },
  card: {
    background: '#1e2435',
    border: '1px solid #2d3748',
    borderRadius: '12px',
    padding: '20px',
    marginBottom: '12px',
  },
  row: { display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' },
  prefix: {
    fontFamily: 'monospace',
    fontSize: '13px',
    color: '#a5b4fc',
    background: '#0f1117',
    padding: '4px 10px',
    borderRadius: '6px',
    border: '1px solid #2d3748',
  },
  keyName: { fontWeight: 600, color: '#f1f5f9', fontSize: '14px' },
  meta: { fontSize: '12px', color: '#64748b' },
  revokedBadge: {
    background: '#ef444422',
    color: '#f87171',
    fontSize: '11px',
    borderRadius: '4px',
    padding: '2px 8px',
    fontWeight: 600,
  },
  activeBadge: {
    background: '#10b98122',
    color: '#34d399',
    fontSize: '11px',
    borderRadius: '4px',
    padding: '2px 8px',
    fontWeight: 600,
  },
  revokeBtn: {
    marginLeft: 'auto',
    padding: '6px 14px',
    background: 'transparent',
    border: '1px solid #ef4444',
    color: '#f87171',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '12px',
  },
  createBtn: {
    padding: '10px 20px',
    background: '#6366f1',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
  },
  input: {
    padding: '8px 14px',
    background: '#0f1117',
    border: '1px solid #334155',
    borderRadius: '8px',
    color: '#e2e8f0',
    fontSize: '14px',
    outline: 'none',
    width: '240px',
  },
  codeBlock: {
    background: '#0a0d14',
    border: '1px solid #2d3748',
    borderRadius: '8px',
    padding: '16px 20px',
    fontFamily: 'monospace',
    fontSize: '13px',
    color: '#a5b4fc',
    whiteSpace: 'pre',
    overflowX: 'auto',
    lineHeight: 1.6,
  },
  tabRow: { display: 'flex', gap: '4px', marginBottom: '12px' },
  tab: (active) => ({
    padding: '6px 16px',
    borderRadius: '6px',
    border: active ? '1px solid #6366f1' : '1px solid #334155',
    background: active ? '#6366f1' : 'transparent',
    color: active ? '#fff' : '#94a3b8',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 500,
  }),
  modal: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.75)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 9999,
  },
  modalBox: {
    background: '#1e2435',
    border: '1px solid #334155',
    borderRadius: '16px',
    padding: '32px',
    width: '520px',
    maxWidth: '92vw',
  },
  modalTitle: { fontSize: '18px', fontWeight: 700, color: '#f1f5f9', margin: '0 0 16px' },
  secretBox: {
    background: '#0a0d14',
    border: '1px solid #6366f1',
    borderRadius: '8px',
    padding: '12px 16px',
    fontFamily: 'monospace',
    fontSize: '13px',
    color: '#a5b4fc',
    wordBreak: 'break-all',
    margin: '8px 0 16px',
  },
  copyBtn: {
    padding: '8px 16px',
    background: '#10b981',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 600,
  },
  doneBtn: {
    padding: '8px 20px',
    background: 'transparent',
    border: '1px solid #334155',
    color: '#94a3b8',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px',
  },
  usageChip: {
    fontSize: '12px',
    color: '#94a3b8',
    background: '#2d3748',
    padding: '2px 8px',
    borderRadius: '999px',
  },
  emptyState: { color: '#64748b', fontSize: '13px', padding: '12px 0' },
};

const PY_SNIPPET = `pip install crucibai

from crucibai import CrucibAI
client = CrucibAI(api_key="crc_YOUR_KEY")

# List marketplace
listings = client.marketplace.listings(kind="template")

# Start a run
run = client.runs.create(prompt="Build a dashboard", mode="build")`;

const TS_SNIPPET = `npm install @crucibai/sdk

import { CrucibAI } from '@crucibai/sdk';
const client = new CrucibAI({ apiKey: 'crc_YOUR_KEY' });

// List marketplace
const { listings } = await client.marketplace.listings({ kind: 'template' });

// Start a run
const run = await client.runs.create({ prompt: 'Build a dashboard', mode: 'build' });`;

export default function DeveloperPortal() {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [secretModal, setSecretModal] = useState(null); // { id, name, prefix, secret }
  const [copied, setCopied] = useState(false);
  const [sdkTab, setSdkTab] = useState('python');
  const [usageMap, setUsageMap] = useState({});
  const [degraded, setDegraded] = useState(false);

  async function fetchKeys() {
    try {
      const r = await fetch('/api/keys');
      const data = await r.json();
      setKeys(data.keys || []);
      setDegraded(!!data.degraded);
    } catch {
      setDegraded(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchKeys(); }, []);

  async function fetchUsage(keyId) {
    try {
      const r = await fetch(`/api/keys/${keyId}/usage`);
      const data = await r.json();
      setUsageMap((m) => ({ ...m, [keyId]: data.calls ?? 0 }));
    } catch {
      setUsageMap((m) => ({ ...m, [keyId]: '—' }));
    }
  }

  useEffect(() => {
    keys.forEach((k) => { if (!k.revoked_at) fetchUsage(k.id); });
  }, [keys]); // eslint-disable-line react-hooks/exhaustive-deps

  async function createKey() {
    if (!newKeyName.trim()) return;
    setCreating(true);
    try {
      const r = await fetch('/api/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newKeyName.trim() }),
      });
      const data = await r.json();
      setSecretModal(data);
      setNewKeyName('');
      fetchKeys();
    } catch {
      alert('Failed to create key');
    } finally {
      setCreating(false);
    }
  }

  async function revokeKey(id) {
    if (!confirm('Revoke this API key? This cannot be undone.')) return;
    try {
      await fetch(`/api/keys/${id}`, { method: 'DELETE' });
      fetchKeys();
    } catch {
      alert('Failed to revoke key');
    }
  }

  function copySecret() {
    if (secretModal?.secret) {
      navigator.clipboard.writeText(secretModal.secret).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  }

  return (
    <div style={S.page}>
      <h1 style={S.h1}>Developer Portal</h1>
      <p style={S.subtitle}>
        Manage API keys and integrate CrucibAI into your own apps.
        {degraded && ' (degraded — DB unavailable)'}
      </p>

      {/* API Keys Section */}
      <div style={S.section}>
        <h2 style={S.h2}>API Keys</h2>

        <div style={{ ...S.row, marginBottom: '20px' }}>
          <input
            style={S.input}
            placeholder="Key name (e.g. my-app-prod)"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && createKey()}
          />
          <button style={S.createBtn} onClick={createKey} disabled={creating || !newKeyName.trim()}>
            {creating ? 'Creating…' : '+ Create Key'}
          </button>
        </div>

        {loading ? (
          <p style={S.emptyState}>Loading keys…</p>
        ) : keys.length === 0 ? (
          <p style={S.emptyState}>No API keys yet. Create one above.</p>
        ) : (
          keys.map((k) => (
            <div key={k.id} style={S.card}>
              <div style={S.row}>
                <div>
                  <div style={S.keyName}>{k.name}</div>
                  <div style={S.meta}>Created {k.created_at ? new Date(k.created_at).toLocaleDateString() : '—'}</div>
                </div>
                <span style={S.prefix}>{k.prefix}…</span>
                <span style={k.revoked_at ? S.revokedBadge : S.activeBadge}>
                  {k.revoked_at ? 'Revoked' : 'Active'}
                </span>
                {!k.revoked_at && (
                  <span style={S.usageChip}>
                    {usageMap[k.id] !== undefined ? `${usageMap[k.id]} calls` : 'loading…'}
                  </span>
                )}
                {!k.revoked_at && (
                  <button style={S.revokeBtn} onClick={() => revokeKey(k.id)}>
                    Revoke
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* SDK Snippets */}
      <div style={S.section}>
        <h2 style={S.h2}>SDK Quickstart</h2>
        <div style={S.tabRow}>
          <button style={S.tab(sdkTab === 'python')} onClick={() => setSdkTab('python')}>Python</button>
          <button style={S.tab(sdkTab === 'typescript')} onClick={() => setSdkTab('typescript')}>TypeScript</button>
        </div>
        <div style={S.codeBlock}>
          {sdkTab === 'python' ? PY_SNIPPET : TS_SNIPPET}
        </div>
      </div>

      {/* Secret Modal */}
      {secretModal && (
        <div style={S.modal} onClick={() => setSecretModal(null)}>
          <div style={S.modalBox} onClick={(e) => e.stopPropagation()}>
            <h2 style={S.modalTitle}>API Key Created</h2>
            <p style={{ color: '#f87171', fontSize: '13px', margin: '0 0 8px' }}>
              Copy this secret now — it will NOT be shown again.
            </p>
            <div style={S.secretBox}>{secretModal.secret}</div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button style={S.copyBtn} onClick={copySecret}>
                {copied ? 'Copied!' : 'Copy Secret'}
              </button>
              <button style={S.doneBtn} onClick={() => setSecretModal(null)}>
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
