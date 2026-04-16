/**
 * Workspace actions fused into the app Sidebar (workspace route only).
 * Recent builds stay in the main History list — this block is actions only (no duplicate list).
 */
import React from 'react';

export default function WorkspaceFusedRail({
  onNewTask,
  workflows,
  workflowsOpen,
  onToggleWorkflows,
  workflowLoading,
  onRunWorkflow,
}) {
  return (
    <div className="sidebar-workspace-fuse-inner">
      <button type="button" className="sidebar-workspace-fuse-primary" onClick={onNewTask}>
        + New task
      </button>
      <div className="sidebar-workspace-fuse-workflows">
        <button type="button" className="sidebar-workspace-fuse-wf-toggle" onClick={onToggleWorkflows}>
          Workflows {workflowsOpen ? '▾' : '▸'}
        </button>
        {workflowsOpen && (
          <div className="sidebar-workspace-fuse-wf-scroll">
            {Object.entries(workflows || {}).map(([category, wfList]) => (
              <div key={category}>
                <div className="sidebar-workspace-fuse-wf-cat">{category}</div>
                {(wfList || []).map((wf) => (
                  <button
                    key={wf.key}
                    type="button"
                    className="sidebar-workspace-fuse-wf-item"
                    disabled={!!workflowLoading}
                    title={wf.description ? String(wf.description) : undefined}
                    onClick={() => onRunWorkflow(wf.key)}
                  >
                    {wf.name}
                  </button>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
