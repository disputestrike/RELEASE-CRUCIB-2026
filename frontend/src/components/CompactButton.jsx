/** CF28 — CompactButton: one-click context compaction for the active session. */
import { useState } from 'react';
import { API_BASE as API } from '../apiBase';

export default function CompactButton({ sessionId, messages, onCompacted }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  const doCompact = async () => {
    setBusy(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers.Authorization = `Bearer ${token}`;
      const r = await fetch(`${API}/runtime/compact`, {
        method: 'POST', headers,
        body: JSON.stringify({ session_id: sessionId || 'default', target_tokens: 4000, messages: messages || [] }),
      });
      const data = await r.json();
      setResult(data);
      if (onCompacted) onCompacted(data);
    } catch {
      setResult({ error: 'compact failed' });
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      onClick={doCompact}
      disabled={busy}
      data-testid="compact-button"
      title="Compact conversation context to reduce token usage"
      style={{
        padding: '6px 12px', borderRadius: 8, background: '#f4f4f5',
        border: '1px solid #e4e4e7', fontSize: 12, fontWeight: 500, cursor: 'pointer',
      }}
    >
      {busy ? 'Compacting…' : result ? `✓ ${result.tokens_before}→${result.tokens_after_target}` : 'Compact context'}
    </button>
  );
}
