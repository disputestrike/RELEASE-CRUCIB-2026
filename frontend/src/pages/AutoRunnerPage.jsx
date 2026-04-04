/**
 * AutoRunnerPage — CrucibAI autonomous build workspace.
 * 3-pane layout: left rail | center pane | right pane.
 * Stage machine: input → plan → running → completed.
 */
import React, { useState, useCallback, useEffect } from 'react';
import { useAuth } from '../App';
import axios from 'axios';
import { useJobStream } from '../hooks/useJobStream';
import {
  Layers, FolderKanban, Briefcase, Bot, FileCode2, Rocket,
  BarChart3, Store, Settings, ChevronLeft, ChevronRight,
  Eye, ShieldCheck, Share2
} from 'lucide-react';
import AutoRunnerPanel from '../components/AutoRunner/AutoRunnerPanel';
import GoalComposer from '../components/AutoRunner/GoalComposer';
import PlanApproval from '../components/AutoRunner/PlanApproval';
import ExecutionTimeline from '../components/AutoRunner/ExecutionTimeline';
import ProofPanel from '../components/AutoRunner/ProofPanel';
import SystemExplorer from '../components/AutoRunner/SystemExplorer';
import FailureDrawer from '../components/AutoRunner/FailureDrawer';
import BuildReplay from '../components/AutoRunner/BuildReplay';
import BuildCompletionCard from '../components/AutoRunner/BuildCompletionCard';
import SystemStatusHUD from '../components/AutoRunner/SystemStatusHUD';
import PreviewPanel from '../components/AutoRunner/PreviewPanel';
import ResizableDivider from '../components/AutoRunner/ResizableDivider';
import './AutoRunnerPage.css';

const API = process.env.REACT_APP_BACKEND_URL || '';

const NAV_ITEMS = [
  { key: 'workspace', label: 'Workspace', Icon: Layers },
  { key: 'projects',  label: 'Projects',  Icon: FolderKanban },
  { key: 'jobs',      label: 'Jobs',       Icon: Briefcase },
  { key: 'agents',    label: 'Agents',     Icon: Bot },
  { key: 'files',     label: 'Files',      Icon: FileCode2 },
  { key: 'deploys',   label: 'Deploys',    Icon: Rocket },
  { key: 'metrics',   label: 'Metrics',    Icon: BarChart3 },
  { key: 'marketplace', label: 'Marketplace', Icon: Store },
  { key: 'settings',  label: 'Settings',   Icon: Settings },
];

const RIGHT_PANES = ['preview', 'timeline', 'proof', 'explorer', 'replay'];

export default function AutoRunnerPage() {
  const { token, user } = useAuth();

  // UX mode
  const [uxMode, setUxMode] = useState(() => localStorage.getItem('crucibai_ux_mode') || 'beginner');
  const toggleUxMode = (m) => { setUxMode(m); localStorage.setItem('crucibai_ux_mode', m); };

  // Rail collapse state
  const [leftCollapsed, setLeftCollapsed] = useState(() => localStorage.getItem('crucibai_left_collapsed') === 'true');
  const [rightCollapsed, setRightCollapsed] = useState(() => localStorage.getItem('crucibai_right_collapsed') === 'true');

  useEffect(() => { localStorage.setItem('crucibai_left_collapsed', leftCollapsed); }, [leftCollapsed]);
  useEffect(() => { localStorage.setItem('crucibai_right_collapsed', rightCollapsed); }, [rightCollapsed]);

  // Resizable right pane
  const [rightWidth, setRightWidth] = useState(() => parseInt(localStorage.getItem('crucibai_right_width') || '440'));
  useEffect(() => { localStorage.setItem('crucibai_right_width', rightWidth); }, [rightWidth]);

  const handleResize = useCallback((delta) => {
    setRightWidth(w => Math.min(640, Math.max(280, w + delta)));
  }, []);

  const handleResetWidth = useCallback(() => {
    setRightWidth(440);
  }, []);

  // Build state
  const [goal, setGoal] = useState('');
  const [autoMode, setAutoMode] = useState('guided');
  const [plan, setPlan] = useState(null);
  const [estimate, setEstimate] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [stage, setStage] = useState('input');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activePane, setActivePane] = useState('preview');
  const [activeNav, setActiveNav] = useState('workspace');
  const [failedStep, setFailedStep] = useState(null);

  // Job stream
  const { job, steps, events, proof, isConnected, refresh } = useJobStream(jobId, token);

  const isCompleted = job?.status === 'completed';
  const latestFailedStep = steps.find(s => s.status === 'failed' && !failedStep);

  // Detect completion stage
  useEffect(() => {
    if (isCompleted && stage === 'running') setStage('completed');
  }, [isCompleted, stage]);

  // Preview status derived from job state
  const previewStatus = isCompleted ? 'ready' : stage === 'running' ? 'building' : 'idle';
  const previewUrl = job?.preview_url || null;

  // Actions
  const handleGeneratePlan = async () => {
    if (!goal.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await axios.post(`${API}/api/orchestrator/plan`,
        { goal: goal.trim(), mode: autoMode },
        { headers }
      );
      setPlan(res.data.plan);
      setEstimate(res.data.estimate);
      setJobId(res.data.job_id);
      setStage('plan');
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to generate plan.');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (runMode = 'guided') => {
    if (!jobId) return;
    setLoading(true);
    setStage('running');
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.post(`${API}/api/orchestrator/run-auto`,
        { job_id: jobId },
        { headers }
      );
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to start job.');
      setStage('plan');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!jobId) return;
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.post(`${API}/api/jobs/${jobId}/cancel`, {}, { headers });
    } catch {}
  };

  const handleResume = async () => {
    if (!jobId) return;
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.post(`${API}/api/jobs/${jobId}/resume`, {}, { headers });
    } catch {}
  };

  const handleRetryStep = async (step) => {
    if (!jobId || !step) return;
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.post(`${API}/api/jobs/${jobId}/retry-step/${step.id}`, {}, { headers });
      setFailedStep(null);
      refresh();
    } catch {}
  };

  const handleReset = () => {
    setGoal('');
    setPlan(null);
    setEstimate(null);
    setJobId(null);
    setStage('input');
    setError(null);
    setFailedStep(null);
  };

  // Compute active agents count
  const activeAgentCount = [...new Set(steps.filter(s => s.status === 'running').map(s => s.agent_name))].length;

  return (
    <div className={`arp-root arp-ux-${uxMode}`}>
      {/* Top bar */}
      <div className="arp-topbar">
        <div className="arp-topbar-left">
          <span className="arp-logo">CrucibAI</span>
          <span className="arp-project-name">{user?.name || 'Project'}</span>
          <span className="arp-env-badge">dev</span>
        </div>

        <div className="arp-topbar-center">
          <AutoRunnerPanel
            mode={autoMode}
            onModeChange={setAutoMode}
            jobId={jobId}
            jobStatus={job?.status}
            onRun={() => handleApprove(autoMode)}
            onPause={handleCancel}
            onResume={handleResume}
            onCancel={handleCancel}
            budget={estimate}
          />
        </div>

        <div className="arp-topbar-right">
          <button className="arp-topbar-btn" title="Preview" onClick={() => { setActivePane('preview'); setRightCollapsed(false); }}>
            <Eye size={14} />
            <span className="arp-topbar-btn-label">Preview</span>
          </button>
          <button className="arp-topbar-btn" title="Deploy">
            <Rocket size={14} />
            <span className="arp-topbar-btn-label">Deploy</span>
          </button>
          <button className="arp-topbar-btn" title="Proof" onClick={() => { setActivePane('proof'); setRightCollapsed(false); }}>
            <ShieldCheck size={14} />
            <span className="arp-topbar-btn-label">Proof</span>
          </button>

          <div className="arp-mode-switch">
            <button
              className={`arp-ux-btn ${uxMode === 'beginner' ? 'active' : ''}`}
              onClick={() => toggleUxMode('beginner')}
            >Beginner</button>
            <button
              className={`arp-ux-btn ${uxMode === 'pro' ? 'active' : ''}`}
              onClick={() => toggleUxMode('pro')}
            >Pro</button>
          </div>

          <SystemStatusHUD
            isConnected={isConnected}
            activeAgentCount={activeAgentCount}
            jobStatus={job?.status}
            steps={steps}
          />
        </div>
      </div>

      {/* Main 3-pane layout */}
      <div className="arp-layout">
        {/* Left rail */}
        <div className={`arp-left-rail ${leftCollapsed ? 'collapsed' : ''}`}>
          <div className="arp-rail-toggle" onClick={() => setLeftCollapsed(!leftCollapsed)}>
            {leftCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
          </div>
          <nav className="arp-nav">
            {NAV_ITEMS.map(({ key, label, Icon }) => (
              <button
                key={key}
                className={`arp-nav-item ${activeNav === key ? 'active' : ''}`}
                onClick={() => setActiveNav(key)}
                title={leftCollapsed ? label : undefined}
              >
                <Icon size={16} />
                {!leftCollapsed && <span className="arp-nav-label">{label}</span>}
              </button>
            ))}
          </nav>
        </div>

        {/* Center pane */}
        <div className="arp-center-pane">
          {stage === 'input' && (
            <GoalComposer
              goal={goal}
              onGoalChange={setGoal}
              onSubmit={handleGeneratePlan}
              loading={loading}
              error={error}
              token={token}
              onEstimateReady={setEstimate}
            />
          )}

          {stage === 'plan' && plan && (
            <PlanApproval
              plan={plan}
              estimate={estimate}
              onApprove={() => handleApprove('guided')}
              onRunAuto={() => handleApprove('auto')}
              onEdit={() => setStage('input')}
              loading={loading}
            />
          )}

          {(stage === 'running' || stage === 'completed') && (
            <div className="arp-execution-area">
              {isCompleted && (
                <BuildCompletionCard
                  job={job}
                  proof={proof}
                  onOpenPreview={() => { setActivePane('preview'); setRightCollapsed(false); }}
                  onOpenProof={() => { setActivePane('proof'); setRightCollapsed(false); }}
                  onOpenCode={() => {}}
                  onDeployAgain={handleReset}
                />
              )}

              <ExecutionTimeline
                steps={steps}
                events={events}
                job={job}
                onRetryStep={handleRetryStep}
                onJumpToCode={() => {}}
                isConnected={isConnected}
              />

              {(failedStep || latestFailedStep) && (
                <FailureDrawer
                  step={failedStep || latestFailedStep}
                  onRetry={handleRetryStep}
                  onOpenCode={() => {}}
                  onPauseJob={handleCancel}
                  onClose={() => setFailedStep(null)}
                />
              )}
            </div>
          )}
        </div>

        {/* Resizable divider */}
        {!rightCollapsed && (
          <ResizableDivider
            onResize={handleResize}
            onDoubleClick={handleResetWidth}
          />
        )}

        {/* Right pane */}
        <div className={`arp-right-pane ${rightCollapsed ? 'collapsed' : ''}`} style={!rightCollapsed ? { width: rightWidth + 'px' } : undefined}>
          <div className="arp-right-toggle" onClick={() => setRightCollapsed(!rightCollapsed)}>
            {rightCollapsed ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
          </div>

          {!rightCollapsed && (
            <>
              <div className="arp-pane-tabs">
                {RIGHT_PANES.map(p => {
                  if (p === 'explorer' && uxMode === 'beginner') return null;
                  if (p === 'replay' && uxMode === 'beginner') return null;
                  return (
                    <button
                      key={p}
                      className={`arp-pane-tab ${activePane === p ? 'active' : ''}`}
                      onClick={() => setActivePane(p)}
                    >
                      {p.charAt(0).toUpperCase() + p.slice(1)}
                    </button>
                  );
                })}
                {uxMode === 'pro' && (
                  <button
                    className={`arp-pane-tab ${activePane === 'system' ? 'active' : ''}`}
                    onClick={() => setActivePane('system')}
                  >
                    System
                  </button>
                )}
              </div>

              <div className="arp-pane-content">
                {activePane === 'preview' && (
                  <PreviewPanel
                    previewUrl={previewUrl}
                    status={previewStatus}
                  />
                )}
                {activePane === 'timeline' && (
                  <ExecutionTimeline
                    steps={steps}
                    events={events}
                    job={job}
                    onRetryStep={handleRetryStep}
                    onJumpToCode={() => {}}
                    isConnected={isConnected}
                  />
                )}
                {activePane === 'proof' && (
                  <ProofPanel
                    proof={proof}
                    jobId={jobId}
                    onExport={() => {}}
                  />
                )}
                {activePane === 'explorer' && uxMode === 'pro' && (
                  <SystemExplorer
                    steps={steps}
                    proof={proof}
                    job={job}
                    projectId={user?.id}
                    token={token}
                  />
                )}
                {activePane === 'system' && uxMode === 'pro' && (
                  <SystemExplorer
                    steps={steps}
                    proof={proof}
                    job={job}
                    projectId={user?.id}
                    token={token}
                  />
                )}
                {activePane === 'replay' && uxMode === 'pro' && (
                  <BuildReplay events={events} steps={steps} />
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
