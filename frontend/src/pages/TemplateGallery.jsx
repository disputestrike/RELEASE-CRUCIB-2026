/**
 * TemplateGallery.jsx — Wave 5: Growth & Ecosystem
 *
 * Full-screen gallery of marketplace listings filtered to kind=template.
 * Larger preview cards with prompt excerpt and proof score visualization.
 */

import { useEffect, useState } from 'react';

const STYLES = {
  page: {
    background: '#0f1117',
    minHeight: '100vh',
    color: '#e2e8f0',
    fontFamily: 'system-ui, sans-serif',
    padding: '32px',
  },
  header: { marginBottom: '32px' },
  title: { fontSize: '28px', fontWeight: 700, color: '#f8fafc', margin: 0 },
  subtitle: { color: '#94a3b8', marginTop: '6px', fontSize: '14px' },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
    gap: '20px',
  },
  card: {
    background: '#1e2435',
    border: '1px solid #2d3748',
    borderRadius: '16px',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
  previewBanner: (url) => ({
    height: '160px',
    background: url
      ? `url(${url}) center/cover no-repeat`
      : 'linear-gradient(135deg, #1e293b 0%, #312e81 100%)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#64748b',
    fontSize: '13px',
    position: 'relative',
  }),
  cardBody: { padding: '20px', display: 'flex', flexDirection: 'column', gap: '10px', flex: 1 },
  cardTitle: { fontSize: '18px', fontWeight: 700, color: '#f1f5f9', margin: 0 },
  cardDesc: { fontSize: '13px', color: '#94a3b8', margin: 0, lineHeight: 1.6 },
  promptBox: {
    background: '#0f1117',
    border: '1px solid #2d3748',
    borderRadius: '8px',
    padding: '10px 14px',
    fontFamily: 'monospace',
    fontSize: '12px',
    color: '#a5b4fc',
    lineHeight: 1.5,
    maxHeight: '72px',
    overflow: 'hidden',
  },
  tagRow: { display: 'flex', gap: '6px', flexWrap: 'wrap' },
  tag: {
    background: '#2d3748',
    color: '#cbd5e1',
    fontSize: '11px',
    borderRadius: '4px',
    padding: '2px 8px',
  },
  metaRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    fontSize: '12px',
    color: '#64748b',
    marginTop: 'auto',
  },
  scoreChip: (score) => ({
    padding: '2px 10px',
    borderRadius: '999px',
    background: score >= 90 ? '#10b98122' : score >= 70 ? '#f59e0b22' : '#ef444422',
    color: score >= 90 ? '#10b981' : score >= 70 ? '#f59e0b' : '#ef4444',
    fontSize: '12px',
    fontWeight: 600,
  }),
  useBtn: {
    padding: '10px 20px',
    background: '#6366f1',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
    marginTop: '4px',
  },
  emptyState: {
    textAlign: 'center',
    color: '#64748b',
    padding: '80px 0',
    fontSize: '15px',
  },
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
    width: '500px',
    maxWidth: '92vw',
  },
  modalTitle: { fontSize: '20px', fontWeight: 700, color: '#f1f5f9', margin: '0 0 12px' },
  codeBlock: {
    background: '#0f1117',
    border: '1px solid #2d3748',
    borderRadius: '8px',
    padding: '12px 16px',
    fontFamily: 'monospace',
    fontSize: '13px',
    color: '#a5b4fc',
    wordBreak: 'break-all',
  },
  btnRow: { display: 'flex', gap: '10px', marginTop: '20px' },
  closeBtn: {
    padding: '8px 20px',
    background: 'transparent',
    border: '1px solid #334155',
    color: '#94a3b8',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px',
  },
};

export default function TemplateGallery() {
  const [templates, setTemplates] = useState([]);
  const [degraded, setDegraded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);

  useEffect(() => {
    fetch('/api/marketplace/listings?kind=template')
      .then((r) => r.json())
      .then((data) => {
        setTemplates(data.listings || []);
        setDegraded(!!data.degraded);
      })
      .catch(() => setDegraded(true))
      .finally(() => setLoading(false));
  }, []);

  async function handleUse(tpl) {
    try {
      const r = await fetch(`/api/marketplace/listings/${tpl.id}/install`, { method: 'POST' });
      const meta = await r.json();
      setModal({ tpl, meta });
    } catch {
      setModal({ tpl, meta: null });
    }
  }

  return (
    <div style={STYLES.page}>
      <div style={STYLES.header}>
        <h1 style={STYLES.title}>Template Gallery</h1>
        <p style={STYLES.subtitle}>
          Proof-verified starter templates ready to remix.
          {degraded && ' (degraded — DB unavailable)'}
        </p>
      </div>

      {loading ? (
        <div style={STYLES.emptyState}>Loading templates…</div>
      ) : templates.length === 0 ? (
        <div style={STYLES.emptyState}>No templates published yet.</div>
      ) : (
        <div style={STYLES.grid}>
          {templates.map((tpl) => (
            <div key={tpl.id} style={STYLES.card}>
              <div style={STYLES.previewBanner(tpl.preview_url)}>
                {!tpl.preview_url && <span>No preview</span>}
              </div>
              <div style={STYLES.cardBody}>
                <h3 style={STYLES.cardTitle}>{tpl.title}</h3>
                {tpl.description && <p style={STYLES.cardDesc}>{tpl.description}</p>}
                {tpl.tags?.length > 0 && (
                  <div style={STYLES.tagRow}>
                    {tpl.tags.map((t) => <span key={t} style={STYLES.tag}>{t}</span>)}
                  </div>
                )}
                <div style={STYLES.metaRow}>
                  <span style={STYLES.scoreChip(tpl.proof_score)}>
                    Proof {Math.round(tpl.proof_score)}%
                  </span>
                  <span>{tpl.install_count ?? 0} uses</span>
                </div>
                <button style={STYLES.useBtn} onClick={() => handleUse(tpl)}>
                  Use Template
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {modal && (
        <div style={STYLES.modal} onClick={() => setModal(null)}>
          <div style={STYLES.modalBox} onClick={(e) => e.stopPropagation()}>
            <h2 style={STYLES.modalTitle}>{modal.tpl.title}</h2>
            {modal.meta ? (
              <>
                <p style={{ color: '#94a3b8', fontSize: '13px', margin: '0 0 8px' }}>
                  Clone this template with:
                </p>
                <div style={STYLES.codeBlock}>{modal.meta.install_cmd}</div>
                <p style={{ color: '#94a3b8', fontSize: '12px', marginTop: '10px' }}>
                  Docs:{' '}
                  <a href={modal.meta.docs_url} target="_blank" rel="noreferrer"
                    style={{ color: '#a5b4fc' }}>
                    {modal.meta.docs_url}
                  </a>
                </p>
              </>
            ) : (
              <p style={{ color: '#ef4444', fontSize: '13px' }}>Failed to load install info.</p>
            )}
            <div style={STYLES.btnRow}>
              <button style={STYLES.closeBtn} onClick={() => setModal(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
