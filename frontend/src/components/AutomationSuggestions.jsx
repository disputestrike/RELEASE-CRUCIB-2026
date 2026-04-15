/**
 * AutomationSuggestions — shown after build completes
 * This is CrucibAI's #1 differentiator: same AI that builds also automates
 * Surfaced in the workspace after a successful build
 */
import React, { useState } from 'react';

const AUTOMATION_TEMPLATES = [
  { id: 'daily_report', icon: '📊', label: 'Daily digest', desc: 'Send a daily summary email at 9am', category: 'notify' },
  { id: 'slack_alert',  icon: '💬', label: 'Slack alerts', desc: 'Notify Slack on key events', category: 'notify' },
  { id: 'email_follow', icon: '✉️', label: 'Email follow-up', desc: 'Auto follow-up with new users', category: 'engage' },
  { id: 'webhook',      icon: '⚡', label: 'Webhook trigger', desc: 'Trigger on record changes', category: 'integrate' },
  { id: 'crm_sync',     icon: '🔄', label: 'CRM sync', desc: 'Sync leads to your CRM nightly', category: 'integrate' },
  { id: 'cleanup_job',  icon: '🧹', label: 'Scheduled cleanup', desc: 'Archive old data weekly', category: 'maintain' },
];

export default function AutomationSuggestions({ jobId, token, onClose, onCreated }) {
  const [creating, setCreating] = useState(null);
  const [created, setCreated] = useState(new Set());

  const handleCreate = async (tmpl) => {
    setCreating(tmpl.id);
    try {
      const API = (typeof process !== 'undefined' && process.env?.REACT_APP_API_URL) || '';
      const res = await fetch(`${API}/api/builds/${jobId}/automation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ description: tmpl.desc }),
      });
      if (res.ok) {
        setCreated(prev => new Set([...prev, tmpl.id]));
        onCreated?.(tmpl);
      }
    } catch {}
    finally { setCreating(null); }
  };

  return (
    <div style={{
      background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12,
      padding: 20, marginTop: 16, boxShadow: '0 1px 8px rgba(0,0,0,0.06)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#111' }}>
            Automate your app
          </div>
          <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>
            The same AI that built it can run these for you
          </div>
        </div>
        {onClose && (
          <button onClick={onClose} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: '#9ca3af', fontSize: 16, padding: '0 4px',
          }}>×</button>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        {AUTOMATION_TEMPLATES.map(tmpl => {
          const isDone = created.has(tmpl.id);
          const isLoading = creating === tmpl.id;
          return (
            <button
              key={tmpl.id}
              onClick={() => !isDone && handleCreate(tmpl)}
              disabled={isDone || isLoading}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: 10, padding: 12,
                background: isDone ? '#f0fdf4' : '#fafafa',
                border: `1px solid ${isDone ? '#bbf7d0' : '#e5e7eb'}`,
                borderRadius: 8, cursor: isDone ? 'default' : 'pointer',
                textAlign: 'left', transition: 'all 0.15s',
              }}
            >
              <span style={{ fontSize: 16 }}>{tmpl.icon}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: isDone ? '#16a34a' : '#374151', marginBottom: 2 }}>
                  {isDone ? '✓ ' : ''}{tmpl.label}
                </div>
                <div style={{ fontSize: 11, color: '#9ca3af', lineHeight: 1.4 }}>
                  {isLoading ? 'Creating…' : tmpl.desc}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <div style={{ marginTop: 12, fontSize: 11, color: '#9ca3af', textAlign: 'center' }}>
        All automations run inside CrucibAI — no separate tools needed
      </div>
    </div>
  );
}
