/**
 * ProofPanel — evidence from GET /api/jobs/:id/proof only (no fabricated scores).
 */
import React, { useState, useCallback, useMemo } from 'react';
import {
  Download,
  FileArchive,
  FileCode2,
  Route,
  Database,
  ShieldCheck,
  Rocket,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { useAuth, API } from '../../App';
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

export default function ProofPanel({ proof, jobId, onExport: _onExport, openWorkspacePath }) {
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState('files');
  const [expandedItems, setExpandedItems] = useState(new Set());
  const [scoreExpanded, setScoreExpanded] = useState(false);
  const [zipBusy, setZipBusy] = useState(false);

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

  const handleDownloadWorkspaceZip = useCallback(async () => {
    if (!jobId || !token || !API) return;
    setZipBusy(true);
    try {
      const res = await fetch(
        `${API}/jobs/${encodeURIComponent(jobId)}/export/full.zip?profile=handoff`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!res.ok) {
        const errText = await res.text().catch(() => '');
        throw new Error(errText || res.statusText || `HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `crucibai-job-${jobId}-handoff.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : 'Download failed');
    } finally {
      setZipBusy(false);
    }
  }, [jobId, token]);

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

  const hasComplianceSketchProof = useMemo(() => {
    const files = proof?.bundle?.files;
    if (!Array.isArray(files)) return false;
    return files.some(
      (row) =>
        row?.payload?.compliance_sketch ||
        row?.payload?.path === 'docs/COMPLIANCE_SKETCH.md',
    );
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
          <span className="pp-score-label">Pipeline quality (proof density)</span>
          <div className="pp-score-bar">
            <div className="pp-score-fill" style={{ width: `${Math.min(score, 100)}%` }} />
          </div>
        </div>
        <div className="pp-proof-count">
          {totalItems} stored items · {verificationItems} verification-class
        </div>
        <div className="pp-header-actions">
          {jobId && token && API ? (
            <button
              type="button"
              className="pp-export-btn"
              onClick={handleDownloadWorkspaceZip}
              disabled={zipBusy}
              title="Download handoff ZIP (app-focused; omits outputs/). Use API ?profile=full for complete tree including outputs/."
            >
              <FileArchive size={12} /> {zipBusy ? 'ZIP…' : 'Workspace ZIP'}
            </button>
          ) : null}
          <button type="button" className="pp-export-btn" onClick={handleExport}>
            <Download size={12} /> Export Proof
          </button>
        </div>
      </div>

      {hasComplianceSketchProof && (
        <div className="pp-compliance-callout" role="status">
          <ShieldCheck size={14} aria-hidden />
          <div>
            <span className="pp-compliance-callout-title">Compliance sketch on disk</span>
            <span className="pp-compliance-callout-desc">
              Proof lists <code className="pp-compliance-code">docs/COMPLIANCE_SKETCH.md</code> — an educational
              checklist tied to your goal. Open the <strong>Files</strong> tab below. Not legal advice.
            </span>
          </div>
        </div>
      )}

      {proof.scorecard && typeof proof.scorecard === 'object' && (
        <div className="pp-honest-scorecard" aria-label="Truthful multi-axis scores">
          <div className="pp-mini-scores">
            <span title="Evidence-weighted trust">
              Trust ~{Number(proof.scorecard.trust_evidence_score ?? proof.trust_score ?? 0).toFixed(0)}
            </span>
            <span title="Stated goal vs what this runner can emit">
              Spec compliance {Number(proof.scorecard.spec_compliance_percent ?? proof.spec_compliance_percent ?? 100).toFixed(0)}%
            </span>
            <span title="Heuristic only — not enterprise certification">
              Prod readiness ~{Number(proof.scorecard.production_readiness_score ?? proof.production_readiness_score ?? 0).toFixed(0)}
            </span>
          </div>
          {proof.scorecard.honest_summary && (
            <p className="pp-honest-summary">{proof.scorecard.honest_summary}</p>
          )}
        </div>
      )}

      {proof.proof_index &&
        typeof proof.proof_index === 'object' &&
        proof.proof_index.by_path &&
        Object.keys(proof.proof_index.by_path).length > 0 && (
          <div className="pp-proof-index" aria-label="Proof rows linked to workspace paths">
            <div className="pp-proof-index-title">Workspace ↔ proof (P5)</div>
            <ul className="pp-proof-index-list">
              {Object.entries(proof.proof_index.by_path)
                .slice(0, 50)
                .map(([path, rows]) => (
                  <li key={path} className="pp-proof-index-row">
                    {openWorkspacePath ? (
                      <button
                        type="button"
                        className="pp-proof-index-path pp-proof-index-path-btn"
                        onClick={() => openWorkspacePath(path)}
                      >
                        {path}
                      </button>
                    ) : (
                      <code className="pp-proof-index-path">{path}</code>
                    )}
                    <span className="pp-proof-index-meta">
                      {Array.isArray(rows) ? rows.length : 0} proof row
                      {Array.isArray(rows) && rows.length === 1 ? '' : 's'}
                    </span>
                  </li>
                ))}
            </ul>
          </div>
        )}

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
                    {item.id &&
                      proof.proof_index?.by_proof_item_id?.[item.id] &&
                      (proof.proof_index.by_proof_item_id[item.id].paths_resolved_in_manifest?.length > 0 ||
                        proof.proof_index.by_proof_item_id[item.id].paths_missing_from_manifest?.length >
                          0) && (
                        <div className="pp-item-file-links" aria-label="Paths linked to this proof row">
                          {(proof.proof_index.by_proof_item_id[item.id].paths_resolved_in_manifest || []).map(
                            (p) =>
                              openWorkspacePath ? (
                                <button
                                  key={`ok-${p}`}
                                  type="button"
                                  className="pp-path-chip pp-path-resolved pp-path-chip-btn"
                                  title="Open in Code"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openWorkspacePath(p);
                                  }}
                                >
                                  {p}
                                </button>
                              ) : (
                                <span key={`ok-${p}`} className="pp-path-chip pp-path-resolved" title="In workspace">
                                  {p}
                                </span>
                              ),
                          )}
                          {(proof.proof_index.by_proof_item_id[item.id].paths_missing_from_manifest || []).map(
                            (p) =>
                              openWorkspacePath ? (
                                <button
                                  key={`miss-${p}`}
                                  type="button"
                                  className="pp-path-chip pp-path-missing pp-path-chip-btn"
                                  title="Open in Code"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openWorkspacePath(p);
                                  }}
                                >
                                  {p}
                                </button>
                              ) : (
                                <span key={`miss-${p}`} className="pp-path-chip pp-path-missing" title="Not in manifest">
                                  {p}
                                </span>
                              ),
                          )}
                        </div>
                      )}
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
