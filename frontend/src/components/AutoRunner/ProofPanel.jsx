/**
 * ProofPanel — shows evidence bundle: files, routes, DB, verification, deploy.
 * Props: proof, jobId, onExport
 */
import React, { useState } from 'react';
import { Download, FileCode2, Route, Database, ShieldCheck, Rocket } from 'lucide-react';
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
        <span>Proof will appear here as steps complete.</span>
      </div>
    );
  }

  const bundle = proof.bundle || {};
  const score = proof.quality_score || 0;
  const items = bundle[activeTab] || [];

  const scoreColor = score >= 80 ? '#6daa45' : score >= 60 ? '#f59e0b' : '#d163a7';

  return (
    <div className="proof-panel">
      <div className="pp-header">
        <span className="pp-title">Proof</span>
        <div className="pp-score" style={{ color: scoreColor }}>
          Quality Score: <strong>{score}</strong>
        </div>
        <button className="pp-export-btn" onClick={() => onExport?.()}>
          <Download size={12} /> Export
        </button>
      </div>

      {/* Category tabs */}
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
          <div className="pp-empty">No {activeTab} evidence yet.</div>
        ) : (
          items.map((item, i) => (
            <div key={item.id || i} className="pp-item">
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
          ))
        )}
      </div>
    </div>
  );
}
