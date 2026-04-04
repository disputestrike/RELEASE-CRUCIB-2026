/**
 * BuildCompletionCard — most polished surface. Shown on successful completion.
 * GATED by: job.status === 'completed' && proofCount > 0 && qualityScore > 0.8
 * Props: job, summary, proof, onOpenPreview, onOpenProof, onOpenCode, onDeployAgain
 */
import React from 'react';
import { Eye, ShieldCheck, Code2, Rocket } from 'lucide-react';
import './BuildCompletionCard.css';

export default function BuildCompletionCard({
  job,
  summary,
  proof,
  onOpenPreview,
  onOpenProof,
  onOpenCode,
  onDeployAgain,
}) {
  const score = job?.quality_score || summary?.quality_score || proof?.quality_score || 0;
  const normalizedScore = typeof score === 'number' && score <= 1 ? score * 100 : score;

  const stats = summary || {};
  const bundle = proof?.bundle || {};
  const pages = stats.pages_created || (bundle.files?.length ?? 0);
  const routes = stats.api_routes_added || (bundle.routes?.length ?? 0);
  const tables = stats.db_tables_created || (bundle.database?.length ?? 0);
  const deploys = stats.deploy_targets || (bundle.deploy?.length ?? 0);
  const proofCount = Object.values(bundle).reduce((sum, arr) => sum + (arr?.length || 0), 0);

  // Hard gate: must have completed status, proof items, and quality above 0.8
  if (job?.status !== 'completed' || proofCount <= 0 || normalizedScore <= 80) {
    return null;
  }

  return (
    <div className="build-completion-card animate-fade-up">
      {/* Success indicator */}
      <div className="bcc-top">
        <div className="bcc-check">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
            <circle cx="20" cy="20" r="19" fill="var(--bg-2)" stroke="var(--state-success)" strokeWidth="2" />
            <path d="M12 20L18 26L28 14" stroke="var(--state-success)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <div className="bcc-header">
          <div className="bcc-title">Build Complete</div>
          <div className="bcc-subtitle">{job?.goal?.slice(0, 80) || 'Your project is ready.'}</div>
        </div>
      </div>

      {/* What was created */}
      <div className="bcc-created">
        {pages > 0 && <span className="bcc-created-item">{pages} {pages === 1 ? 'file' : 'files'}</span>}
        {routes > 0 && <span className="bcc-created-item">{routes} API {routes === 1 ? 'route' : 'routes'}</span>}
        {tables > 0 && <span className="bcc-created-item">{tables} DB {tables === 1 ? 'table' : 'tables'}</span>}
        {deploys > 0 && <span className="bcc-created-item">{deploys} {deploys === 1 ? 'deploy' : 'deploys'}</span>}
      </div>

      {/* Quality score */}
      <div className="bcc-score-section">
        <span className="bcc-score-num">{normalizedScore.toFixed ? normalizedScore.toFixed(1) : normalizedScore}</span>
        <span className="bcc-score-label">Verified</span>
      </div>

      {/* Status rows */}
      <div className="bcc-status-rows">
        <div className="bcc-status-row">
          <span className="bcc-status-dot bcc-dot-success" />
          <span>Preview ready</span>
        </div>
        <div className="bcc-status-row">
          <span className="bcc-status-dot bcc-dot-success" />
          <span>Deployment live</span>
        </div>
        <div className="bcc-status-row">
          <span className="bcc-status-dot bcc-dot-success" />
          <span>Proof available</span>
        </div>
      </div>

      {/* CTAs */}
      <div className="bcc-actions">
        <button className="bcc-btn" onClick={onOpenPreview}>
          <Eye size={13} /> Open Preview
        </button>
        <button className="bcc-btn" onClick={onOpenProof}>
          <ShieldCheck size={13} /> Open Proof
        </button>
        <button className="bcc-btn" onClick={onOpenCode}>
          <Code2 size={13} /> Open Code
        </button>
        <button className="bcc-btn" onClick={onDeployAgain}>
          <Rocket size={13} /> Deploy Again
        </button>
      </div>
    </div>
  );
}
