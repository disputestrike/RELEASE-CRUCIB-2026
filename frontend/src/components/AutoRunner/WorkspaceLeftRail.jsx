import React from 'react';
import { ChevronLeft, ChevronRight, Eye, Rocket, ShieldCheck, FileArchive } from 'lucide-react';
import WorkspaceFileTree from './WorkspaceFileTree';

export default function WorkspaceLeftRail({
  leftCollapsed,
  leftWidth,
  activePane,
  wsPaths,
  activeWsPath,
  treeRevealTick,
  wsListLoading,
  onToggleCollapsed,
  onSelectPane,
  onSelectWorkspacePath,
}) {
  return (
    <aside className={`arp-left-rail ${leftCollapsed ? 'collapsed' : ''}`} style={!leftCollapsed ? { width: `${leftWidth}px` } : undefined}>
      <div className="arp-rail-toggle" onClick={onToggleCollapsed}>
        {leftCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </div>

      <nav className="arp-nav">
        {!leftCollapsed && <div className="arp-nav-section-label">Navigate</div>}
        <button
          type="button"
          className={`arp-nav-item ${activePane === 'preview' ? 'active' : ''}`}
          onClick={() => onSelectPane('preview')}
          title="Preview"
        >
          <Eye size={15} />
          {!leftCollapsed && <span className="arp-nav-label">Preview</span>}
        </button>
        <button
          type="button"
          className={`arp-nav-item ${activePane === 'timeline' ? 'active' : ''}`}
          onClick={() => onSelectPane('timeline')}
          title="Timeline"
        >
          <Rocket size={15} />
          {!leftCollapsed && <span className="arp-nav-label">Timeline</span>}
        </button>
        <button
          type="button"
          className={`arp-nav-item ${activePane === 'proof' ? 'active' : ''}`}
          onClick={() => onSelectPane('proof')}
          title="Proof"
        >
          <ShieldCheck size={15} />
          {!leftCollapsed && <span className="arp-nav-label">Proof</span>}
        </button>
        <button
          type="button"
          className={`arp-nav-item ${activePane === 'code' ? 'active' : ''}`}
          onClick={() => onSelectPane('code')}
          title="Code + Files"
        >
          <FileArchive size={15} />
          {!leftCollapsed && <span className="arp-nav-label">Code</span>}
        </button>

        {!leftCollapsed && <div className="arp-nav-section-label arp-nav-section-label-system">Workspace Files</div>}
        {!leftCollapsed && (
          <div className="uw-left-tree-wrap">
            <WorkspaceFileTree
              paths={wsPaths}
              selectedPath={activeWsPath}
              onSelectPath={onSelectWorkspacePath}
              revealTick={treeRevealTick}
              loading={wsListLoading}
            />
          </div>
        )}
      </nav>
    </aside>
  );
}
