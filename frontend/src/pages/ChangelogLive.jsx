import { useEffect, useState } from 'react';

const CHANGELOG_URL = '/api/changelog';

function relativeTime(iso) {
  try {
    const diff = Date.now() - new Date(iso).getTime();
    const s = Math.floor(diff / 1000);
    if (s < 60) return s + 's ago';
    const m = Math.floor(s / 60);
    if (m < 60) return m + 'm ago';
    const h = Math.floor(m / 60);
    if (h < 24) return h + 'h ago';
    const d = Math.floor(h / 24);
    if (d < 30) return d + 'd ago';
    const mo = Math.floor(d / 30);
    if (mo < 12) return mo + 'mo ago';
    return Math.floor(mo / 12) + 'y ago';
  } catch (_) {
    return iso || '';
  }
}

const S = {
  page: { minHeight: '100vh', background: '#0d0e10', color: '#e0e0e0', fontFamily: 'system-ui, -apple-system, sans-serif', fontSize: '14px', padding: '0 0 64px' },
  header: { background: '#15161a', borderBottom: '1px solid #2a2b30', padding: '24px 32px 20px' },
  title: { margin: 0, fontSize: '22px', fontWeight: 700, color: '#e0e0e0' },
  sub: { marginTop: '6px', fontSize: '12px', color: '#888' },
  list: { padding: '32px', display: 'flex', flexDirection: 'column', gap: '0' },
  item: { display: 'flex', alignItems: 'flex-start', gap: '16px', padding: '12px 0', borderBottom: '1px solid #1e1f24' },
  sha: { fontFamily: 'monospace', fontSize: '12px', color: '#3a3b50', minWidth: '56px', paddingTop: '2px', userSelect: 'all' },
  subject: { fontWeight: 600, color: '#e0e0e0', flexGrow: 1 },
  meta: { fontSize: '11px', color: '#555', whiteSpace: 'nowrap', paddingTop: '2px' },
  author: { fontSize: '11px', color: '#3a3b50', whiteSpace: 'nowrap', paddingTop: '2px' },
  degraded: { padding: '12px 32px', background: '#2a200a', color: '#f5a623', fontSize: '12px', fontFamily: 'monospace', borderBottom: '1px solid #4a3210' },
};

export default function ChangelogLive() {
  const [commits, setCommits] = useState(null);
  const [degraded, setDegraded] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(CHANGELOG_URL)
      .then((r) => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then((d) => {
        if (!cancelled) {
          setCommits(d.commits || []);
          setDegraded(!!d.degraded);
        }
      })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  return (
    <div style={S.page}>
      <div style={S.header}>
        <h1 style={S.title}>Changelog</h1>
        <div style={S.sub}>Last 50 commits from the repository</div>
      </div>
      {degraded && <div style={S.degraded}>Git unavailable — commit history cannot be loaded in this environment.</div>}
      {error && <div style={{ padding: '40px 32px', color: '#f5a623', fontFamily: 'monospace' }}>Error: {error}</div>}
      {commits !== null && (
        <div style={S.list}>
          {commits.length === 0 && !degraded && <div style={{ color: '#555', fontFamily: 'monospace', fontSize: '12px' }}>No commits found.</div>}
          {commits.map((c) => (
            <div key={c.sha} style={S.item}>
              <span style={S.sha}>{c.sha}</span>
              <span style={S.subject}>{c.subject}</span>
              <span style={S.author}>{c.author}</span>
              <span style={S.meta}>{relativeTime(c.committed_at)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
