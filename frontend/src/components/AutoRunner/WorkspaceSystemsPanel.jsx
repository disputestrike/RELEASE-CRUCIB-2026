import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  Bot,
  Cpu,
  FolderGit2,
  Phone,
  Play,
  Radar,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { API_BASE as API } from '../../apiBase';
import TerminalAgent from '../TerminalAgent';
import './WorkspaceSystemsPanel.css';

function prettyDetail(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (detail && typeof detail === 'object') {
    try {
      return JSON.stringify(detail);
    } catch {
      return 'Request failed';
    }
  }
  return error?.message || 'Request failed';
}

export default function WorkspaceSystemsPanel({
  jobId,
  projectId,
  token,
  events = [],
  proof = null,
  taskProgress = null,
  actionChips = [],
  controller = null,
}) {
  const headers = useMemo(
    () => (token ? { Authorization: `Bearer ${token}` } : {}),
    [token],
  );

  const [activeSkillIds, setActiveSkillIds] = useState([]);
  const [skillsLoading, setSkillsLoading] = useState(false);

  const [spawnTask, setSpawnTask] = useState('Probe the current job for the fastest safe next action.');
  const [spawnBusy, setSpawnBusy] = useState(false);
  const [spawnError, setSpawnError] = useState('');
  const [spawnResult, setSpawnResult] = useState(null);

  const [scenario, setScenario] = useState('Simulate how the current build behaves if the next fix prioritizes reliability over speed.');
  const [simulationBusy, setSimulationBusy] = useState(false);
  const [simulationError, setSimulationError] = useState('');
  const [simulationResult, setSimulationResult] = useState(null);

  const [mobilePlatform, setMobilePlatform] = useState('ios');
  const [mobileTarget, setMobileTarget] = useState('debug');
  const [mobileBusy, setMobileBusy] = useState(false);
  const [mobileError, setMobileError] = useState('');
  const [mobileBuild, setMobileBuild] = useState(null);
  const [mobileQr, setMobileQr] = useState(null);
  const [mobileChecklist, setMobileChecklist] = useState(null);
  const [mobileHelperBusy, setMobileHelperBusy] = useState(false);
  const [mobileHelperError, setMobileHelperError] = useState('');

  const [worktreeId, setWorktreeId] = useState(() => `wt-${Date.now().toString(36)}`);
  const [worktreeBusy, setWorktreeBusy] = useState(false);
  const [worktreeError, setWorktreeError] = useState('');
  const [worktreeStatus, setWorktreeStatus] = useState(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setSkillsLoading(true);
    axios
      .get(`${API}/skills`, { headers })
      .then((res) => {
        if (cancelled) return;
        setActiveSkillIds(Array.isArray(res.data?.active_skill_ids) ? res.data.active_skill_ids : []);
      })
      .catch(() => {
        if (!cancelled) setActiveSkillIds([]);
      })
      .finally(() => {
        if (!cancelled) setSkillsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, headers]);

  const providerSummary = useMemo(() => {
    const providerEvent = [...events].reverse().find((event) => {
      const type = event?.type || event?.event_type;
      return type === 'provider.chain.selected.runtime';
    });
    const payload = providerEvent?.payload && typeof providerEvent.payload === 'object'
      ? providerEvent.payload
      : (() => {
          try {
            return JSON.parse(providerEvent?.payload_json || '{}');
          } catch {
            return {};
          }
        })();
    const provider = payload?.provider || {};
    return {
      current: provider.alias || provider.model || provider.type || 'pending',
      trust: typeof proof?.trust_score === 'number' ? proof.trust_score.toFixed(1) : '0.0',
      quality: typeof proof?.quality_score === 'number' ? proof.quality_score.toFixed(1) : '0.0',
      proofItems: typeof proof?.total_proof_items === 'number' ? proof.total_proof_items : 0,
    };
  }, [events, proof]);

  const runSpawn = async () => {
    if (!jobId || !token) return;
    setSpawnBusy(true);
    setSpawnError('');
    try {
      const res = await axios.post(
        `${API}/spawn/run`,
        {
          jobId,
          task: spawnTask,
          config: { branches: 4, mode: 'swan' },
          context: {},
        },
        { headers },
      );
      setSpawnResult(res.data || null);
    } catch (error) {
      setSpawnResult(null);
      setSpawnError(prettyDetail(error));
    } finally {
      setSpawnBusy(false);
    }
  };

  const runSimulation = async () => {
    if (!jobId || !token) return;
    setSimulationBusy(true);
    setSimulationError('');
    try {
      const res = await axios.post(
        `${API}/spawn/simulate`,
        {
          jobId,
          scenario,
          population_size: 24,
          rounds: 3,
          agent_roles: [],
          priors: {},
        },
        { headers },
      );
      setSimulationResult(res.data || null);
    } catch (error) {
      setSimulationResult(null);
      setSimulationError(prettyDetail(error));
    } finally {
      setSimulationBusy(false);
    }
  };

  const queueMobileBuild = async () => {
    if (!projectId) return;
    setMobileBusy(true);
    setMobileError('');
    try {
      const res = await axios.post(
        `${API}/mobile/build`,
        { platform: mobilePlatform, project_id: projectId, target: mobileTarget || undefined },
        { headers },
      );
      setMobileBuild(res.data || null);
    } catch (error) {
      setMobileBuild(null);
      setMobileError(prettyDetail(error));
    } finally {
      setMobileBusy(false);
    }
  };

  const loadMobileHelpers = async () => {
    if (!projectId || !token) return;
    setMobileHelperBusy(true);
    setMobileHelperError('');
    try {
      const [qrRes, checklistRes] = await Promise.allSettled([
        axios.get(`${API}/projects/${encodeURIComponent(projectId)}/mobile/qr`, { headers }),
        axios.get(`${API}/projects/${encodeURIComponent(projectId)}/mobile/store-checklist`, { headers }),
      ]);
      if (qrRes.status === 'fulfilled') setMobileQr(qrRes.value.data || null);
      if (checklistRes.status === 'fulfilled') setMobileChecklist(checklistRes.value.data || null);
      if (qrRes.status === 'rejected' && checklistRes.status === 'rejected') {
        setMobileHelperError(prettyDetail(qrRes.reason || checklistRes.reason));
      }
    } catch (error) {
      setMobileHelperError(prettyDetail(error));
    } finally {
      setMobileHelperBusy(false);
    }
  };

  const runEasUpdate = async () => {
    if (!projectId || !token) return;
    setMobileHelperBusy(true);
    setMobileHelperError('');
    try {
      const res = await axios.post(
        `${API}/projects/${encodeURIComponent(projectId)}/mobile/eas-update`,
        { message: `Workspace publish ${new Date().toISOString()}`, channel: 'preview', runtime_version: '1.0.0' },
        { headers },
      );
      setMobileChecklist((prev) => ({ ...(prev || {}), last_update: res.data || null }));
    } catch (error) {
      setMobileHelperError(prettyDetail(error));
    } finally {
      setMobileHelperBusy(false);
    }
  };

  const createWorktree = async () => {
    if (!token) return;
    setWorktreeBusy(true);
    setWorktreeError('');
    try {
      const res = await axios.post(`${API}/worktrees/create`, { id: worktreeId }, { headers });
      setWorktreeStatus({ kind: 'created', data: res.data || null });
    } catch (error) {
      setWorktreeStatus(null);
      setWorktreeError(prettyDetail(error));
    } finally {
      setWorktreeBusy(false);
    }
  };

  const mergeWorktree = async () => {
    if (!jobId || !token) return;
    setWorktreeBusy(true);
    setWorktreeError('');
    try {
      const res = await axios.post(`${API}/worktrees/merge`, { id: worktreeId, jobId }, { headers });
      setWorktreeStatus({ kind: 'merged', data: res.data || null });
    } catch (error) {
      setWorktreeStatus(null);
      setWorktreeError(prettyDetail(error));
    } finally {
      setWorktreeBusy(false);
    }
  };

  const deleteWorktree = async () => {
    if (!token) return;
    setWorktreeBusy(true);
    setWorktreeError('');
    try {
      const res = await axios.post(`${API}/worktrees/delete`, { id: worktreeId }, { headers });
      setWorktreeStatus({ kind: 'deleted', data: res.data || null });
    } catch (error) {
      setWorktreeStatus(null);
      setWorktreeError(prettyDetail(error));
    } finally {
      setWorktreeBusy(false);
    }
  };

  return (
    <div className="wsp-root">
      {taskProgress && (
        <section className="wsp-card wsp-progress-card">
          <div className="wsp-card-title"><Radar size={16} /> Task Progress</div>
          <div className="wsp-progress-bar-bg">
            <div 
              className="wsp-progress-bar-fill" 
              style={{ width: `${taskProgress.percentage || 0}%` }} 
            />
          </div>
          <div className="wsp-progress-meta">
            <span>{taskProgress.summary || taskProgress.label || 'Processing...'}</span>
            <strong>{taskProgress.percentage || 0}%</strong>
          </div>
          {actionChips.length > 0 && (
            <div className="wsp-chip-row" style={{ marginTop: '8px' }}>
              {actionChips.map((chip, i) => (
                <span key={i} className={`wsp-chip wsp-chip-action ${chip.type || ''}`}>
                  {chip.label}
                </span>
              ))}
            </div>
          )}
        </section>
      )}

      {controller && (
        <section className="wsp-card">
          <div className="wsp-card-title"><Bot size={16} /> Controller Intelligence</div>
          <div className="wsp-controller-status">
            <div className="wsp-inline-item">
              <span>State</span>
              <strong>{controller.state || 'idle'}</strong>
            </div>
            <div className="wsp-inline-item">
              <span>Focus</span>
              <strong>{controller.current_focus || 'None'}</strong>
            </div>
          </div>
          {controller.recommendation && (
            <div className="wsp-result" style={{ gridTemplateColumns: '1fr', marginTop: '4px' }}>
              <div>
                <span>Recommendation</span>
                <p style={{ fontSize: '12px', margin: '4px 0 0' }}>{controller.recommendation}</p>
              </div>
            </div>
          )}
        </section>
      )}

      <section className="wsp-card">
        <div className="wsp-card-header">
          <div>
            <h3>Systems Overview</h3>
            <p>Advanced operator tools and read-only runtime visibility.</p>
          </div>
          <div className="wsp-summary-grid">
            <div>
              <span>Provider</span>
              <strong>{providerSummary.current}</strong>
            </div>
            <div>
              <span>Trust</span>
              <strong>{providerSummary.trust}</strong>
            </div>
            <div>
              <span>Quality</span>
              <strong>{providerSummary.quality}</strong>
            </div>
            <div>
              <span>Proof</span>
              <strong>{providerSummary.proofItems}</strong>
            </div>
          </div>
        </div>
        <div className="wsp-inline-list">
          <div className="wsp-inline-item">
            <Sparkles size={14} />
            <span>Active skills</span>
            <strong>{skillsLoading ? 'Loading…' : activeSkillIds.length || 'None'}</strong>
          </div>
          <a className="wsp-link-btn" href="/app/skills">Manage skills</a>
          <a className="wsp-link-btn" href="/status">Status</a>
        </div>
        {activeSkillIds.length > 0 ? (
          <div className="wsp-chip-row">
            {activeSkillIds.map((skillId) => (
              <span key={skillId} className="wsp-chip">{skillId}</span>
            ))}
          </div>
        ) : null}
      </section>

      <section className="wsp-card">
        <div className="wsp-card-title"><Radar size={16} /> Scenario Simulation</div>
        <textarea
          className="wsp-textarea"
          value={scenario}
          onChange={(event) => setScenario(event.target.value)}
          placeholder="Describe the scenario to simulate"
        />
        <div className="wsp-actions">
          <button type="button" className="wsp-btn" disabled={!jobId || !token || simulationBusy || !scenario.trim()} onClick={runSimulation}>
            <Play size={14} /> {simulationBusy ? 'Running…' : 'Run simulation'}
          </button>
          {!jobId ? <span className="wsp-muted">Open a job first to run orchestration simulation.</span> : null}
        </div>
        {simulationError ? <div className="wsp-error">{simulationError}</div> : null}
        {simulationResult ? (
          <div className="wsp-result">
            <div><span>Recommendation</span><strong>{simulationResult.recommendation || 'No recommendation'}</strong></div>
            <div><span>Consensus</span><strong>{simulationResult.consensus_reached ? 'Reached' : 'Mixed'}</strong></div>
            <div><span>Updates</span><strong>{Array.isArray(simulationResult.updates) ? simulationResult.updates.length : 0}</strong></div>
          </div>
        ) : null}
      </section>

      <section className="wsp-card">
        <div className="wsp-card-title"><Bot size={16} /> Subagent Swarm</div>
        <textarea
          className="wsp-textarea"
          value={spawnTask}
          onChange={(event) => setSpawnTask(event.target.value)}
          placeholder="Describe the branch task"
        />
        <div className="wsp-actions">
          <button type="button" className="wsp-btn" disabled={!jobId || !token || spawnBusy || !spawnTask.trim()} onClick={runSpawn}>
            <Play size={14} /> {spawnBusy ? 'Running…' : 'Run swarm'}
          </button>
        </div>
        {spawnError ? <div className="wsp-error">{spawnError}</div> : null}
        {spawnResult ? (
          <div className="wsp-result">
            <div><span>Confidence</span><strong>{typeof spawnResult.confidence === 'number' ? spawnResult.confidence.toFixed(2) : '0.00'}</strong></div>
            <div><span>Branches</span><strong>{spawnResult.swarm?.actual_branches || 0}</strong></div>
            <div><span>Action</span><strong>{spawnResult.recommendedAction || 'Proceed'}</strong></div>
          </div>
        ) : null}
      </section>

      <section className="wsp-card">
        <div className="wsp-card-title"><Phone size={16} /> Mobile Builder</div>
        <div className="wsp-form-row">
          <label>
            Platform
            <select className="wsp-input" value={mobilePlatform} onChange={(event) => setMobilePlatform(event.target.value)}>
              <option value="ios">iOS</option>
              <option value="android">Android</option>
            </select>
          </label>
          <label>
            Target
            <select className="wsp-input" value={mobileTarget} onChange={(event) => setMobileTarget(event.target.value)}>
              <option value="debug">Debug</option>
              <option value="release">Release</option>
            </select>
          </label>
        </div>
        <div className="wsp-actions">
          <button type="button" className="wsp-btn" disabled={!projectId || mobileBusy} onClick={queueMobileBuild}>
            <Play size={14} /> {mobileBusy ? 'Queueing…' : 'Queue mobile build'}
          </button>
          <button type="button" className="wsp-btn wsp-btn-secondary" disabled={!projectId || !token || mobileHelperBusy} onClick={loadMobileHelpers}>
            <ShieldCheck size={14} /> {mobileHelperBusy ? 'Loading…' : 'Load mobile tools'}
          </button>
          <button type="button" className="wsp-btn wsp-btn-secondary" disabled={!projectId || !token || mobileHelperBusy} onClick={runEasUpdate}>
            <Cpu size={14} /> Publish EAS update
          </button>
        </div>
        {!projectId ? <div className="wsp-muted">Project context is required for mobile tools.</div> : null}
        {mobileError ? <div className="wsp-error">{mobileError}</div> : null}
        {mobileHelperError ? <div className="wsp-error">{mobileHelperError}</div> : null}
        {mobileBuild ? (
          <div className="wsp-result">
            <div><span>Job</span><strong>{mobileBuild.job_id}</strong></div>
            <div><span>Status</span><strong>{mobileBuild.status}</strong></div>
            <div><span>Platform</span><strong>{mobileBuild.platform}</strong></div>
          </div>
        ) : null}
        {mobileQr?.qr_code ? (
          <div className="wsp-mobile-preview">
            <img src={mobileQr.qr_code} alt="Expo QR code" className="wsp-qr" />
            <div className="wsp-mobile-copy">
              <strong>Expo preview ready</strong>
              <span>{mobileQr.expo_url}</span>
            </div>
          </div>
        ) : null}
        {Array.isArray(mobileChecklist?.sections) && mobileChecklist.sections.length > 0 ? (
          <div className="wsp-checklist">
            {mobileChecklist.sections.slice(0, 2).map((section) => (
              <div key={section.title} className="wsp-checklist-section">
                <strong>{section.title}</strong>
                <span>{Array.isArray(section.items) ? section.items.length : 0} items</span>
              </div>
            ))}
          </div>
        ) : null}
      </section>

      <section className="wsp-card">
        <div className="wsp-card-title"><FolderGit2 size={16} /> Worktrees</div>
        <label>
          Worktree id
          <input className="wsp-input" value={worktreeId} onChange={(event) => setWorktreeId(event.target.value)} />
        </label>
        <div className="wsp-actions">
          <button type="button" className="wsp-btn wsp-btn-secondary" disabled={!token || worktreeBusy || !worktreeId.trim()} onClick={createWorktree}>Create</button>
          <button type="button" className="wsp-btn wsp-btn-secondary" disabled={!jobId || !token || worktreeBusy || !worktreeId.trim()} onClick={mergeWorktree}>Merge</button>
          <button type="button" className="wsp-btn wsp-btn-secondary" disabled={!token || worktreeBusy || !worktreeId.trim()} onClick={deleteWorktree}>Delete</button>
        </div>
        {worktreeError ? <div className="wsp-error">{worktreeError}</div> : null}
        {worktreeStatus ? (
          <div className="wsp-result">
            <div><span>Last action</span><strong>{worktreeStatus.kind}</strong></div>
            <div><span>Detail</span><strong>{worktreeStatus.data?.status || worktreeStatus.data?.id || 'ok'}</strong></div>
            <div><span>Job linked</span><strong>{jobId ? 'Yes' : 'No'}</strong></div>
          </div>
        ) : null}
      </section>

      <section className="wsp-card wsp-card-terminal">
        <div className="wsp-card-title"><Cpu size={16} /> Terminal</div>
        <div className="wsp-terminal-wrap">
          <TerminalAgent projectId={projectId} token={token} />
        </div>
      </section>
    </div>
  );
}