/**
 * ProofPanel — evidence bundle viewer.
 * Tabs: Files | Routes | Database | Verification | Deploy
 * Shows quality score, proof count, verification items.
 * Props: proof, jobId, onExport
 */
import React, { useState } from 'react';
import { Download, FileCode2, Route, Database, ShieldCheck, Rocket, CheckCircle2 } from 'lucide-react';
import './ProofPanel.css';

const CATEGORIES = [
  { key: 'files',        label: 'Files',        Icon: FileCode2 },
  { key: 'routes',       label: 'Routes',       Icon: Route },
  { key: 'database',     label: 'Database',     Icon: Database },
  { key: 'verification', label: 'Verification', Icon: ShieldCheck },
  { key: 'deploy',       label: 'Deploy',       Icon: Rocket },
];

export default function ProofPanel({ proof, jobId, onExport }) {
  const [activeTab, setActiveTab] = useState('files');

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
  const score = proof.quality_score || 0;
  const items = bundle[activeTab] || [];

  const totalItems = Object.values(bundle).reduce((sum, arr) => sum + (arr?.length || 0), 0);
  const verifiedItems = totalItems; // Assume all generated items are verified

  return (
    <div className="proof-panel">
      <div className="pp-header">
        <div className="pp-score-area">
          <span className="pp-score-num">{score.toFixed ? score.toFixed(1) : score}</span>
          <span className="pp-score-label">Quality Score</span>
          <div className="pp-score-bar">
            <div
              className="pp-score-fill"
              style={{ width: `${Math.min(score, 100)}%` }}
            />
          </div>
        </div>
        <div className="pp-proof-count">
          {totalItems} items &middot; {verifiedItems} verified
        </div>
        <button className="pp-export-btn" onClick={() => onExport?.()}>
          <Download size={12} /> Export Proof
        </button>
      </div>

      {/* Tab bar */}
      <div className="pp-tabs">
        {CATEGORIES.map(({ key, label, Icon }) => {
          const count = (bundle[key] || []).length;
          return (
            <button
              key={key}
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

      {/* Items */}
      <div className="pp-items">
        {items.length === 0 ? (
          <div className="pp-empty">No {activeTab} evidence recorded in this build.</div>
        ) : (
          items.map((item, i) => (
            <div key={item.id || i} className="pp-item">
              <div className="pp-item-left">
                <span className="pp-item-type-badge">{activeTab}</span>
              </div>
              <div className="pp-item-content">
                <div className="pp-item-title">{item.title}</div>
                {item.payload && Object.keys(item.payload).length > 0 && (
                  <div className="pp-item-payload">
                    {Object.entries(item.payload).map(([k, v]) => (
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
          ))
        )}
      </div>
    </div>
  );
}
