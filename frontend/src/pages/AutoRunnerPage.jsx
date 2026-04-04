/**
 * AutoRunnerPage — Main autonomous build workspace.
 * Combines: goal input → plan approval → execution timeline → proof → completion.
 * Also includes: mode switch (Beginner/Pro), system explorer, failure drawer, replay.
 */
import React, { useState, useCallback } from 'react';
import { useAuth } from '../App';
import axios from 'axios';
import { useJobStream } from '../hooks/useJobStream';
import AutoRunnerPanel from '../components/AutoRunner/AutoRunnerPanel';
import PlanApproval from '../components/AutoRunner/PlanApproval';
import ExecutionTimeline from '../components/AutoRunner/ExecutionTimeline';
import ProofPanel from '../components/AutoRunner/ProofPanel';
import SystemExplorer from '../components/AutoRunner/SystemExplorer';
import FailureDrawer from '../components/AutoRunner/FailureDrawer';
import BuildReplay from '../components/AutoRunner/BuildReplay';
import BuildCompletionCard from '../components/AutoRunner/BuildCompletionCard';
import CostEstimator from '../components/AutoRunner/CostEstimator';
import './AutoRunnerPage.css';

const API = process.env.REACT_APP_BACKEND_URL || '';

const PANES = ['timeline', 'proof', 'explorer', 'replay'];

export default function AutoRunnerPage() {
  const { token, user } = useAuth();

  // User experience mode
  const [uxMode, setUxMode] = useState(() => localStorage.getItem('crucibai_ux_mode') || 'beginner');
  const toggleUxMode = (m) => { setUxMode(m); localStorage.setItem('crucibai_ux_mode', m); };

  // Build state
  const [goal, setGoal] = useState('');
  const [autoMode, setAutoMode] = useState('guided');
  const [plan, setPlan] = useState(null);
  const [estimate, setEstimate] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [stage, setStage] = useState('input');  // input | plan | running | completed
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activePane, setActivePane] = useState('timeline');
  const [failedStep, setFailedStep] = useState(null);

  // Job stream
  const { job, steps, events, proof, isConnected, refresh } = useJobStream(jobId, token);

  // Detect completion
  const isCompleted = job?.status === 'completed';
  const isFailed = job?.status === 'failed';

  // If job has failed steps, show failure drawer
  const latestFailedStep = steps.find(s => s.status === 'failed' && !failedStep);

  // ── Actions ──────────────────────────────────────────────────────────────

  const handleGeneratePlan = async () => {
    if (!goal.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await axios.post(`${API}/api/orchestrator/plan`,
        { project_id: user?.id || 'demo', goal: goal.trim(), mode: autoMode },
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

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className={`auto-runner-page arp-ux-${uxMode}`}>
      {/* Top bar */}
      <div className="arp-topbar">
        <div className="arp-topbar-left">
          <span className="arp-logo">CrucibAI</span>
          <span className="arp-separator">›</span>
          <span className="arp-page-name">Auto-Runner</span>
        </div>
        <div className="arp-topbar-center">
          {jobId && (
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
          )}
        </div>
        <div className="arp-topbar-right">
          {/* Beginner / Pro mode switch */}
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
        </div>
      </div>

      {/* Main layout */}
      <div className="arp-main">
        {/* Left rail — goal input / plan approval / completion */}
        <div className="arp-left-pane">
          {stage === 'input' && (
            <div className="arp-goal-area">
              <div className="arp-goal-label">What do you want to build?</div>
              <textarea
                className="arp-goal-input"
                placeholder="e.g. Build a SaaS dashboard with auth, billing, and analytics"
                value={goal}
                onChange={e => setGoal(e.target.value)}
                rows={4}
              />
              <CostEstimator goal={goal} token={token} onEstimateReady={setEstimate} />
              {error && <div className="arp-error">{error}</div>}
              <button
                className="arp-generate-btn"
                onClick={handleGeneratePlan}
                disabled={loading || !goal.trim()}
              >
                {loading ? 'Generating plan...' : 'Generate Plan →'}
              </button>
            </div>
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
            <div className="arp-running-info">
              {isCompleted && (
                <BuildCompletionCard
                  job={job}
                  proof={proof}
                  onOpenPreview={() => setActivePane('preview')}
                  onOpenProof={() => setActivePane('proof')}
                  onOpenCode={() => {}}
                  onDeployAgain={handleReset}
                />
              )}
              {!isCompleted && (
                <div className="arp-job-status-card">
                  <div className="arp-job-goal">{job?.goal || goal}</div>
                  <div className="arp-job-phase">Phase: <strong>{job?.current_phase || '—'}</strong></div>
                  <div className="arp-job-score">Quality: <strong>{job?.quality_score || 0}</strong></div>
                </div>
              )}
              {/* Failure drawer */}
              {(failedStep || latestFailedStep) && (
                <div style={{ marginTop: 12 }}>
                  <FailureDrawer
                    step={failedStep || latestFailedStep}
                    onRetry={handleRetryStep}
                    onOpenCode={() => {}}
                    onPauseJob={handleCancel}
                    onClose={() => setFailedStep(null)}
                  />
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right pane — tabs */}
        <div className="arp-right-pane">
          {/* Tab bar */}
          <div className="arp-pane-tabs">
            {PANES.map(p => (
              <button
                key={p}
                className={`arp-pane-tab ${activePane === p ? 'active' : ''}`}
                onClick={() => setActivePane(p)}
              >
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </button>
            ))}
            {uxMode === 'pro' && (
              <button
                className={`arp-pane-tab ${activePane === 'system' ? 'active' : ''}`}
                onClick={() => setActivePane('system')}
              >
                System X-Ray
              </button>
            )}
          </div>

          <div className="arp-pane-content">
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
                onExport={() => alert('Export proof bundle — coming soon!')}
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
            {activePane === 'replay' && (
              <BuildReplay events={events} steps={steps} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
