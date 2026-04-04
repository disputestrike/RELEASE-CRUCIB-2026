/**
 * BuildCompletionCard — shown when job.status === 'completed'.
 * Beautiful conclusive summary with quality score, stats, and CTAs.
 * Props: job, summary, proof, onOpenPreview, onOpenProof, onOpenCode, onDeployAgain
 */
import React from 'react';
import { CheckCircle2, Eye, ShieldCheck, Code2, Rocket } from 'lucide-react';
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
  const scoreColor = score >= 80 ? '#6daa45' : score >= 60 ? '#f59e0b' : '#d163a7';

  const stats = summary || {};
  const pages = stats.pages_created || (proof?.bundle?.files?.length ?? 0);
  const routes = stats.api_routes_added || (proof?.bundle?.routes?.length ?? 0);
  const tables = stats.db_tables_created || (proof?.bundle?.database?.length ?? 0);
  const deploys = stats.deploy_targets || (proof?.bundle?.deploy?.length ?? 0);

  return (
    <div className="build-completion-card">
      <div className="bcc-top">
        <CheckCircle2 size={32} className="bcc-check" />
        <div>
          <div className="bcc-title">Build Completed</div>
          <div className="bcc-subtitle">{job?.goal?.slice(0, 80) || 'Your project is ready.'}</div>
        </div>
      </div>

      {/* Stats */}
      <div className="bcc-stats">
        {pages > 0 && (
          <div className="bcc-stat">
            <span className="bcc-stat-num">{pages}</span>
            <span className="bcc-stat-label">{pages === 1 ? 'page' : 'pages'}</span>
          </div>
        )}
        {routes > 0 && (
          <div className="bcc-stat">
            <span className="bcc-stat-num">{routes}</span>
            <span className="bcc-stat-label">API {routes === 1 ? 'route' : 'routes'}</span>
          </div>
        )}
        {tables > 0 && (
          <div className="bcc-stat">
            <span className="bcc-stat-num">{tables}</span>
            <span className="bcc-stat-label">DB {tables === 1 ? 'table' : 'tables'}</span>
          </div>
        )}
        {deploys > 0 && (
          <div className="bcc-stat">
            <span className="bcc-stat-num">{deploys}</span>
            <span className="bcc-stat-label">{deploys === 1 ? 'deploy' : 'deploys'}</span>
          </div>
        )}
      </div>

      {/* Indicators */}
      <div className="bcc-indicators">
        <div className="bcc-indicator">
          <div className="bcc-indicator-label">Quality Score</div>
          <div className="bcc-indicator-val" style={{ color: scoreColor }}>{score}</div>
        </div>
        <div className="bcc-indicator">
          <div className="bcc-indicator-label">Preview</div>
          <div className="bcc-indicator-val bcc-val-ok">Ready</div>
        </div>
        <div className="bcc-indicator">
          <div className="bcc-indicator-label">Proof</div>
          <div className="bcc-indicator-val bcc-val-ok">✓</div>
        </div>
      </div>

      {/* CTAs */}
      <div className="bcc-actions">
        <button className="bcc-btn bcc-btn-preview" onClick={onOpenPreview}>
          <Eye size={13} /> Open Preview
        </button>
        <button className="bcc-btn bcc-btn-proof" onClick={onOpenProof}>
          <ShieldCheck size={13} /> Open Proof
        </button>
        <button className="bcc-btn bcc-btn-code" onClick={onOpenCode}>
          <Code2 size={13} /> Open Code
        </button>
        <button className="bcc-btn bcc-btn-deploy" onClick={onDeployAgain}>
          <Rocket size={13} /> Deploy Again
        </button>
      </div>
    </div>
  );
}
