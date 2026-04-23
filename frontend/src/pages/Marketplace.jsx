/**
 * Marketplace.jsx — Wave 5: Growth & Ecosystem
 *
 * Displays community marketplace listings from /api/marketplace/listings.
 * Supports kind filters (plugin / skill / template / mcp) and install modal.
 */

import { useEffect, useState } from 'react';

const KINDS = ['all', 'plugin', 'skill', 'template', 'mcp'];

const STYLES = {
  page: {
    background: '#0f1117',
    minHeight: '100vh',
    color: '#e2e8f0',
    fontFamily: 'system-ui, sans-serif',
    padding: '32px',
  },
  header: {
    marginBottom: '24px',
  },
  title: {
    fontSize: '28px',
    fontWeight: 700,
    color: '#f8fafc',
    margin: 0,
  },
  subtitle: {
    color: '#94a3b8',
    marginTop: '6px',
    fontSize: '14px',
  },
  filterRow: {
    display: 'flex',
    gap: '8px',
    marginBottom: '24px',
    flexWrap: 'wrap',
  },
  chip: (active) => ({
    padding: '6px 16px',
    borderRadius: '999px',
    border: active ? '1px solid #6366f1' : '1px solid #334155',
    background: active ? '#6366f1' : 'transparent',
    color: active ? '#fff' : '#94a3b8',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 500,
    transition: 'all 0.15s',
  }),
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '16px',
  },
  card: {
    background: '#1e2435',
    border: '1px solid #2d3748',
    borderRadius: '12px',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  cardTitle: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#f1f5f9',
    margin: 0,
  },
  cardDesc: {
    fontSize: '13px',
    color: '#94a3b8',
    margin: 0,
    lineHeight: 1.5,
  },
  tagRow: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap',
  },
  tag: {
    background: '#2d3748',
    color: '#a5b4fc',
    fontSize: '11px',
    borderRadius: '4px',
    padding: '2px 8px',
  },
  kindBadge: (kind) => {
    const colors = {
      plugin: '#0ea5e9',
      skill: '#10b981',
      mcp: '#f59e0b',
      template: '#6366f1',
    };
    return {
      background: (colors[kind] || '#6366f1') + '22',
      color: colors[kind] || '#6366f1',
      border: `1px solid ${colors[kind] || '#6366f1'}44`,
      fontSize: '11px',
      borderRadius: '4px',
      padding: '2px 8px',
      fontWeight: 600,
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
    };
  },
  scoreRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '12px',
    color: '#64748b',
  },
  scoreBar: (score) => ({
    height: '4px',
    width: '60px',
    background: '#2d3748',
    borderRadius: '2px',
    overflow: 'hidden',
  }),
  scoreBarFill: (score) => ({
    height: '100%',
    width: `${score}%`,
    background: score >= 90 ? '#10b981' : score >= 70 ? '#f59e0b' : '#ef4444',
    borderRadius: '2px',
  }),
  installBtn: {
    marginTop: 'auto',
    padding: '8px 16px',
    background: '#6366f1',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 600,
  },
  emptyState: {
    textAlign: 'center',
    color: '#64748b',
    padding: '60px 0',
    fontSize: '14px',
  },
  modal: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.7)',
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
    width: '480px',
    maxWidth: '90vw',
  },
  modalTitle: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#f1f5f9',
    margin: '0 0 16px',
  },
  codeBlock: {
    background: '#0f1117',
    border: '1px solid #2d3748',
    borderRadius: '8px',
    padding: '12px 16px',
    fontFamily: 'monospace',
    fontSize: '13px',
    color: '#a5b4fc',
    wordBreak: 'break-all',
    margin: '8px 0',
  },
  modalClose: {
    marginTop: '20px',
    padding: '8px 20px',
    background: 'transparent',
    border: '1px solid #334155',
    color: '#94a3b8',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px',
  },
};

export default function Marketplace() {
  const [listings, setListings] = useState([]);
  const [degraded, setDegraded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [activeKind, setActiveKind] = useState('all');
  const [modal, setModal] = useState(null); // { listing, installMeta }
  const [installLoading, setInstallLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch('/api/marketplace/listings')
      .then((r) => r.json())
      .then((data) => {
        setListings(data.listings || []);
        setDegraded(!!data.degraded);
      })
      .catch(() => setDegraded(true))
      .finally(() => setLoading(false));
  }, []);

  const filtered =
    activeKind === 'all' ? listings : listings.filter((l) => l.kind === activeKind);

  async function handleInstall(listing) {
    setInstallLoading(true);
    try {
      const r = await fetch(`/api/marketplace/listings/${listing.id}/install`, {
        method: 'POST',
      });
      const meta = await r.json();
      setModal({ listing, installMeta: meta });
    } catch {
      setModal({ listing, installMeta: null });
    } finally {
      setInstallLoading(false);
    }
  }

  return (
    <div style={STYLES.page}>
      <div style={STYLES.header}>
        <h1 style={STYLES.title}>Marketplace</h1>
        <p style={STYLES.subtitle}>
          Discover and install community plugins, skills, templates, and MCPs.
          {degraded && ' (running in degraded mode — DB unavailable)'}
        </p>
      </div>

      <div style={STYLES.filterRow}>
        {KINDS.map((k) => (
          <button
            key={k}
            style={STYLES.chip(activeKind === k)}
            onClick={() => setActiveKind(k)}
          >
            {k.charAt(0).toUpperCase() + k.slice(1)}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={STYLES.emptyState}>Loading listings…</div>
      ) : filtered.length === 0 ? (
        <div style={STYLES.emptyState}>
          No listings found{activeKind !== 'all' ? ` for kind: ${activeKind}` : ''}.
        </div>
      ) : (
        <div style={STYLES.grid}>
          {filtered.map((listing) => (
            <div key={listing.id} style={STYLES.card}>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={STYLES.kindBadge(listing.kind)}>{listing.kind}</span>
              </div>
              <h3 style={STYLES.cardTitle}>{listing.title}</h3>
              {listing.description && (
                <p style={STYLES.cardDesc}>{listing.description}</p>
              )}
              {listing.tags?.length > 0 && (
                <div style={STYLES.tagRow}>
                  {listing.tags.map((t) => (
                    <span key={t} style={STYLES.tag}>{t}</span>
                  ))}
                </div>
              )}
              <div style={STYLES.scoreRow}>
                <span>Proof</span>
                <div style={STYLES.scoreBar(listing.proof_score)}>
                  <div style={STYLES.scoreBarFill(listing.proof_score)} />
                </div>
                <span>{Math.round(listing.proof_score)}%</span>
                <span style={{ marginLeft: 'auto' }}>
                  {listing.install_count} installs
                </span>
              </div>
              <button
                style={STYLES.installBtn}
                onClick={() => handleInstall(listing)}
                disabled={installLoading}
              >
                Install
              </button>
            </div>
          ))}
        </div>
      )}

      {modal && (
        <div style={STYLES.modal} onClick={() => setModal(null)}>
          <div style={STYLES.modalBox} onClick={(e) => e.stopPropagation()}>
            <h2 style={STYLES.modalTitle}>
              Install: {modal.listing.title}
            </h2>
            {modal.installMeta ? (
              <>
                <p style={{ color: '#94a3b8', fontSize: '13px', margin: '0 0 8px' }}>
                  Type: <strong style={{ color: '#e2e8f0' }}>{modal.installMeta.type}</strong>
                </p>
                <p style={{ color: '#94a3b8', fontSize: '13px', margin: '0 0 4px' }}>
                  Install command:
                </p>
                <div style={STYLES.codeBlock}>{modal.installMeta.install_cmd}</div>
                <p style={{ color: '#94a3b8', fontSize: '13px', margin: '8px 0 4px' }}>
                  Docs:{' '}
                  <a
                    href={modal.installMeta.docs_url}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: '#a5b4fc' }}
                  >
                    {modal.installMeta.docs_url}
                  </a>
                </p>
              </>
            ) : (
              <p style={{ color: '#ef4444', fontSize: '13px' }}>
                Failed to load install info.
              </p>
            )}
            <button style={STYLES.modalClose} onClick={() => setModal(null)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
