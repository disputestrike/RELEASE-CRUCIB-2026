import React from 'react';
import { Eye, ShieldCheck, FolderTree, History, AlertTriangle, FileCode2, Rocket, Share2 } from 'lucide-react';

const ICONS = {
  preview: Eye,
  proof: ShieldCheck,
  explorer: FolderTree,
  replay: History,
  failure: AlertTriangle,
  timeline: History,
  code: FileCode2,
};

export default function WorkspaceWorkSurface({
  activePane,
  setActivePane,
  visibleRightPanes,
  uxMode,
  toggleUxMode,
  title,
  subtitle,
  children,
  onShare,
  onFocusPreview,
}) {
  return (
    <div className="wsv4-surface">
      <div className="wsv4-surface-toolbar">
        <div className="wsv4-surface-titleblock">
          <div className="wsv4-surface-eyebrow">Live work surface</div>
          <div className="wsv4-surface-title">{title}</div>
          {subtitle ? <div className="wsv4-surface-subtitle">{subtitle}</div> : null}
        </div>
        <div className="wsv4-surface-actions">
          <button type="button" className="wsv4-icon-btn" title="Preview" onClick={onFocusPreview}><Rocket size={15} /></button>
          <button type="button" className="wsv4-icon-btn" title="Share" onClick={onShare}><Share2 size={15} /></button>
          <div className="wsv4-mode-switch">
            <button type="button" className={uxMode === 'beginner' ? 'active' : ''} onClick={() => toggleUxMode('beginner')}>Simple</button>
            <button type="button" className={uxMode === 'pro' ? 'active' : ''} onClick={() => toggleUxMode('pro')}>Dev</button>
          </div>
        </div>
      </div>
      <div className="wsv4-tab-row">
        {visibleRightPanes.map((pane) => {
          const Icon = ICONS[pane] || FileCode2;
          return (
            <button key={pane} type="button" className={`wsv4-tab ${activePane === pane ? 'active' : ''}`} onClick={() => setActivePane(pane)}>
              <Icon size={14} />
              <span>{pane.charAt(0).toUpperCase() + pane.slice(1)}</span>
            </button>
          );
        })}
      </div>
      <div className="wsv4-surface-body">{children}</div>
    </div>
  );
}
