/**
 * WorkspaceManusV2 — pixel-accurate Manus.im replica layout
 * Wraps all UnifiedWorkspace logic, replaces the visual shell.
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation, useSearchParams, Link } from 'react-router-dom';
import { useAuth, API } from '../App';
import { useJobStream } from '../hooks/useJobStream';
import { useTaskStore } from '../stores/useTaskStore';
import PreviewPanel from '../components/AutoRunner/PreviewPanel';
import WorkspaceFileViewer from '../components/AutoRunner/WorkspaceFileViewer';
import WorkspaceFileTree from '../components/AutoRunner/WorkspaceFileTree';
import { computeSandpackFilesWithMeta } from '../workspace/sandpackFromFiles';
import axios from 'axios';
import './ManusStyle.css';

// Icons (inline SVG for zero deps)
const IcoPlus = () => <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>;
const IcoHome = () => <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><path d="M2 6.5L7.5 2 13 6.5V13H9.5v-3h-4v3H2V6.5z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/></svg>;
const IcoAgent = () => <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><circle cx="7.5" cy="5" r="3" stroke="currentColor" strokeWidth="1.3"/><path d="M2 13c0-3 2.5-5 5.5-5s5.5 2 5.5 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>;
const IcoSearch = () => <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><circle cx="6.5" cy="6.5" r="4" stroke="currentColor" strokeWidth="1.3"/><path d="M11 11l2.5 2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>;
const IcoLibrary = () => <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><rect x="2" y="2" width="4" height="11" rx="1" stroke="currentColor" strokeWidth="1.3"/><rect x="8" y="2" width="5" height="11" rx="1" stroke="currentColor" strokeWidth="1.3"/></svg>;
const IcoShare = () => <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="11" cy="3" r="1.5" stroke="currentColor" strokeWidth="1.3"/><circle cx="3" cy="7" r="1.5" stroke="currentColor" strokeWidth="1.3"/><circle cx="11" cy="11" r="1.5" stroke="currentColor" strokeWidth="1.3"/><path d="M4.3 6.3L9.7 3.7M4.3 7.7l5.4 2.6" stroke="currentColor" strokeWidth="1.3"/></svg>;
const IcoPublish = () => <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1v8M4 4l3-3 3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/><path d="M2 10v2a1 1 0 001 1h8a1 1 0 001-1v-2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>;
const IcoMic = () => <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><rect x="5" y="1" width="5" height="8" rx="2.5" stroke="currentColor" strokeWidth="1.3"/><path d="M2.5 7.5a5 5 0 0010 0" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/><path d="M7.5 12.5v2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>;
const IcoAttach = () => <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><path d="M12.5 7.5l-5.5 5.5a4 4 0 01-5.657-5.657l6-6a2.5 2.5 0 013.536 3.536l-6 6a1 1 0 01-1.414-1.414l5.5-5.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>;
const IcoScreen = () => <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><rect x="1" y="2" width="13" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.3"/><path d="M5 13h5M7.5 11v2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>;
const IcoSend = () => <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M12 7L2 2l2.5 5L2 12l10-5z" fill="currentColor"/></svg>;
const IcoChevron = ({ open }) => <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}><path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>;
const IcoEdit = () => <span style={{fontSize:11}}>✎</span>;
const IcoTerminal = () => <span style={{fontSize:11}}>{'>'}_</span>;
const IcoCheck = () => <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 5l2.5 2.5L8 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>;
const IcoX = () => <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 2l6 6M8 2l-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>;

function stepIcon(status) {
  if (status === 'completed') return <span className="manus-step-icon done"><IcoCheck /></span>;
  if (status === 'running' || status === 'verifying') return <span className="manus-step-icon running"><IcoSend /></span>;
  if (status === 'failed' || status === 'blocked') return <span className="manus-step-icon failed"><IcoX /></span>;
  return <span className="manus-step-icon pending" />;
}

function chipIcon(type) {
  if (type === 'file') return <span className="manus-chip-icon"><IcoEdit /></span>;
  if (type === 'terminal') return <span className="manus-chip-icon"><IcoTerminal /></span>;
  return <span className="manus-chip-icon">🔧</span>;
}

function parseChipFromEvent(ev) {
  const t = ev?.type || ev?.event_type || '';
  const payload = ev?.payload || {};
  const path = payload?.path || payload?.file_path || payload?.step_key || '';
  if (t.includes('file') || t.includes('write') || t.includes('workspace')) {
    return { type: 'file', text: path || t };
  }
  if (t.includes('terminal') || t.includes('command') || t.includes('exec')) {
    return { type: 'terminal', text: payload?.command || t };
  }
  return null;
}

export default function WorkspaceManusV2() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { token, user } = useAuth();
  const { tasks, addTask, updateTask } = useTaskStore();

  const jobIdFromUrl = searchParams.get('jobId');
  const taskIdFromUrl = searchParams.get('taskId');

  const [goal, setGoal] = useState('');
  const [activeJobId, setActiveJobId] = useState(jobIdFromUrl || null);
  const [stage, setStage] = useState('input'); // input | plan | running | completed | failed
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activePane, setActivePane] = useState('preview');
  const [activeFile, setActiveFile] = useState(null);
  const [taskCardOpen, setTaskCardOpen] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState({});

  const chatScrollRef = useRef(null);
  const textareaRef = useRef(null);

  // Stream job data
  const { job, steps, events, proof, isConnected, connectionMode, refresh } = useJobStream(
    activeJobId, token, API
  );

  // Derive state from job
  useEffect(() => {
    if (!job) return;
    if (job.status === 'completed') setStage('completed');
    else if (job.status === 'failed') setStage('failed');
    else if (job.status === 'running') setStage('running');
  }, [job?.status]);

  // Auto-scroll chat
  useEffect(() => {
    const el = chatScrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [events, steps]);

  // Preview URL cascade
  const previewUrl = job?.dev_server_url || job?.preview_url || job?.published_url || job?.deploy_url
    || (stage === 'completed' && activeJobId ? `/published/${encodeURIComponent(activeJobId)}/` : null);

  // Sandpack files
  const { sandpackFiles, isFallback: sandpackIsFallback } = React.useMemo(
    () => computeSandpackFilesWithMeta(
      Object.fromEntries((steps || []).filter(s => s.output_files).flatMap(s => {
        try { return Object.entries(JSON.parse(s.output_files)); } catch { return []; }
      }))
    ),
    [steps]
  );

  // Build chips from recent events
  const recentChips = React.useMemo(() => {
    return (events || []).slice(-20).map(parseChipFromEvent).filter(Boolean).slice(-8);
  }, [events]);

  // Step groups for task progress
  const stepGroups = React.useMemo(() => {
    const groups = {};
    (steps || []).forEach(s => {
      const g = s.phase || 'Build';
      if (!groups[g]) groups[g] = [];
      groups[g].push(s);
    });
    return groups;
  }, [steps]);

  const totalSteps = steps?.length || 0;
  const completedSteps = steps?.filter(s => s.status === 'completed').length || 0;

  // Send goal
  const handleSend = useCallback(async () => {
    const trimmed = goal.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError(null);
    setStage('running');
    const headers = { Authorization: `Bearer ${token}` };
    try {
      const planRes = await axios.post(`${API}/orchestrator/plan`,
        { goal: trimmed, mode: 'auto' }, { headers });
      const jid = planRes.data.job_id;
      setActiveJobId(jid);
      setSearchParams(p => { const n = new URLSearchParams(p); n.set('jobId', jid); return n; }, { replace: true });
      await axios.post(`${API}/orchestrator/run-auto`, { job_id: jid }, { headers });
      setGoal('');
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Build failed');
      setStage('failed');
    } finally {
      setLoading(false);
    }
  }, [goal, loading, token, setSearchParams]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  // Recent tasks for sidebar
  const recentTasks = tasks.slice(0, 8);

  const isRunning = stage === 'running' || loading;
  const currentStepName = steps?.find(s => s.status === 'running' || s.status === 'verifying')?.agent_name || '';

  return (
    <div className="manus-shell">

      {/* ── Top bar ── */}
      <div className="manus-topbar">
        <div className="manus-topbar-left">
          <button className="manus-compose-tool-btn" style={{marginRight:4}} onClick={() => navigate('/app')}>
            ☰
          </button>
          <div className="manus-topbar-brand">
            <span>Crucible</span>
          </div>
          <div className="manus-model-badge">
            <span>Auto</span>
            <IcoChevron open={false} />
          </div>
        </div>
        <div className="manus-topbar-right">
          {isRunning && (
            <div style={{display:'flex',alignItems:'center',gap:6,fontSize:13,color:'#3b82f6'}}>
              <div className="manus-thinking-dot" />
              {currentStepName || 'Running…'}
            </div>
          )}
          <button className="manus-btn-ghost"><IcoShare /> Share</button>
          <button className="manus-btn-publish"><IcoPublish /> Publish</button>
          {activeJobId && <button className="manus-btn-ghost" onClick={() => { setActiveJobId(null); setStage('input'); setGoal(''); setSearchParams({}); }}>✕</button>}
        </div>
      </div>

      <div className="manus-body">

        {/* ── Left sidebar ── */}
        <div className="manus-sidebar">
          <div className="manus-sidebar-top">
            <button className="manus-new-task-btn" onClick={() => { setActiveJobId(null); setStage('input'); setGoal(''); setSearchParams({}); }}>
              <IcoPlus /> New task
            </button>
          </div>
          <div className="manus-sidebar-nav">
            <Link to="/app" className="manus-nav-item"><IcoHome /> Home</Link>
            <Link to="/app/agents" className="manus-nav-item"><IcoAgent /> Agents</Link>
            <button className="manus-nav-item"><IcoSearch /> Search</button>
            <Link to="/app/learn" className="manus-nav-item"><IcoLibrary /> Library</Link>
          </div>
          <div className="manus-sidebar-section">
            <span>History</span>
          </div>
          <div className="manus-task-list">
            {recentTasks.map((t, i) => (
              <button key={t.id || i} className={`manus-task-item ${t.id === taskIdFromUrl ? 'active' : ''}`}
                onClick={() => { setSearchParams({ taskId: t.id }); }}>
                <div className={`manus-task-dot ${t.status === 'completed' ? 'done' : t.status === 'failed' ? 'failed' : t.status === 'running' ? 'running' : 'idle'}`} />
                <span className="manus-task-label">{t.name || t.prompt?.slice(0, 60)}</span>
              </button>
            ))}
          </div>
        </div>

        {/* ── Center chat ── */}
        <div className="manus-center">
          <div className="manus-chat-scroll" ref={chatScrollRef}>
            <div className="manus-chat-inner">

              {/* User's goal */}
              {(job?.goal || goal) && (
                <div className="manus-msg-user">{job?.goal || goal}</div>
              )}

              {/* Agent response block */}
              {(isRunning || stage === 'completed' || stage === 'failed') && (
                <div className="manus-msg-agent">
                  <div className="manus-agent-avatar">C</div>
                  <div className="manus-agent-body">
                    <div className="manus-agent-name">
                      Crucible
                      <span className="manus-agent-tier">Auto</span>
                    </div>

                    {/* Brain narration */}
                    {isRunning && (
                      <div className="manus-agent-text" style={{marginBottom:8}}>
                        {completedSteps === 0
                          ? "I've reviewed your approved plan and I'm beginning execution: foundation and dependencies first, then features and quality checks in order."
                          : `Working on ${currentStepName || 'next steps'}…`}
                      </div>
                    )}
                    {stage === 'completed' && (
                      <div className="manus-agent-text" style={{marginBottom:8,color:'#10b981'}}>
                        ✓ Build complete — {completedSteps} steps finished. Preview is ready.
                      </div>
                    )}
                    {stage === 'failed' && (
                      <div className="manus-agent-text" style={{marginBottom:8,color:'#ef4444'}}>
                        Build encountered issues. Check the Failure tab for details.
                      </div>
                    )}

                    {/* Action chips */}
                    {recentChips.length > 0 && (
                      <div className="manus-action-chips">
                        {recentChips.map((chip, i) => (
                          <div key={i} className="manus-chip">
                            {chipIcon(chip.type)}
                            <span className="manus-chip-text">{chip.text}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Task progress card */}
                    {totalSteps > 0 && (
                      <div className="manus-task-card">
                        <div className="manus-task-card-header" onClick={() => setTaskCardOpen(o => !o)}>
                          <span>{job?.goal?.slice(0, 50) || 'Build progress'}</span>
                          <div className="manus-task-card-meta">
                            <span>{completedSteps}/{totalSteps}</span>
                            <IcoChevron open={taskCardOpen} />
                          </div>
                        </div>
                        {taskCardOpen && (
                          <div className="manus-task-progress-list">
                            {Object.entries(stepGroups).map(([group, groupSteps]) => (
                              <div key={group}>
                                <div style={{fontSize:11,color:'#999',fontWeight:600,textTransform:'uppercase',letterSpacing:'0.05em',padding:'4px 0 2px',cursor:'pointer'}}
                                  onClick={() => setExpandedGroups(eg => ({...eg, [group]: !eg[group]}))}>
                                  {group} ({groupSteps.filter(s=>s.status==='completed').length}/{groupSteps.length})
                                </div>
                                {(expandedGroups[group] !== false) && groupSteps.map(s => (
                                  <div key={s.id} className="manus-task-progress-item">
                                    {stepIcon(s.status)}
                                    <span style={{color: s.status==='running'?'#3b82f6': s.status==='failed'?'#ef4444':'inherit', fontWeight: s.status==='running'?500:'inherit'}}>
                                      {s.agent_name || s.step_key}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Thinking indicator */}
                    {isRunning && (
                      <div className="manus-thinking" style={{marginTop:8}}>
                        <div className="manus-thinking-dot" />
                        {currentStepName ? `Working on ${currentStepName}` : 'Thinking…'}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Empty state */}
              {stage === 'input' && !job && (
                <div style={{textAlign:'center',color:'#999',padding:'40px 0',fontSize:14}}>
                  Describe what you want to build below
                </div>
              )}

            </div>
          </div>

          {/* ── Compose bar ── */}
          <div className="manus-composer">
            <div className="manus-compose-box">
              <textarea
                ref={textareaRef}
                className="manus-compose-textarea"
                placeholder={isRunning ? "Steer anytime — Enter sends on this same run." : "Describe what to build…"}
                value={goal}
                onChange={e => setGoal(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
              />
              <div className="manus-compose-actions">
                <div className="manus-compose-tools">
                  <button className="manus-compose-tool-btn" title="Attach"><IcoAttach /></button>
                  <button className="manus-compose-tool-btn" title="Screen"><IcoScreen /></button>
                  <button className="manus-compose-tool-btn" title="Mic"><IcoMic /></button>
                </div>
                <button className="manus-compose-send" onClick={handleSend} disabled={!goal.trim() || loading}>
                  {loading ? '…' : <IcoSend />}
                </button>
              </div>
            </div>
            {error && <div style={{color:'#ef4444',fontSize:12,textAlign:'center',marginTop:6}}>{error}</div>}
          </div>
        </div>

        {/* ── Right pane ── */}
        <div className="manus-right">
          <div className="manus-right-tabs">
            {['preview','proof','explorer','replay','failure','timeline','code'].map(p => (
              <button key={p} className={`manus-right-tab ${activePane===p?'active':''}`}
                onClick={() => setActivePane(p)}>
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </button>
            ))}
          </div>

          <div className="manus-right-content">
            {activePane === 'preview' && (
              <div style={{display:'flex',flexDirection:'column',flex:1,overflow:'hidden',position:'relative'}}>
                <div className="manus-preview-bar">
                  <div className="manus-preview-nav-btns">
                    <button className="manus-preview-nav-btn">←</button>
                    <button className="manus-preview-nav-btn">→</button>
                    <button className="manus-preview-nav-btn">↻</button>
                  </div>
                  <div className="manus-preview-url-bar">
                    <span>🏠</span>
                    <span>{previewUrl ? previewUrl.replace(/^https?:\/\//, '') : '/'}</span>
                  </div>
                  {previewUrl && <button className="manus-preview-nav-btn" onClick={() => window.open(previewUrl, '_blank')}>↗</button>}
                </div>
                {previewUrl ? (
                  <iframe
                    className="manus-preview-frame"
                    src={previewUrl}
                    title="Live Preview"
                    sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
                  />
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
                      {isRunning ? 'Crucible is building your app. Hang tight!' : 'Start a build to see preview'}
                      {isRunning && <div style={{marginTop:4,fontSize:12}}>Preview will appear when ready</div>}
                    </div>
                  </div>
                )}
                {isRunning && previewUrl && (
                  <div className="manus-preview-taking-shape">Taking shape</div>
                )}
              </div>
            )}

            {activePane === 'code' && (
              <div className="manus-code-split">
                <div className="manus-file-tree">
                  {Object.keys(sandpackFiles || {}).length > 0
                    ? Object.keys(sandpackFiles).map(path => (
                        <div key={path} className={`manus-file-item ${activeFile===path?'active':''}`}
                          onClick={() => setActiveFile(path)}>
                          <span>📄</span>{path.split('/').pop()}
                        </div>
                      ))
                    : <div style={{padding:'8px 12px',fontSize:12,color:'#999'}}>No files yet</div>
                  }
                </div>
                <div style={{flex:1,overflow:'auto',background:'#1e1e1e',padding:'12px 16px'}}>
                  <pre style={{color:'#d4d4d4',fontSize:12,margin:0,fontFamily:'monospace',whiteSpace:'pre-wrap'}}>
                    {activeFile && sandpackFiles[activeFile]?.code || '// Select a file'}
                  </pre>
                </div>
              </div>
            )}

            {activePane === 'proof' && (
              <div style={{padding:16,overflow:'auto',flex:1}}>
                <div style={{fontSize:13,fontWeight:600,marginBottom:12}}>Proof</div>
                {proof?.total_proof_items > 0
                  ? <div style={{fontSize:13,color:'#10b981'}}>✓ {proof.total_proof_items} proof items</div>
                  : <div style={{fontSize:13,color:'#999'}}>No proof items yet</div>
                }
              </div>
            )}

            {activePane === 'failure' && (
              <div style={{padding:16,overflow:'auto',flex:1}}>
                <div style={{fontSize:13,fontWeight:600,marginBottom:12}}>Failures</div>
                {steps?.filter(s => s.status === 'failed').map(s => (
                  <div key={s.id} style={{background:'#fef2f2',border:'1px solid #fecaca',borderRadius:8,padding:'10px 12px',marginBottom:8}}>
                    <div style={{fontSize:13,fontWeight:500,color:'#dc2626'}}>{s.agent_name || s.step_key}</div>
                    <div style={{fontSize:12,color:'#666',marginTop:4}}>{s.error_message || 'Unknown error'}</div>
                  </div>
                ))}
                {!steps?.some(s => s.status === 'failed') && (
                  <div style={{fontSize:13,color:'#999'}}>No failures</div>
                )}
              </div>
            )}

            {activePane === 'timeline' && (
              <div style={{padding:16,overflow:'auto',flex:1}}>
                <div style={{fontSize:13,fontWeight:600,marginBottom:12}}>Timeline</div>
                {(steps || []).map((s, i) => (
                  <div key={s.id} style={{display:'flex',gap:10,marginBottom:10,alignItems:'flex-start'}}>
                    <div style={{width:2,background:'#e5e5e0',alignSelf:'stretch',marginTop:6,flexShrink:0}} />
                    <div>
                      <div style={{fontSize:12,fontWeight:500,color:'#1a1a1a'}}>{s.agent_name || s.step_key}</div>
                      <div style={{fontSize:11,color: s.status==='completed'?'#10b981': s.status==='failed'?'#ef4444':'#999'}}>
                        {s.status}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {(activePane === 'explorer' || activePane === 'replay') && (
              <div style={{padding:16,flex:1,display:'flex',alignItems:'center',justifyContent:'center',color:'#999',fontSize:13}}>
                {activePane.charAt(0).toUpperCase() + activePane.slice(1)} coming soon
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
