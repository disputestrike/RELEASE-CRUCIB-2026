import React from 'react';
import axios from 'axios';
import {
  Box,
  Braces,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Code2,
  Eye,
  FileArchive,
  Files,
  GitBranch,
  PanelRightClose,
  PanelRightOpen,
  RefreshCw,
  ShieldCheck,
  SquareTerminal,
  Wrench,
} from 'lucide-react';
import Logo from '../Logo';
import GoalComposer from '../AutoRunner/GoalComposer';
import BrainGuidancePanel from '../AutoRunner/BrainGuidancePanel';
import BuildReplay from '../AutoRunner/BuildReplay';
import ExecutionTimeline from '../AutoRunner/ExecutionTimeline';
import FailureDrawer from '../AutoRunner/FailureDrawer';
import PreviewPanel from '../AutoRunner/PreviewPanel';
import ProofPanel from '../AutoRunner/ProofPanel';
import ResizableDivider from '../AutoRunner/ResizableDivider';
import SystemExplorer from '../AutoRunner/SystemExplorer';
import SystemStatusHUD from '../AutoRunner/SystemStatusHUD';
import WorkspaceFileTree from '../AutoRunner/WorkspaceFileTree';
import WorkspaceFileViewer from '../AutoRunner/WorkspaceFileViewer';
import WorkspaceLiveControl from '../AutoRunner/WorkspaceLiveControl';
import WorkspaceSystemsPanel from '../AutoRunner/WorkspaceSystemsPanel';
import EnhancedProofPanel from '../Proof/EnhancedProofPanel';
import './ClaudeCodeWorkspace.css';

const PANE_LABELS = {
  preview: 'Preview',
  live: 'Runtime',
  proof: 'Proof',
  systems: 'System',
  explorer: 'Files',
  replay: 'Replay',
  failure: 'Issues',
  timeline: 'Events',
  code: 'Code',
};

const PANE_ICONS = {
  preview: Eye,
  live: SquareTerminal,
  proof: ShieldCheck,
  systems: Wrench,
  explorer: Files,
  replay: GitBranch,
  failure: Wrench,
  timeline: Braces,
  code: Code2,
};

function jobStateLabel({ job, stage, loading }) {
  const status = String(job?.status || '').toLowerCase();
  if (loading || status === 'running' || status === 'queued') return 'working';
  if (status === 'completed' || status === 'success' || status === 'done') return 'ready';
  if (status === 'failed' || status === 'blocked') return 'needs attention';
  if (stage === 'running') return 'working';
  return 'ready';
}

function statusClass(label) {
  if (label === 'ready') return 'ccw-state--ready';
  if (label === 'needs attention') return 'ccw-state--attention';
  return 'ccw-state--working';
}

function compactCount(value) {
  const n = Number(value || 0);
  if (!Number.isFinite(n) || n <= 0) return '0';
  if (n > 999) return `${Math.round(n / 100) / 10}k`;
  return String(n);
}

function PaneButton({ pane, active, onClick }) {
  const Icon = PANE_ICONS[pane] || Box;
  return (
    <button type="button" className={`ccw-pane-tab${active ? ' is-active' : ''}`} onClick={onClick}>
      <Icon size={15} />
      <span>{PANE_LABELS[pane] || pane}</span>
    </button>
  );
}

export default function ClaudeCodeWorkspace({
  uxMode,
  toggleUxMode,
  loading,
  job,
  stage,
  currentActivity,
  userChatMessages,
  effectiveJobId,
  effectiveProjectId,
  sessionTaskId,
  taskIdFromUrl,
  goal,
  setGoal,
  handleSend,
  handleCancel,
  authLoading,
  buildTarget,
  setBuildTarget,
  buildTargets,
  buildTargetMeta,
  handlePause,
  handleResume,
  reloadWorkspaceFromServer,
  rightCollapsed,
  setRightCollapsed,
  rightWidth,
  handleResize,
  handleResetWidth,
  visibleRightPanes,
  activePane,
  setActivePane,
  rightRailSubtitle,
  handleShare,
  connectionMode,
  isConnected,
  activeAgentCount,
  healthMs,
  events,
  steps,
  proof,
  proofItemCount,
  previewUrl,
  previewStatus,
  sandpackFiles,
  sandpackDeps,
  filesReadyKey,
  sandpackIsFallback,
  previewBlockedDetail,
  latestFailure,
  failureStep,
  setFailedStep,
  handleRetryStep,
  jumpStepToCode,
  token,
  apiBase,
  openWorkspacePath,
  milestoneBatch,
  repairQueueLen,
  refresh,
  wsPaths,
  activeWsPath,
  setActiveWsPath,
  treeRevealTick,
  setTreeRevealTick,
  wsListLoading,
  wsFileCache,
  traceByPath,
  editorColorMode,
  handleCodeChange,
  zipBusy,
  handleDownloadWorkspaceZip,
  navigate,
}) {
  const stateLabel = jobStateLabel({ job, stage, loading });
  const filteredUserMessages = (userChatMessages || []).filter(
    (m) => !m.jobId || !effectiveJobId || m.jobId === effectiveJobId,
  );
  const hasSandpack = Boolean(sandpackFiles && Object.keys(sandpackFiles).length > 0);
  const canSync = Boolean((effectiveProjectId || effectiveJobId) && token);
  const hasEnhancedProof = proof && (proof.final_status || proof.selected_stack || proof.generated_files?.count !== undefined);

  const onProofRepair = async () => {
    if (!token || !apiBase || !effectiveJobId) return;
    const res = await axios.post(
      `${apiBase}/jobs/${encodeURIComponent(effectiveJobId)}/repair-from-proof`,
      { job_id: effectiveJobId, selected_repair_target: 'validation' },
      { headers: { Authorization: `Bearer ${token}` }, timeout: 60000 },
    );
    if (res.data?.success) refresh?.();
  };

  const onProofReplay = async () => {
    if (!token || !apiBase || !effectiveJobId) return;
    const res = await axios.post(
      `${apiBase}/jobs/${encodeURIComponent(effectiveJobId)}/replay`,
      {},
      { headers: { Authorization: `Bearer ${token}` }, timeout: 30000 },
    );
    if (res.data?.replay_job_id) navigate?.(`/app/workspace?jobId=${encodeURIComponent(res.data.replay_job_id)}`);
  };

  return (
    <div className={`uw-root ccw-root arp-ux-${uxMode}`} data-testid="unified-workspace-root">
      <div className="ccw-layout">
        <main className="ccw-center" aria-label="Build conversation">
          <header className="ccw-header">
            <div className="ccw-brand">
              <Logo
                variant="full"
                height={34}
                href={null}
                className="sidebar-logo ccw-logo"
                showTagline={false}
                showWordmark
                nameClassName="sidebar-logo-text"
              />
              <span className={`ccw-state ${statusClass(stateLabel)}`}>{stateLabel}</span>
            </div>
            <div className="ccw-header-actions">
              <span className="ccw-counter" title="Rendered runtime events">
                {compactCount(events?.length)} events
              </span>
              <span className="ccw-counter" title="Workspace paths loaded">
                {compactCount(wsPaths?.length)} files
              </span>
              <button type="button" className="ccw-icon-btn" title="Sync workspace" onClick={reloadWorkspaceFromServer} disabled={!canSync}>
                <RefreshCw size={15} />
              </button>
            </div>
          </header>

          {currentActivity?.title ? (
            <div className="ccw-live-strip" aria-live="polite">
              <span className="ccw-live-dot" />
              <span>{currentActivity.title}</span>
              {currentActivity.detailLine ? <small>{currentActivity.detailLine}</small> : null}
            </div>
          ) : null}

          <section className="ccw-transcript" aria-label="Runtime transcript">
            <BrainGuidancePanel
              userMessages={filteredUserMessages}
              events={events}
              jobStatus={job?.status}
              jobId={effectiveJobId || null}
              previewUrl={previewUrl}
              proofTruthSurface={proof?.truth_surface || null}
              token={token}
              apiBase={apiBase}
              hasTaskOrJobContext={Boolean(effectiveJobId || sessionTaskId || taskIdFromUrl)}
              buildTargetMeta={buildTargetMeta}
              buildTargetId={buildTarget}
              isTyping={Boolean(loading || stateLabel === 'working')}
              omitInlineBrandChrome
              onPause={handlePause}
              onResume={handleResume}
              onCancel={handleCancel}
              onSync={reloadWorkspaceFromServer}
              canSync={canSync}
            />
          </section>

          <footer className="ccw-composer">
            <GoalComposer
              goal={goal}
              onGoalChange={setGoal}
              onSubmit={handleSend}
              onStop={handleCancel}
              jobStatus={job?.status}
              loading={loading}
              error={null}
              errorRaw={null}
              token={token}
              onEstimateReady={() => {}}
              authLoading={authLoading}
              buildTarget={buildTarget}
              onBuildTargetChange={setBuildTarget}
              buildTargets={buildTargets}
              showExecutionTargets={false}
              showContinuation={false}
              showQuickChips={false}
              showCostEstimator={false}
              showSmartTags={false}
              showComposerHeader={false}
              enterSends
              composerInputRows={3}
              composerSubtitle={null}
              inputPlaceholder="Write a message..."
              composerVariant="workspace"
            />
          </footer>
        </main>

        {!rightCollapsed && <ResizableDivider onResize={handleResize} onDoubleClick={handleResetWidth} />}

        <aside
          className={`ccw-artifact-pane${rightCollapsed ? ' is-collapsed' : ''}`}
          style={!rightCollapsed ? { width: `${rightWidth}px` } : undefined}
          aria-label="Preview and artifacts"
        >
          <button
            type="button"
            className="ccw-collapse-btn"
            onClick={() => setRightCollapsed(!rightCollapsed)}
            aria-label={rightCollapsed ? 'Open preview pane' : 'Close preview pane'}
            title={rightCollapsed ? 'Open preview pane' : 'Close preview pane'}
          >
            {rightCollapsed ? <PanelRightOpen size={16} /> : <PanelRightClose size={16} />}
          </button>

          {!rightCollapsed ? (
            <>
              <header className="ccw-artifact-header">
                <div>
                  <strong>Artifacts</strong>
                  <span>{rightRailSubtitle || currentActivity?.title || 'Preview, files, proof'}</span>
                </div>
                <div className="ccw-artifact-actions">
                  <button type="button" className="ccw-icon-btn" title="Preview" onClick={() => setActivePane('preview')}>
                    <Eye size={15} />
                  </button>
                  <button type="button" className="ccw-icon-btn" title="Proof" onClick={() => setActivePane('proof')}>
                    <ShieldCheck size={15} />
                  </button>
                  <button type="button" className="ccw-icon-btn" title="Share" onClick={handleShare}>
                    <GitBranch size={15} />
                  </button>
                </div>
              </header>

              <div className="ccw-artifact-toolbar">
                <div className="ccw-mode-switch" title="Choose visible tooling">
                  <button type="button" className={uxMode === 'beginner' ? 'is-active' : ''} onClick={() => toggleUxMode('beginner')}>Simple</button>
                  <button type="button" className={uxMode === 'pro' ? 'is-active' : ''} onClick={() => toggleUxMode('pro')}>Dev</button>
                </div>
                <SystemStatusHUD
                  variant="minimal"
                  connectionMode={connectionMode}
                  activeAgentCount={activeAgentCount}
                  jobStatus={job?.status}
                  steps={steps}
                  healthLatencyMs={healthMs}
                  eventCount={events.length}
                  proofItemCount={proofItemCount}
                />
              </div>

              <nav className="ccw-pane-tabs" aria-label="Artifact panes">
                {visibleRightPanes.map((pane) => (
                  <PaneButton
                    key={pane}
                    pane={pane}
                    active={activePane === pane}
                    onClick={() => setActivePane(pane)}
                  />
                ))}
              </nav>

              <div className="ccw-pane-body">
                {activePane === 'preview' && (
                  <PreviewPanel
                    previewUrl={previewUrl}
                    status={previewStatus}
                    sandpackFiles={sandpackFiles}
                    sandpackDeps={sandpackDeps}
                    filesReadyKey={filesReadyKey}
                    sandpackIsFallback={sandpackIsFallback}
                    blockedDetail={previewBlockedDetail}
                    jobId={effectiveJobId}
                    token={token}
                    apiBase={apiBase}
                    jobStatus={job?.status}
                    events={events}
                  />
                )}
                {activePane === 'live' && (
                  <WorkspaceLiveControl
                    job={job}
                    stage={stage}
                    steps={steps}
                    events={events}
                    proof={proof}
                    previewStatus={previewStatus}
                    previewUrl={previewUrl}
                    hasSandpack={hasSandpack}
                    workspacePathCount={wsPaths.length}
                    latestFailure={latestFailure}
                    blockedDetail={previewBlockedDetail}
                    connectionMode={connectionMode}
                    isConnected={isConnected}
                    proofItemCount={proofItemCount}
                    activeAgentCount={activeAgentCount}
                    healthLatencyMs={healthMs}
                    onOpenPreview={() => setActivePane('preview')}
                    onOpenProof={() => setActivePane('proof')}
                    onOpenCode={() => setActivePane('code')}
                    onOpenFailure={() => setActivePane('failure')}
                  />
                )}
                {activePane === 'timeline' && (
                  <ExecutionTimeline
                    steps={steps}
                    events={events}
                    job={job}
                    onRetryStep={handleRetryStep}
                    onJumpToCode={jumpStepToCode}
                    isConnected={isConnected}
                    connectionMode={connectionMode}
                  />
                )}
                {activePane === 'proof' && (
                  hasEnhancedProof ? (
                    <EnhancedProofPanel
                      proof={proof}
                      jobId={effectiveJobId}
                      jobStatus={job?.status}
                      openWorkspacePath={openWorkspacePath}
                      onRepair={onProofRepair}
                      onReplay={onProofReplay}
                    />
                  ) : (
                    <ProofPanel
                      proof={proof}
                      jobId={effectiveJobId}
                      jobStatus={job?.status}
                      onExport={() => {}}
                      openWorkspacePath={openWorkspacePath}
                      milestoneBatch={milestoneBatch}
                      repairQueueLen={repairQueueLen}
                      onRepairComplete={refresh}
                    />
                  )
                )}
                {activePane === 'systems' && uxMode === 'pro' && (
                  <WorkspaceSystemsPanel
                    jobId={effectiveJobId}
                    projectId={effectiveProjectId}
                    token={token}
                    events={events}
                    proof={proof}
                  />
                )}
                {activePane === 'explorer' && uxMode === 'pro' && (
                  <SystemExplorer
                    steps={steps}
                    proof={proof}
                    job={job}
                    projectId={effectiveProjectId}
                    token={token}
                    openWorkspacePath={openWorkspacePath}
                  />
                )}
                {activePane === 'replay' && uxMode === 'pro' && <BuildReplay events={events} steps={steps} />}
                {activePane === 'failure' && (
                  failureStep ? (
                    <FailureDrawer
                      step={failureStep}
                      onRetry={handleRetryStep}
                      onOpenCode={jumpStepToCode}
                      onPauseJob={handleCancel}
                      onClose={() => setFailedStep(null)}
                      openWorkspacePath={openWorkspacePath}
                    />
                  ) : (
                    <div className="ccw-empty-pane">No repair issue is open.</div>
                  )
                )}
                {activePane === 'code' && uxMode === 'pro' && (
                  <div className="ccw-code-pane">
                    <div className="ccw-code-actions">
                      {effectiveJobId && token ? (
                        <button
                          type="button"
                          className="ccw-code-download"
                          disabled={zipBusy}
                          onClick={handleDownloadWorkspaceZip}
                        >
                          <FileArchive size={13} />
                          <span>{zipBusy ? 'Preparing...' : 'Download workspace'}</span>
                        </button>
                      ) : null}
                      <span>{wsPaths.length ? `${wsPaths.length} paths` : 'No file list yet'}</span>
                    </div>
                    <div className="ccw-code-main">
                      <WorkspaceFileTree
                        paths={wsPaths}
                        selectedPath={activeWsPath}
                        onSelectPath={(path) => {
                          setActiveWsPath(path);
                          setTreeRevealTick((tick) => tick + 1);
                        }}
                        revealTick={treeRevealTick}
                        loading={wsListLoading}
                      />
                      <WorkspaceFileViewer
                        activePathPosix={activeWsPath}
                        entry={wsFileCache[activeWsPath]}
                        trace={activeWsPath ? traceByPath[activeWsPath] : null}
                        editorColorMode={editorColorMode}
                        onTextChange={handleCodeChange}
                      />
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : null}
        </aside>
      </div>
    </div>
  );
}
