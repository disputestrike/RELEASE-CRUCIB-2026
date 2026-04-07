/**
 * Always-on scope disclosure — separate track from goal/plan/timeline.
 * Sticky in the center pane so it stays visible while scrolling; does not block runs.
 */
import React, { useMemo, useState } from 'react';
import { Info, X } from 'lucide-react';
import {
  specGapCopy,
  PIPELINE_INFRA_SCOPE_RISK,
  BEFORE_PRODUCTION_SMTP_NOTE,
} from './planApprovalCopy';
import './RunnerScopeTrack.css';

export default function RunnerScopeTrack({ buildTargetId = 'vite_react', buildTargetMeta = null }) {
  const [isVisible, setIsVisible] = useState(true);
  const copy = useMemo(() => specGapCopy(buildTargetId, buildTargetMeta), [buildTargetId, buildTargetMeta]);

  if (!isVisible) return null;

  return (
    <aside className="rst-root" aria-label="Auto-Runner scope disclosure">
      <div className="rst-header">
        <Info size={14} className="rst-icon" aria-hidden />
        <span className="rst-title">Full pipeline — run never blocked</span>
        <button 
          type="button"
          onClick={() => setIsVisible(false)}
          className="rst-close-btn"
          aria-label="Close"
          title="Close"
        >
          <X size={16} />
        </button>
      </div>
      <p className="rst-p">{copy.runIntro}</p>
      <p className="rst-p rst-target">{copy.targetDetail}</p>
      <div className="rst-subhead">Optional depth &amp; follow-ups</div>
      <p className="rst-p rst-muted">{PIPELINE_INFRA_SCOPE_RISK}</p>
      <div className="rst-subhead">Before production</div>
      <p className="rst-p rst-muted">
        Fix secrets before go-live. For local testing you can run anyway — builds use mocks or placeholders where
        needed. {BEFORE_PRODUCTION_SMTP_NOTE}
      </p>
      <p className="rst-footer" role="note">
        Approve &amp; Run is never blocked by these notes — they describe pipeline scope only.
      </p>
    </aside>
  );
}
