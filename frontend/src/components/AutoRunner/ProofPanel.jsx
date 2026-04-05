/**
 * ProofPanel — evidence from GET /api/jobs/:id/proof only (no fabricated scores).
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Download, FileCode2, Route, Database, ShieldCheck, Rocket, CheckCircle2, ChevronDown, ChevronRight } from 'lucide-react';
import './ProofPanel.css';

const CATEGORIES = [
  { key: 'files', label: 'Files', Icon: FileCode2 },
  { key: 'routes', label: 'Routes', Icon: Route },
  { key: 'database', label: 'Database', Icon: Database },
  { key: 'verification', label: 'Verification', Icon: ShieldCheck },
  { key: 'deploy', label: 'Deploy', Icon: Rocket },
];

const CATEGORY_LABELS = {
  files: 'Files',
  routes: 'Routes',
  database: 'Database',
  verification: 'Verification',
  deploy: 'Deploy',
  generic: 'Other',
};

function payloadSummary(payload) {
  if (!payload || typeof payload !== 'object') return null;
  try {
    return JSON.stringify(payload, null, 2);
  } catch {
    return String(payload);
  }
}

export default function ProofPanel({ proof, jobId, onExport }) {
  const [activeTab, setActiveTab] = useState('files');
  const [expandedItems, setExpandedItems] = useState(new Set());
  const [scoreExpanded, setScoreExpanded] = useState(false);

  const handleExport = useCallback(() => {
    if (!proof) return;
    const blob = new Blob([JSON.stringify(proof, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `crucibai-proof-${jobId || 'bundle'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [proof, jobId]);

  const toggleItem = (idx) => {
    setExpandedItems((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const breakdownRows = useMemo(() => {
    const counts = proof?.category_counts;
    if (!counts || typeof counts !== 'object') return [];
    return Object.entries(counts)
      .filter(([, n]) => n > 0)
      .map(([key, n]) => ({ key, label: CATEGORY_LABELS[key] || key, count: n }));
  }, [proof]);

  if (!proof) {
    return (
      <div className="proof-panel proof-empty">
        <ShieldCheck size={24} />
        <span className="proof-empty-title">No proof items yet</span>
        <span className="proof-empty-desc">Run a job to generate verifiable evidence.</span>
      </div>
    );
  }

  const bundle = proof.bundle || {};
  const score = typeof proof.quality_score === 'number' ? proof.quality_score : 0;
  const items = bundle[activeTab] || [];
  const totalItems =
    typeof proof.total_proof_items === 'number'
      ? proof.total_proof_items
      : Object.values(bundle).reduce((sum, arr) => sum + (arr?.length || 0), 0);
  const verificationItems =
    typeof proof.verification_proof_items === 'number'
      ? proof.verification_proof_items
      : (bundle.verification || []).length;

  return (
    <div className="proof-panel">
      {proof.proofFetchFailed && (
        <p className="pp-breakdown-empty" role="alert" style={{ margin: '0 0 12px' }}>
          Could not load proof from the server (offline, wrong API URL, or error). Fix the connection, then reload this page.
        </p>
      )}
      {totalItems === 0 && !proof.proofFetchFailed && (
        <p className="pp-breakdown-empty" style={{ margin: '0 0 12px' }}>
          Proof is written after each step passes verification. Zeros usually mean the run never executed steps (check <strong>Timeline</strong> / <strong>Failure</strong> for errors), or the job has no DAG steps — use <strong>Plan</strong> then <strong>Approve &amp; Run</strong> again. Restart the <strong>backend</strong> after backend code changes.
        </p>
      )}
      <div className="pp-header">
        <div className="pp-score-area">
          <span className="pp-score-num">{score.toFixed(1)}</span>
          <span className="pp-score-label">Quality Score</span>
          <div className="pp-score-bar">
            <div className="pp-score-fill" style={{ width: `${Math.min(score, 100)}%` }} />
          </div>
        </div>
        <div className="pp-proof-count">
          {totalItems} stored items · {verificationItems} verification-class
        </div>
        <button type="button" className="pp-export-btn" onClick={handleExport}>
          <Download size={12} /> Export Proof
        </button>
      </div>

      <div className="pp-score-breakdown">
        <button type="button" className="pp-score-toggle" onClick={() => setScoreExpanded(!scoreExpanded)}>
          {scoreExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          <span>Score breakdown (from stored proof rows)</span>
        </button>
        {scoreExpanded && (
          <div className="pp-score-factors">
            {totalItems === 0 ? (
              <p className="pp-breakdown-empty">No proof rows yet — score stays at 0 until the job stores evidence.</p>
            ) : (
              <>
                {breakdownRows.map((row) => (
                  <div key={row.key} className="pp-factor-row pp-factor-row-real">
                    <span className="pp-factor-check">
                      <CheckCircle2 size={10} />
                    </span>
                    <span className="pp-factor-name">{row.label}</span>
                    <span className="pp-factor-score">{row.count} items</span>
                  </div>
                ))}
                <p className="pp-reach-100 pp-reach-muted">
                  Score is computed on the server from verification-class proof types vs total items (see proof_service).
                </p>
              </>
            )}
          </div>
        )}
      </div>

      <div className="pp-tabs">
        {CATEGORIES.map(({ key, label, Icon }) => {
          const count = (bundle[key] || []).length;
          return (
            <button
              key={key}
              type="button"
              className={`pp-tab ${activeTab === key ? 'active' : ''}`}
              onClick={() => setActiveTab(key)}
            >
              <Icon size={11} />
              {label}
              {count > 0 && <span className="pp-tab-count">{count}</span>}
            </button>
          );
        })}
      </div>

      <div className="pp-items">
        {items.length === 0 ? (
          <div className="pp-empty">No {activeTab} evidence recorded in this build.</div>
        ) : (
          items.map((item, i) => {
            const isExpanded = expandedItems.has(i);
            const body = payloadSummary(item.payload);
            return (
              <div key={item.id || i} className={`pp-item ${isExpanded ? 'pp-item-expanded' : ''}`}>
                <div
                  role="button"
                  tabIndex={0}
                  className="pp-item-row"
                  onClick={() => toggleItem(i)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      toggleItem(i);
                    }
                  }}
                >
                  <button type="button" className="pp-item-chevron" aria-hidden tabIndex={-1}>
                    {isExpanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
                  </button>
                  <div className="pp-item-left">
                    <span className="pp-item-type-badge">{item.type || activeTab}</span>
                  </div>
                  <div className="pp-item-content">
                    <div className="pp-item-title">{item.title}</div>
                    {item.created_at && <div className="pp-item-meta">{item.created_at}</div>}
                    {!isExpanded && item.payload && Object.keys(item.payload).length > 0 && (
                      <div className="pp-item-payload">
                        {Object.entries(item.payload).slice(0, 4).map(([k, v]) => (
                          <span key={k} className="pp-item-kv">
                            <span className="pp-kv-key">{k}:</span>
                            <span className="pp-kv-val">{String(v)}</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <CheckCircle2 size={14} className="pp-verified-icon" />
                </div>
                {isExpanded && body && (
                  <div className="pp-expanded-content">
                    <pre className="pp-expanded-mono">{body}</pre>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
