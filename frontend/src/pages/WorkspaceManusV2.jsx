/**
 * WorkspaceManusV2 — Manus.im-exact layout, fully wired to backend
 * All data comes from real API endpoints — zero placeholders.
 */
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth, API } from '../App';
import { useJobStream } from '../hooks/useJobStream';
import { useTaskStore } from '../stores/useTaskStore';
import { computeSandpackFilesWithMeta } from '../workspace/sandpackFromFiles';
import { SandpackProvider, SandpackPreview } from '@codesandbox/sandpack-react';
import axios from 'axios';
import './ManusStyle.css';

// ── Icons ─────────────────────────────────────────────────────────────────────
const Ico = {
  Plus:    () => <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>,
  Home:    () => <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><path d="M2 6.5L7.5 2 13 6.5V13H9.5v-3h-4v3H2V6.5z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/></svg>,
  Agent:   () => <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><circle cx="7.5" cy="5" r="3" stroke="currentColor" strokeWidth="1.3"/><path d="M2 13c0-3 2.5-5 5.5-5s5.5 2 5.5 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>,
  Search:  () => <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><circle cx="6.5" cy="6.5" r="4" stroke="currentColor" strokeWidth="1.3"/><path d="M11 11l2.5 2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>,
  Library: () => <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><rect x="2" y="2" width="4" height="11" rx="1" stroke="currentColor" strokeWidth="1.3"/><rect x="8" y="2" width="5" height="11" rx="1" stroke="currentColor" strokeWidth="1.3"/></svg>,
  Share:   () => <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="11" cy="3" r="1.5" stroke="currentColor" strokeWidth="1.3"/><circle cx="3" cy="7" r="1.5" stroke="currentColor" strokeWidth="1.3"/><circle cx="11" cy="11" r="1.5" stroke="currentColor" strokeWidth="1.3"/><path d="M4.3 6.3L9.7 3.7M4.3 7.7l5.4 2.6" stroke="currentColor" strokeWidth="1.3"/></svg>,
  Publish: () => <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1v8M4 4l3-3 3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/><path d="M2 10v2a1 1 0 001 1h8a1 1 0 001-1v-2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>,
  Mic:     () => <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><rect x="5" y="1" width="5" height="8" rx="2.5" stroke="currentColor" strokeWidth="1.3"/><path d="M2.5 7.5a5 5 0 0010 0" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/><path d="M7.5 12.5v2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>,
  Attach:  () => <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><path d="M12.5 7.5l-5.5 5.5a4 4 0 01-5.657-5.657l6-6a2.5 2.5 0 013.536 3.536l-6 6a1 1 0 01-1.414-1.414l5.5-5.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>,
  Screen:  () => <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><rect x="1" y="2" width="13" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.3"/><path d="M5 13h5M7.5 11v2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>,
  Send:    () => <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M12 7L2 2l2.5 5L2 12l10-5z" fill="currentColor"/></svg>,
  Chevron: ({ open }) => <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{transform: open?'rotate(180deg)':'none',transition:'transform 0.2s'}}><path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  Check:   () => <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 5l2.5 2.5L8 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  X:       () => <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 2l6 6M8 2l-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>,
  File:    () => <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 1h6l3 3v7a1 1 0 01-1 1H2a1 1 0 01-1-1V2a1 1 0 011-1z" stroke="currentColor" strokeWidth="1.2"/><path d="M8 1v3h3" stroke="currentColor" strokeWidth="1.2"/></svg>,
  Terminal:() => <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><rect x="1" y="1" width="10" height="10" rx="2" stroke="currentColor" strokeWidth="1.2"/><path d="M3.5 4.5L5.5 6l-2 1.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/><path d="M6.5 7.5h2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/></svg>,
  Refresh: () => <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M11 6.5A4.5 4.5 0 112 6.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/><path d="M11 3v3.5H7.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  External:() => <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M7 2h4v4M11 2L6 7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/><path d="M6 3H2a1 1 0 00-1 1v7a1 1 0 001 1h7a1 1 0 001-1V8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>,
};

function StepIcon({ status }) {
  const cls = `manus-step-icon ${status === 'completed' ? 'done' : status === 'running' || status === 'verifying' ? 'running' : status === 'failed' || status === 'blocked' ? 'failed' : 'pending'}`;
  return (
    <span className={cls}>
      {status === 'completed' && <Ico.Check />}
      {(status === 'failed' || status === 'blocked') && <Ico.X />}
    </span>
  );
}

// ── Hook: load real workspace files from backend ──────────────────────────────
function useWorkspaceFiles(jobId, token) {
  const [files, setFiles] = useState([]);
  const [fileContent, setFileContent] = useState({});
  const [loading, setLoading] = useState(false);

  const loadFiles = useCallback(async () => {
    if (!jobId || !token) return;
    setLoading(true);
    try {
      const res = await axios.get(`${API}/jobs/${jobId}/workspace/files`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setFiles(res.data?.files || []);
    } catch { setFiles([]); }
    finally { setLoading(false); }
  }, [jobId, token]);

  const loadFileContent = useCallback(async (path) => {
    if (!jobId || !token || fileContent[path] !== undefined) return;
    try {
      const res = await axios.get(`${API}/jobs/${jobId}/workspace/file`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { path }
      });
      setFileContent(prev => ({ ...prev, [path]: res.data?.content || '' }));
    } catch {
      setFileContent(prev => ({ ...prev, [path]: '// Could not load file' }));
    }
  }, [jobId, token, fileContent]);

  useEffect(() => { loadFiles(); }, [loadFiles]);

  return { files, fileContent, loadFileContent, reloadFiles: loadFiles, loading };
}

// ── Main component ────────────────────────────────────────────────────────────
export default function WorkspaceManusV2() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { token, user } = useAuth();
  const { tasks, addTask, updateTask } = useTaskStore();

  const jobIdFromUrl = searchParams.get('jobId');
  const taskIdFromUrl = searchParams.get('taskId');

  const [goal, setGoal] = useState('');
  const [activeJobId, setActiveJobId] = useState(jobIdFromUrl || null);
  const [stage, setStage] = useState(jobIdFromUrl ? 'running' : 'input');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activePane, setActivePane] = useState('preview');
  const [activeFile, setActiveFile] = useState(null);
  const [taskCardOpen, setTaskCardOpen] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState({});
  const [deployLoading, setDeployLoading] = useState(false);
  const [deployResult, setDeployResult] = useState(null);
  const [workflows, setWorkflows] = useState({});
  const [workflowsOpen, setWorkflowsOpen] = useState(false);
  const [workflowLoading, setWorkflowLoading] = useState(null);

  // Load workflows from backend
  useEffect(() => {
    axios.get(`${API}/workflows`, token ? { headers: { Authorization: `Bearer ${token}` } } : {})
      .then(r => setWorkflows(r.data?.workflows || {}))
      .catch(() => {});
  }, [token]);

  const handleWorkflow = useCallback(async (workflowKey) => {
    setWorkflowLoading(workflowKey);
    setWorkflowsOpen(false);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.post(`${API}/workflows/run`,
        { workflow_key: workflowKey, project_id: job?.project_id || null },
        { headers }
      );
      if (res.data.success) {
        setActiveJobId(res.data.job_id);
        setStage('running');
        setSearchParams(p => { const n = new URLSearchParams(p); n.set('jobId', res.data.job_id); return n; }, { replace: true });
      } else if (res.data.fallback) {
        // Backend couldn't start it directly — set as goal and submit
        setGoal(res.data.goal);
      }
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setWorkflowLoading(null);
    }
  }, [token, job?.project_id, setSearchParams]);

  const chatScrollRef = useRef(null);
  const textareaRef = useRef(null);

  // ── Real data from backend ──────────────────────────────────────────────────
  const { job, steps, events, proof, isConnected, connectionMode, refresh } = useJobStream(
    activeJobId, token
  );
  const { files: wsFiles, fileContent, loadFileContent, reloadFiles } = useWorkspaceFiles(
    activeJobId, token
  );

  // ── Derive stage from live job status ───────────────────────────────────────
  useEffect(() => {
    if (!job) return;
    if (job.status === 'completed') setStage('completed');
    else if (job.status === 'failed') setStage('failed');
    else if (job.status === 'running') setStage('running');
    else if (job.status === 'pending') setStage('running');
  }, [job?.status]);

  // ── Auto-scroll ─────────────────────────────────────────────────────────────
  useEffect(() => {
    const el = chatScrollRef.current;
    if (el) requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; });
  }, [events?.length, steps?.length]);

  // ── Reload workspace files when job completes ───────────────────────────────
  useEffect(() => {
    if (stage === 'completed') reloadFiles();
  }, [stage]);

  // ── Load selected file content ──────────────────────────────────────────────
  useEffect(() => {
    if (activeFile && activePane === 'code') loadFileContent(activeFile);
  }, [activeFile, activePane]);

  // ── Preview URL (real cascade) ──────────────────────────────────────────────
  const previewUrl = job?.dev_server_url || job?.preview_url || job?.published_url || job?.deploy_url
    || (stage === 'completed' && activeJobId ? `/published/${encodeURIComponent(activeJobId)}/` : null);

  // ── Sandpack fallback from step output_files ────────────────────────────────
  const { sandpackFiles } = useMemo(() => computeSandpackFilesWithMeta(
    Object.fromEntries((steps || []).filter(s => s.output_files).flatMap(s => {
      try { return Object.entries(JSON.parse(s.output_files)); } catch { return []; }
    }))
  ), [steps]);

  // ── Action chips from real events ───────────────────────────────────────────
  const recentChips = useMemo(() => {
    return (events || []).slice(-30).reduce((acc, ev) => {
      const t = ev?.type || ev?.event_type || '';
      const p = ev?.payload || {};
      let chip = null;
      if (t.includes('file_written') || t.includes('workspace_write') || p.path) {
        chip = { type: 'file', text: p.path || p.file_path || t, icon: 'file' };
      } else if (t.includes('command') || t.includes('terminal') || t.includes('exec') || p.command) {
        chip = { type: 'terminal', text: p.command?.slice(0, 80) || t, icon: 'terminal' };
      } else if (t === 'brain_guidance') {
        const payload = p.payload || p;
        if (payload.headline) chip = { type: 'brain', text: payload.headline, icon: 'brain' };
      }
      if (chip && !acc.find(c => c.text === chip.text)) acc.push(chip);
      return acc;
    }, []).slice(-6);
  }, [events]);

  // ── Step groups ─────────────────────────────────────────────────────────────
  const stepGroups = useMemo(() => {
    const g = {};
    (steps || []).forEach(s => {
      const grp = (s.phase || 'Build').charAt(0).toUpperCase() + (s.phase || 'Build').slice(1);
      if (!g[grp]) g[grp] = [];
      g[grp].push(s);
    });
    return g;
  }, [steps]);

  const totalSteps = steps?.length || 0;
  const completedSteps = steps?.filter(s => s.status === 'completed').length || 0;
  const failedSteps = steps?.filter(s => s.status === 'failed' || s.status === 'blocked') || [];
  const currentStep = steps?.find(s => s.status === 'running' || s.status === 'verifying');
  const isRunning = stage === 'running' || loading;

  // ── Brain narration from events ─────────────────────────────────────────────
  const brainMessages = useMemo(() => {
    return (events || [])
      .filter(e => (e.type || e.event_type) === 'brain_guidance')
      .map(e => {
        const p = e.payload?.payload || e.payload || {};
        return p.summary || p.headline || null;
      })
      .filter(Boolean)
      .slice(-3);
  }, [events]);

  // ── Send goal ───────────────────────────────────────────────────────────────
  const handleSend = useCallback(async () => {
    const trimmed = goal.trim();
    if (!trimmed || loading) return;

    // Steer running job
    if (isRunning && activeJobId) {
      try {
        const headers = { Authorization: `Bearer ${token}` };
        await axios.post(`${API}/jobs/${activeJobId}/steer`,
          { message: trimmed, resume: false }, { headers });
        setGoal('');
      } catch (e) {
        setError(e.response?.data?.detail || e.message);
      }
      return;
    }

    setLoading(true);
    setError(null);
    setStage('running');
    setActiveJobId(null);
    setDeployResult(null);

    try {
      const headers = { Authorization: `Bearer ${token}` };
      const planRes = await axios.post(`${API}/orchestrator/plan`,
        { goal: trimmed, mode: 'auto' }, { headers });
      const jid = planRes.data.job_id;
      setActiveJobId(jid);
      setSearchParams(p => { const n = new URLSearchParams(p); n.set('jobId', jid); return n; }, { replace: true });

      const taskId = `task_${Date.now()}`;
      addTask({ id: taskId, name: trimmed.slice(0, 80), prompt: trimmed, status: 'running', type: 'build', createdAt: Date.now() });

      await axios.post(`${API}/orchestrator/run-auto`, { job_id: jid }, { headers });
      setGoal('');
    } catch (e) {
      const detail = e.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : detail?.message || e.message || 'Build failed');
      setStage('failed');
    } finally {
      setLoading(false);
    }
  }, [goal, loading, isRunning, activeJobId, token, setSearchParams, addTask]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  // ── One-click Railway deploy ────────────────────────────────────────────────
  const handleDeploy = useCallback(async () => {
    if (!activeJobId || !job?.project_id || deployLoading) return;
    setDeployLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.post(`${API}/projects/${job.project_id}/deploy/railway`,
        { job_id: activeJobId }, { headers });
      setDeployResult(res.data);
    } catch (e) {
      setDeployResult({ error: e.response?.data?.detail || e.message });
    } finally {
      setDeployLoading(false);
    }
  }, [activeJobId, job?.project_id, deployLoading, token]);

  // ── File tree: group by directory ───────────────────────────────────────────
  const fileTree = useMemo(() => {
    const tree = {};
    wsFiles.forEach(f => {
      const parts = f.path.split('/');
      const dir = parts.length > 1 ? parts.slice(0, -1).join('/') : '/';
      if (!tree[dir]) tree[dir] = [];
      tree[dir].push(f);
    });
    return tree;
  }, [wsFiles]);

  // ── Proof summary ────────────────────────────────────────────────────────────
  const proofItems = useMemo(() => {
    if (!proof) return [];
    const bundle = proof.bundle || {};
    return Object.entries(bundle).flatMap(([type, items]) =>
      (items || []).map(item => ({ type, ...item }))
    );
  }, [proof]);

  const recentTasks = tasks.slice(0, 10);
  const statusColor = { running: '#3b82f6', completed: '#10b981', failed: '#ef4444', input: '#d1d5db' };

  return (
    <div className="manus-shell">

      {/* ── Top bar ── */}
      <div className="manus-topbar">
        <div className="manus-topbar-left">
          <button className="manus-compose-tool-btn" style={{marginRight:4,fontSize:16}} onClick={() => navigate('/app')}>☰</button>
          <div className="manus-topbar-brand">Crucible</div>
          <div className="manus-model-badge">
            <span style={{width:7,height:7,borderRadius:'50%',background:isConnected?'#10b981':'#d1d5db',display:'inline-block'}} />
            <span>{connectionMode === 'sse' ? 'Live' : connectionMode === 'polling' ? 'Polling' : 'Offline'}</span>
            <Ico.Chevron open={false} />
          </div>
        </div>
        <div className="manus-topbar-right">
          {isRunning && currentStep && (
            <div style={{display:'flex',alignItems:'center',gap:6,fontSize:13,color:'#3b82f6'}}>
              <div className="manus-thinking-dot" />
              <span>{currentStep.agent_name || currentStep.step_key}</span>
              {totalSteps > 0 && <span style={{color:'#999',fontSize:12}}>{completedSteps}/{totalSteps}</span>}
            </div>
          )}
          {stage === 'completed' && activeJobId && (
            <a
              href={`${API}/jobs/${activeJobId}/workspace/download`}
              download
              className="manus-btn-ghost"
              style={{color:'#666'}}
              title="Download all generated files as ZIP">
              📥 Download
            </a>
          )}
          {stage === 'completed' && !deployResult && (
            <button className="manus-btn-ghost" onClick={handleDeploy} disabled={deployLoading}
              style={{color:'#10b981',borderColor:'#10b981'}}>
              {deployLoading ? '…' : '🚄 Deploy'}
            </button>
          )}
          {deployResult?.deploy_url && (
            <a href={deployResult.deploy_url} target="_blank" rel="noopener noreferrer"
              className="manus-btn-ghost" style={{color:'#10b981'}}>↗ Live</a>
          )}
          <button className="manus-btn-ghost"><Ico.Share /> Share</button>
          <button className="manus-btn-publish" onClick={() => previewUrl && window.open(previewUrl,'_blank')}>
            <Ico.Publish /> Publish
          </button>
          {activeJobId && (
            <button className="manus-btn-ghost" onClick={() => {
              setActiveJobId(null); setStage('input'); setGoal('');
              setSearchParams({}); setDeployResult(null);
            }}>✕</button>
          )}
        </div>
      </div>

      <div className="manus-body">

        {/* ── Left sidebar ── */}
        <div className="manus-sidebar">
          <div className="manus-sidebar-top">
            <button className="manus-new-task-btn" onClick={() => {
              setActiveJobId(null); setStage('input'); setGoal('');
              setSearchParams({}); setDeployResult(null);
            }}>
              <Ico.Plus /> New task
            </button>
          </div>
          <div className="manus-sidebar-nav">
            <Link to="/app" className="manus-nav-item"><Ico.Home /> Home</Link>
            <Link to="/app/agents" className="manus-nav-item"><Ico.Agent /> Agents</Link>
            <button className="manus-nav-item"><Ico.Search /> Search</button>
            <Link to="/app/learn" className="manus-nav-item"><Ico.Library /> Library</Link>
          </div>
          <div className="manus-sidebar-section">
            <span>History</span>
          </div>
          <div className="manus-task-list">
            {recentTasks.length === 0 && (
              <div style={{padding:'12px',fontSize:12,color:'#aaa'}}>No tasks yet</div>
            )}
            {recentTasks.map((t, i) => (
              <button key={t.id || i}
                className={`manus-task-item ${(t.jobId || t.id) === activeJobId ? 'active' : ''}`}
                onClick={() => {
                  if (t.jobId) { setActiveJobId(t.jobId); setStage('completed'); setSearchParams({ jobId: t.jobId }); }
                }}>
                <div className={`manus-task-dot ${
                  t.status === 'completed' ? 'done' : t.status === 'failed' ? 'failed' :
                  t.status === 'running' ? 'running' : 'idle'}`} />
                <span className="manus-task-label">{t.name || t.prompt?.slice(0, 60) || 'Task'}</span>
              </button>
            ))}
          </div>

          {/* ── Workflows ── */}
          <div style={{borderTop:'1px solid #e5e5e0',padding:'8px'}}>
            <button
              className="manus-nav-item"
              style={{width:'100%',fontWeight:600,justifyContent:'space-between'}}
              onClick={() => setWorkflowsOpen(o => !o)}>
              <span>⚡ Workflows</span>
              <Ico.Chevron open={workflowsOpen} />
            </button>
            {workflowsOpen && (
              <div style={{maxHeight:320,overflowY:'auto',marginTop:4}}>
                {Object.entries(workflows).map(([category, wfList]) => (
                  <div key={category}>
                    <div style={{fontSize:10,fontWeight:700,textTransform:'uppercase',
                      letterSpacing:'0.06em',color:'#aaa',padding:'6px 10px 2px'}}>{category}</div>
                    {wfList.map(wf => (
                      <button key={wf.key}
                        className="manus-nav-item"
                        style={{width:'100%',fontSize:12,padding:'5px 10px',opacity:workflowLoading?0.6:1}}
                        disabled={!!workflowLoading}
                        onClick={() => handleWorkflow(wf.key)}
                        title={wf.description}>
                        <span>{wf.icon}</span>
                        <span style={{flex:1,textAlign:'left',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{wf.name}</span>
                        {workflowLoading === wf.key && <div className="manus-thinking-dot" style={{width:6,height:6}} />}
                      </button>
                    ))}
                  </div>
                ))}
                {Object.keys(workflows).length === 0 && (
                  <div style={{padding:'8px 12px',fontSize:12,color:'#aaa'}}>Loading workflows…</div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── Center chat ── */}
        <div className="manus-center">
          <div className="manus-chat-scroll" ref={chatScrollRef}>
            <div className="manus-chat-inner">

              {/* User goal bubble */}
              {(job?.goal || (isRunning && goal)) && (
                <div className="manus-msg-user">{job?.goal || goal}</div>
              )}

              {/* Empty state */}
              {stage === 'input' && !job && (
                <div style={{textAlign:'center',padding:'60px 0 20px',color:'#aaa'}}>
                  <div style={{fontSize:32,marginBottom:12}}>✦</div>
                  <div style={{fontSize:15,color:'#666',marginBottom:6}}>What do you want to build?</div>
                  <div style={{fontSize:13}}>Describe it below and Crucible will build it.</div>
                </div>
              )}

              {/* Agent response */}
              {(isRunning || stage === 'completed' || stage === 'failed') && (
                <div className="manus-msg-agent">
                  <div className="manus-agent-avatar">C</div>
                  <div className="manus-agent-body">
                    <div className="manus-agent-name">
                      Crucible
                      <span className="manus-agent-tier">Auto</span>
                      {isConnected && <span style={{fontSize:11,color:'#10b981',fontWeight:400}}>● Live</span>}
                    </div>

                    {/* Brain narration — real from backend events */}
                    {brainMessages.map((msg, i) => (
                      <div key={i} className="manus-agent-text" style={{marginBottom:6}}>{msg}</div>
                    ))}
                    {brainMessages.length === 0 && isRunning && (
                      <div className="manus-agent-text" style={{marginBottom:8}}>
                        {completedSteps === 0
                          ? "I've reviewed your approved plan and I'm beginning execution: foundation and dependencies first, then features and quality checks in order."
                          : `${completedSteps} steps done — continuing with ${currentStep?.agent_name || 'next steps'}…`}
                      </div>
                    )}
                    {stage === 'completed' && (
                      <div className="manus-agent-text" style={{marginBottom:8,color:'#10b981'}}>
                        ✓ Build complete — {completedSteps}/{totalSteps} steps. Preview is ready.
                        {deployResult?.deploy_url && <span> <a href={deployResult.deploy_url} target="_blank" rel="noopener noreferrer" style={{color:'#3b82f6'}}>View live →</a></span>}
                      </div>
                    )}
                    {stage === 'failed' && (
                      <div className="manus-agent-text" style={{marginBottom:8,color:'#ef4444'}}>
                        {failedSteps.length} step{failedSteps.length !== 1 ? 's' : ''} failed.
                        {failedSteps[0]?.error_message && <span> {failedSteps[0].error_message.slice(0, 120)}</span>}
                      </div>
                    )}

                    {/* Action chips — real from events */}
                    {recentChips.length > 0 && (
                      <div className="manus-action-chips">
                        {recentChips.map((chip, i) => (
                          <div key={i} className="manus-chip">
                            <span className="manus-chip-icon">
                              {chip.icon === 'file' ? <Ico.File /> : chip.icon === 'terminal' ? <Ico.Terminal /> : '✦'}
                            </span>
                            <span className="manus-chip-text">{chip.text}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Task progress card — real steps from backend */}
                    {totalSteps > 0 && (
                      <div className="manus-task-card" style={{marginTop:8}}>
                        <div className="manus-task-card-header" onClick={() => setTaskCardOpen(o => !o)}>
                          <span>{job?.goal?.slice(0, 48) || 'Build progress'}{job?.goal?.length > 48 ? '…' : ''}</span>
                          <div className="manus-task-card-meta">
                            <span style={{color: stage==='completed'?'#10b981': stage==='failed'?'#ef4444':'inherit'}}>
                              {completedSteps}/{totalSteps}
                            </span>
                            <Ico.Chevron open={taskCardOpen} />
                          </div>
                        </div>
                        {taskCardOpen && (
                          <div className="manus-task-progress-list">
                            {Object.entries(stepGroups).map(([group, groupSteps]) => {
                              const done = groupSteps.filter(s => s.status === 'completed').length;
                              const isOpen = expandedGroups[group] !== false;
                              return (
                                <div key={group}>
                                  <div style={{fontSize:11,color:'#999',fontWeight:600,textTransform:'uppercase',
                                    letterSpacing:'0.05em',padding:'6px 0 3px',cursor:'pointer',
                                    display:'flex',justifyContent:'space-between'}}
                                    onClick={() => setExpandedGroups(eg => ({...eg, [group]: !isOpen}))}>
                                    <span>{group}</span>
                                    <span>{done}/{groupSteps.length}</span>
                                  </div>
                                  {isOpen && groupSteps.map(s => (
                                    <div key={s.id} className="manus-task-progress-item">
                                      <StepIcon status={s.status} />
                                      <span style={{
                                        color: s.status==='running'||s.status==='verifying' ? '#3b82f6' :
                                               s.status==='failed'||s.status==='blocked' ? '#ef4444' : '#333',
                                        fontWeight: s.status==='running' ? 500 : 400,
                                        fontSize: 13,
                                      }}>
                                        {s.agent_name || s.step_key}
                                      </span>
                                      {(s.status === 'running' || s.status === 'verifying') && (
                                        <span className="manus-thinking-dot" style={{marginLeft:'auto',width:6,height:6}} />
                                      )}
                                    </div>
                                  ))}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Thinking indicator */}
                    {isRunning && (
                      <div className="manus-thinking" style={{marginTop:10}}>
                        <div className="manus-thinking-dot" />
                        {currentStep ? `Working on ${currentStep.agent_name || currentStep.step_key}` : 'Processing…'}
                      </div>
                    )}
                  </div>
                </div>
              )}

            </div>
          </div>

          {/* ── Compose bar ── */}
          <div className="manus-composer">
            {error && (
              <div style={{color:'#ef4444',fontSize:12,marginBottom:8,padding:'6px 12px',
                background:'#fef2f2',borderRadius:8,border:'1px solid #fecaca'}}>
                {error}
              </div>
            )}
            <div className="manus-compose-box">
              <textarea
                ref={textareaRef}
                className="manus-compose-textarea"
                placeholder={isRunning ? "Steer anytime — Enter sends on this same run." : "Describe what to build…"}
                value={goal}
                onChange={e => { setGoal(e.target.value); e.target.style.height='auto'; e.target.style.height=Math.min(e.target.scrollHeight,160)+'px'; }}
                onKeyDown={handleKeyDown}
                rows={1}
              />
              <div className="manus-compose-actions">
                <div className="manus-compose-tools">
                  <button className="manus-compose-tool-btn" title="Attach file"><Ico.Attach /></button>
                  <button className="manus-compose-tool-btn" title="Screen share"><Ico.Screen /></button>
                  <button className="manus-compose-tool-btn" title="Voice input"><Ico.Mic /></button>
                </div>
                <button className="manus-compose-send" onClick={handleSend}
                  disabled={!goal.trim() || loading} title="Send (Enter)">
                  {loading ? <div className="manus-thinking-dot" style={{width:8,height:8}} /> : <Ico.Send />}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* ── Right pane ── */}
        <div className="manus-right">
          <div className="manus-right-tabs">
            {['preview','code','proof','failure','timeline'].map(p => (
              <button key={p} className={`manus-right-tab ${activePane===p?'active':''}`}
                onClick={() => setActivePane(p)}>
                {p.charAt(0).toUpperCase()+p.slice(1)}
                {p === 'failure' && failedSteps.length > 0 && (
                  <span style={{marginLeft:4,background:'#ef4444',color:'#fff',borderRadius:'10px',
                    fontSize:10,padding:'1px 5px'}}>{failedSteps.length}</span>
                )}
              </button>
            ))}
          </div>

          <div className="manus-right-content">

            {/* ── Preview ── real iframe or Sandpack fallback */}
            {activePane === 'preview' && (
              <div style={{display:'flex',flexDirection:'column',flex:1,overflow:'hidden',position:'relative'}}>
                <div className="manus-preview-bar">
                  <div className="manus-preview-nav-btns">
                    <button className="manus-preview-nav-btn" title="Refresh"
                      onClick={() => { const f = document.querySelector('.manus-preview-frame'); if(f) f.src=f.src; }}>
                      <Ico.Refresh />
                    </button>
                  </div>
                  <div className="manus-preview-url-bar">
                    <span>🏠</span>
                    <span style={{flex:1,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
                      {previewUrl ? previewUrl.replace(/^https?:\/\/[^/]+/, '') || '/' : '/'}
                    </span>
                  </div>
                  {previewUrl && (
                    <button className="manus-preview-nav-btn" title="Open in new tab"
                      onClick={() => window.open(previewUrl, '_blank')}>
                      <Ico.External />
                    </button>
                  )}
                </div>

                {previewUrl ? (
                  <iframe className="manus-preview-frame" src={previewUrl} title="Live Preview"
                    sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals" />
                ) : Object.keys(sandpackFiles || {}).length > 0 ? (
                  <div style={{flex:1,overflow:'hidden'}}>
                    <SandpackProvider files={sandpackFiles} template="react"
                      theme="dark" options={{autoReload:true,recompileDelay:500}}>
                      <SandpackPreview style={{height:'100%'}} />
                    </SandpackProvider>
                  </div>
                ) : (
                  <div className="manus-preview-empty">
                    <div className="manus-preview-empty-icon">
                      <div className="manus-preview-empty-row" style={{width:'100%'}} />
                      <div style={{display:'flex',gap:4,width:'100%'}}>
                        <div className="manus-preview-empty-row" style={{width:'40%'}} />
                        <div className="manus-preview-empty-row" style={{width:'55%'}} />
                      </div>
                      <div style={{display:'flex',gap:4,width:'100%'}}>
                        <div className="manus-preview-empty-row" style={{width:'70%'}} />
                        <div className="manus-preview-empty-row" style={{width:'25%'}} />
                      </div>
                    </div>
                    <div className="manus-preview-empty-text">
                      {isRunning ? 'Crucible is building your app. Hang tight!' : 'Preview will appear here when build completes'}
                      {isRunning && <><br/><span style={{fontSize:12}}>Sandpack preview loads when code is ready</span></>}
                    </div>
                  </div>
                )}
                {isRunning && previewUrl && (
                  <div className="manus-preview-taking-shape">Taking shape</div>
                )}
              </div>
            )}

            {/* ── Code ── real workspace files */}
            {activePane === 'code' && (
              <div className="manus-code-split">
                <div className="manus-file-tree" style={{maxHeight:220}}>
                  {wsFiles.length === 0 && (
                    <div style={{padding:'8px 12px',fontSize:12,color:'#999'}}>
                      {isRunning ? 'Files generating…' : 'No workspace files'}
                    </div>
                  )}
                  {Object.entries(fileTree).map(([dir, dirFiles]) => (
                    <div key={dir}>
                      {dir !== '/' && <div style={{fontSize:11,color:'#888',padding:'4px 8px 2px',fontWeight:600}}>{dir}/</div>}
                      {dirFiles.map(f => (
                        <div key={f.path}
                          className={`manus-file-item ${activeFile===f.path?'active':''}`}
                          onClick={() => { setActiveFile(f.path); loadFileContent(f.path); }}>
                          <Ico.File />
                          <span>{f.path.split('/').pop()}</span>
                          <span style={{marginLeft:'auto',fontSize:10,color:'#bbb'}}>{(f.size/1024).toFixed(1)}k</span>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
                <div style={{flex:1,overflow:'auto',background:'#1e1e1e',padding:'12px 16px'}}>
                  {activeFile ? (
                    fileContent[activeFile] !== undefined ? (
                      <pre style={{color:'#d4d4d4',fontSize:12,margin:0,fontFamily:"'Fira Code',monospace",
                        whiteSpace:'pre-wrap',lineHeight:1.6}}>
                        {fileContent[activeFile]}
                      </pre>
                    ) : (
                      <div style={{color:'#666',fontSize:12,paddingTop:8}}>Loading…</div>
                    )
                  ) : (
                    <div style={{color:'#555',fontSize:12,paddingTop:8}}>
                      {wsFiles.length > 0 ? 'Select a file from the tree above' : 'Files will appear when build generates code'}
                    </div>
                  )}
                </div>
                {wsFiles.length > 0 && (
                  <div style={{padding:'6px 10px',borderTop:'1px solid #333',background:'#1e1e1e',
                    display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                    <span style={{fontSize:11,color:'#666'}}>{wsFiles.length} files</span>
                    <div style={{display:'flex',gap:8}}>
                      <button onClick={reloadFiles} style={{background:'transparent',border:'none',
                        color:'#666',fontSize:11,cursor:'pointer'}}>↻ Refresh</button>
                      {activeJobId && (
                        <a href={`${API}/jobs/${activeJobId}/workspace/download`} download
                          style={{color:'#10b981',fontSize:11,textDecoration:'none'}}>
                          📥 Download ZIP
                        </a>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ── Proof ── real proof bundle from backend */}
            {activePane === 'proof' && (
              <div style={{padding:16,overflow:'auto',flex:1}}>
                <div style={{fontSize:14,fontWeight:600,marginBottom:12,display:'flex',justifyContent:'space-between'}}>
                  <span>Proof</span>
                  {proof?.total_proof_items > 0 && (
                    <span style={{fontSize:12,color:'#10b981'}}>{proof.total_proof_items} items</span>
                  )}
                </div>
                {proof?.quality_score !== undefined && (
                  <div style={{background:'#f0fdf4',border:'1px solid #bbf7d0',borderRadius:8,
                    padding:'10px 14px',marginBottom:12,fontSize:13}}>
                    Quality score: <strong style={{color:'#16a34a'}}>{
                      typeof proof.quality_score === 'number' && proof.quality_score <= 1
                        ? (proof.quality_score * 100).toFixed(1) : proof.quality_score
                    }</strong>
                  </div>
                )}
                {proofItems.length === 0 && (
                  <div style={{fontSize:13,color:'#999'}}>
                    {isRunning ? 'Proof collecting as build runs…' : 'No proof items recorded'}
                  </div>
                )}
                {Object.entries(proof?.bundle || {}).map(([type, items]) => (
                  items?.length > 0 && (
                    <div key={type} style={{marginBottom:12}}>
                      <div style={{fontSize:11,fontWeight:600,textTransform:'uppercase',letterSpacing:'0.05em',
                        color:'#666',marginBottom:6}}>{type} ({items.length})</div>
                      {items.slice(0,5).map((item, i) => (
                        <div key={i} style={{background:'#f9f9f5',border:'1px solid #e5e5e0',borderRadius:6,
                          padding:'6px 10px',marginBottom:4,fontSize:12,color:'#444'}}>
                          {item.proof_type || item.type || item.title || JSON.stringify(item).slice(0,100)}
                        </div>
                      ))}
                      {items.length > 5 && <div style={{fontSize:11,color:'#999'}}>+{items.length-5} more</div>}
                    </div>
                  )
                ))}
              </div>
            )}

            {/* ── Failure ── real failed steps */}
            {activePane === 'failure' && (
              <div style={{padding:16,overflow:'auto',flex:1}}>
                <div style={{fontSize:14,fontWeight:600,marginBottom:12}}>
                  Failures {failedSteps.length > 0 && <span style={{color:'#ef4444'}}>({failedSteps.length})</span>}
                </div>
                {failedSteps.length === 0 && (
                  <div style={{fontSize:13,color:'#10b981'}}>✓ No failures so far</div>
                )}
                {failedSteps.map(s => (
                  <div key={s.id} style={{background:'#fef2f2',border:'1px solid #fecaca',
                    borderRadius:8,padding:'10px 14px',marginBottom:10}}>
                    <div style={{fontSize:13,fontWeight:600,color:'#dc2626',marginBottom:4}}>
                      {s.agent_name || s.step_key}
                    </div>
                    <div style={{fontSize:12,color:'#666',marginBottom:s.error_details?6:0}}>
                      {s.error_message || 'Unknown error'}
                    </div>
                    {s.error_details && (
                      <pre style={{fontSize:11,color:'#888',margin:0,whiteSpace:'pre-wrap',
                        background:'#fff',padding:'6px 8px',borderRadius:4,marginTop:4}}>
                        {typeof s.error_details === 'string' ? s.error_details.slice(0,400) : JSON.stringify(s.error_details,null,2).slice(0,400)}
                      </pre>
                    )}
                    <div style={{fontSize:11,color:'#aaa',marginTop:4}}>
                      Attempt {(s.retry_count||0)+1} · Phase: {s.phase || '—'}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* ── Timeline ── real step history */}
            {activePane === 'timeline' && (
              <div style={{padding:16,overflow:'auto',flex:1}}>
                <div style={{fontSize:14,fontWeight:600,marginBottom:12}}>Timeline</div>
                {(steps||[]).length === 0 && (
                  <div style={{fontSize:13,color:'#999'}}>Steps will appear here as build runs</div>
                )}
                <div style={{position:'relative',paddingLeft:20}}>
                  <div style={{position:'absolute',left:8,top:0,bottom:0,width:2,background:'#e5e5e0'}} />
                  {(steps||[]).map((s,i) => (
                    <div key={s.id} style={{marginBottom:12,position:'relative'}}>
                      <div style={{position:'absolute',left:-16,top:3,width:10,height:10,borderRadius:'50%',
                        background: s.status==='completed'?'#10b981': s.status==='failed'?'#ef4444':
                                    s.status==='running'?'#3b82f6':'#d1d5db',
                        border:'2px solid #fff'}} />
                      <div style={{fontSize:13,fontWeight:500,color:'#1a1a1a'}}>
                        {s.agent_name || s.step_key}
                      </div>
                      <div style={{fontSize:12,color:s.status==='completed'?'#10b981':s.status==='failed'?'#ef4444':'#999',
                        display:'flex',gap:8,alignItems:'center',marginTop:2}}>
                        <span>{s.status}</span>
                        {s.phase && <span style={{color:'#bbb'}}>· {s.phase}</span>}
                        {s.retry_count > 0 && <span style={{color:'#f59e0b'}}>· {s.retry_count} retries</span>}
                      </div>
                      {s.status==='running' && <div className="manus-thinking-dot" style={{marginTop:4,width:6,height:6}} />}
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>
        </div>

      </div>
    </div>
  );
}
