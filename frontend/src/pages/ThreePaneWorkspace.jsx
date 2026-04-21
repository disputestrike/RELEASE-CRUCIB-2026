/**
 * ThreePaneWorkspace.jsx — CF33
 * APPROVED SHELL — DO NOT REPLACE. Features fuse INTO this file.
 *
 * LEFT: nav (from Layout/Sidebar)
 * MIDDLE: chat thread + composer + live activity feed
 * RIGHT: tabs — Preview, Plan, Code, Proof, Logs, Capability, Trust
 *   Each tab renders the real Manus-style panel (SystemStatusHUD in header,
 *   WorkspaceActivityFeed above composer, PreviewPanel / WorkspaceFileTree /
 *   BrainGuidancePanel / ProofPanel / FailureDrawer on the right).
 *
 * Backend contract (live):
 *   POST /api/orchestrator/plan     -> { job_id, plan, ... }
 *   POST /api/orchestrator/run-auto -> kicks off agents
 *   GET  /api/jobs/{id}/stream      -> SSE live step + event stream (via useJobStream)
 *   POST /api/ai/chat               -> real LLM chat (fallback for non-build msgs)
 */
import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Play, Square, Send,
} from 'lucide-react';
import VoiceRecorder from '../components/voice/VoiceRecorder';
import CompactButton from '../components/CompactButton';
import axios from 'axios';
import { API_BASE as API } from '../apiBase';
import { useAuth } from '../authContext';
import { useJobStream } from '../hooks/useJobStream';
import SystemStatusHUD from '../components/AutoRunner/SystemStatusHUD';
import WorkspaceActivityFeed from '../components/AutoRunner/WorkspaceActivityFeed';
import PreviewPanel from '../components/AutoRunner/PreviewPanel';
import WorkspaceFileTree from '../components/AutoRunner/WorkspaceFileTree';
import WorkspaceFileViewer from '../components/AutoRunner/WorkspaceFileViewer';
import BrainGuidancePanel from '../components/AutoRunner/BrainGuidancePanel';
import ProofPanel from '../components/AutoRunner/ProofPanel';
import FailureDrawer from '../components/AutoRunner/FailureDrawer';
import ExecutionTimeline from '../components/AutoRunner/ExecutionTimeline';
import '../styles/three_pane.css';

const EXECUTION_MODES = [
  { value: 'auto',         label: 'Auto' },
  { value: 'build',        label: 'Build' },
  { value: 'analyze_only', label: 'Analyze' },
  { value: 'plan_first',   label: 'Plan' },
  { value: 'migration',    label: 'Migrate' },
  { value: 'repair',       label: 'Repair' },
];

const DEV_TABS    = ['Preview', 'Plan', 'Code', 'Proof', 'Logs', 'Capability', 'Trust'];
const SIMPLE_TABS = ['Preview', 'Plan', 'Code', 'Proof'];

export default function ThreePaneWorkspace() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth() || {};
  const [mobileView, setMobileView] = useState('mid');
  const [workspaceMode, setWorkspaceMode] = useState(() => {
    if (user?.workspace_mode) return user.workspace_mode;
    return localStorage.getItem('crucibai_workspace_mode') || 'developer';
  });
  const [mode, setMode] = useState('auto');
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [running, setRunning] = useState(false);
  const [activeTab, setActiveTab] = useState('Preview');
  const [jobId, setJobId] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const textareaRef = useRef(null);

  const isDev = workspaceMode === 'developer';
  const tabs = isDev ? DEV_TABS : SIMPLE_TABS;

  useEffect(() => {
    if (!tabs.includes(activeTab)) setActiveTab(tabs[0]);
  }, [isDev, tabs, activeTab]);

  const toggleMode = (next) => {
    setWorkspaceMode(next);
    localStorage.setItem('crucibai_workspace_mode', next);
    const token = localStorage.getItem('token');
    if (token) {
      axios.post(`${API}/user/workspace-mode`, { mode: next }, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 5000,
      }).catch(() => {});
    }
  };

  // Live SSE stream for the active job — powers activity feed, system HUD, code tree, etc.
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
  const { job, steps, events, proof, isConnected, error: streamError } = useJobStream(jobId, { token });

  // Dashboard handoff: if we land here with state.initialPrompt, auto-fire.
  useEffect(() => {
    const st = location?.state;
    if (!st || typeof st.initialPrompt !== 'string') return;
    const trimmed = st.initialPrompt.trim();
    if (!trimmed) return;
    // Clear navigation state so a refresh doesn't re-fire.
    navigate(location.pathname + location.search, { replace: true, state: {} });
    setInput(trimmed);
    if (st.autoStart) {
      setTimeout(() => runGoal(trimmed), 40);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Live activity lines for the WorkspaceActivityFeed briefing card.
  const activityLines = useMemo(() => {
    const lines = [];
    if (job?.status) lines.push({ ts: Date.now(), text: `Job ${String(job.status).toLowerCase()}` });
    (events || []).slice(-6).forEach((e) => {
      const label = e.event_type || e.type || 'event';
      lines.push({ ts: e.created_at || Date.now(), text: `${label}: ${JSON.stringify(e.payload || {}).slice(0, 120)}` });
    });
    return lines;
  }, [job, events]);

  const runGoal = useCallback(async (goalText) => {
    const text = (goalText || input).trim();
    if (!text || running) return;
    setMessages((m) => [...m, { role: 'user', text, ts: Date.now() }]);
    setInput('');
    setRunning(true);
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    try {
      // 1. Plan
      const planRes = await axios.post(
        `${API}/orchestrator/plan`,
        { goal: text, mode: mode === 'auto' ? 'auto' : 'guided', build_target: null },
        { headers, timeout: 30000 }
      );
      const newJid = planRes?.data?.job_id;
      if (!newJid) throw new Error('no job_id returned from planner');
      setJobId(newJid);
      setMessages((m) => [...m, {
        role: 'assistant',
        text: `Plan ready (job ${newJid.slice(0, 8)}). Starting agents…`,
        ts: Date.now(),
        job_id: newJid,
      }]);
      // 2. Run
      await axios.post(`${API}/orchestrator/run-auto`, { job_id: newJid }, { headers, timeout: 15000 });
      setActiveTab('Preview');
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || 'Run failed';
      setMessages((m) => [...m, {
        role: 'assistant',
        text: `Could not start run: ${msg}. Falling back to chat…`,
        ts: Date.now(),
      }]);
      // Fallback: plain chat via /api/ai/chat so the user gets a reply.
      try {
        const chatRes = await axios.post(
          `${API}/ai/chat`,
          { message: text, model: 'auto' },
          { headers, timeout: 30000 }
        );
        const reply = chatRes?.data?.response || chatRes?.data?.message || 'No reply from model.';
        setMessages((m) => [...m, { role: 'assistant', text: reply, ts: Date.now() }]);
      } catch (err2) {
        setMessages((m) => [...m, {
          role: 'assistant',
          text: `Chat also failed: ${err2?.response?.status || 'offline'}`,
          ts: Date.now(),
        }]);
      }
    } finally {
      setRunning(false);
    }
  }, [input, mode, running, token]);

  const onRun = () => runGoal(input);

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onRun();
    }
  };

  // System HUD props (real numbers only).
  const hudProps = {
    connectionMode: isConnected ? 'connected' : (jobId ? 'connecting' : 'offline'),
    activeAgentCount: (steps || []).filter((s) => s.status === 'running').length,
    jobStatus: job?.status || 'idle',
    steps: steps || [],
    eventCount: (events || []).length,
    proofItemCount: proof?.total_proof_items || 0,
  };

  return (
    <div className="tp-root" data-testid="crucib-three-pane-root" data-mobile-view={mobileView}>
      {/* MIDDLE — chat */}
      <section className="tp-mid" role="main">
        <div className="tp-mid__header">
          <div className="tp-mid__title">Thread</div>
          <div className="tp-mode-toggle" role="tablist" aria-label="Workspace view mode" style={{ marginLeft: 12 }}>
            <button
              type="button"
              className={`tp-mode-btn${isDev ? ' active' : ''}`}
              onClick={() => toggleMode('developer')}
              data-testid="tp-mode-dev"
            >Developer</button>
            <button
              type="button"
              className={`tp-mode-btn${!isDev ? ' active' : ''}`}
              onClick={() => toggleMode('simple')}
              data-testid="tp-mode-simple"
            >Builder</button>
          </div>
          <select
            className="tp-mid__mode-select"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            aria-label="Execution mode"
          >
            {EXECUTION_MODES.map((m) => (<option key={m.value} value={m.value}>{m.label}</option>))}
          </select>
          <div style={{ marginLeft: 'auto' }}>
            <SystemStatusHUD {...hudProps} />
          </div>
        </div>
        <div className="tp-mid__messages" aria-live="polite">
          {messages.length === 0 ? (
            <div className="tp-empty-state">
              <strong>Start a thread</strong>
              Describe what you want to build, improve, or automate. Crucib will plan, pick agents from the DAG, and stream the run live into the right pane.
            </div>
          ) : messages.map((m, i) => (
            <div key={i} className={`tp-msg tp-msg--${m.role}`}>
              <div className="tp-msg__bubble">{m.text}</div>
            </div>
          ))}
        </div>
        {jobId && (
          <div style={{ padding: '8px 12px', borderTop: '1px solid var(--theme-border,#e4e4e7)' }}>
            <WorkspaceActivityFeed
              jobId={jobId}
              jobStatus={job?.status}
              steps={steps || []}
              events={events || []}
              activityLines={activityLines}
            />
          </div>
        )}
        <div className="tp-mid__composer-toolbar" style={{ display: 'flex', gap: 8, padding: '4px 8px', alignItems: 'center', borderTop: '1px solid var(--theme-border,#e4e4e7)' }}>
          <VoiceRecorder
            sessionId={'tp-' + (user?.id || 'anon')}
            onTranscript={(t) => setInput((prev) => (prev ? prev + ' ' : '') + t)}
          />
          <CompactButton
            sessionId={'tp-' + (user?.id || 'anon')}
            messages={messages.map((m) => ({ role: m.role, content: m.text }))}
            onCompacted={(res) => {
              setMessages((ms) => [...ms, { role: 'system', text: `Context compacted: ${res.tokens_before} -> ${res.tokens_after_target} tokens (ratio ${res.ratio?.toFixed?.(2) ?? res.ratio})` }]);
            }}
          />
        </div>
        <div className="tp-mid__composer">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Describe what you want to build… (Enter to send, Shift+Enter newline)"
            aria-label="Chat input"
          />
          <button
            type="button"
            className="tp-mid__run-btn"
            onClick={onRun}
            disabled={running || !input.trim()}
            data-testid="tp-run-btn"
          >
            {running ? <><Square size={14} /> Running</> : <><Send size={14} /> Send</>}
          </button>
        </div>
      </section>

      {/* RIGHT — everything else (real panels, not stubs) */}
      <aside className="tp-right" role="complementary">
        <div className="tp-right__tabs" role="tablist">
          {tabs.map((t) => (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={activeTab === t}
              className={`tp-right__tab${activeTab === t ? ' active' : ''}`}
              onClick={() => setActiveTab(t)}
            >{t}</button>
          ))}
        </div>
        <div className="tp-right__pane" role="tabpanel">
          <RightPaneContent
            tab={activeTab}
            isDev={isDev}
            jobId={jobId}
            job={job}
            steps={steps}
            events={events}
            proof={proof}
            streamError={streamError}
            isConnected={isConnected}
            selectedFile={selectedFile}
            setSelectedFile={setSelectedFile}
            token={token}
          />
        </div>
      </aside>

      {/* Mobile tab bar */}
      <div className="tp-mobile-tabbar">
        {['nav', 'mid', 'right'].map((v) => (
          <button key={v} className={mobileView === v ? 'active' : ''} onClick={() => setMobileView(v)}>
            {v === 'nav' ? 'Menu' : v === 'mid' ? 'Chat' : 'More'}
          </button>
        ))}
      </div>
    </div>
  );
}

function RightPaneContent({
  tab, isDev, jobId, job, steps, events, proof, streamError, isConnected,
  selectedFile, setSelectedFile, token,
}) {
  // No job yet → show a friendly empty state explaining what goes here.
  const noJobYet = !jobId;

  if (tab === 'Preview') {
    return (
      <div style={{ height: '100%' }}>
        {noJobYet ? (
          <EmptyState title="Live preview"
            body="The running app will render here. Send a goal in the chat and the preview will boot as soon as files are ready." />
        ) : (
          <PreviewPanel
            previewUrl={job?.preview_url || null}
            status={job?.status || 'idle'}
            sandpackFiles={null}
            sandpackDeps={null}
            filesReadyKey={`job-${jobId}`}
            blockedDetail={streamError || null}
            jobId={jobId}
            token={token}
            apiBase={API}
          />
        )}
      </div>
    );
  }

  if (tab === 'Plan') {
    return noJobYet
      ? <EmptyState title="Plan" body="The planner's proposed steps will appear here. The Brain explains its choices live as the run progresses." />
      : (
        <BrainGuidancePanel
          jobId={jobId}
          job={job}
          steps={steps || []}
          events={events || []}
        />
      );
  }

  if (tab === 'Code') {
    return noJobYet
      ? <EmptyState title="Code" body="Every file the agents write lives here, browsable + diffable. Click a file for the full contents." />
      : (
        <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 8, height: '100%' }}>
          <div style={{ borderRight: '1px solid var(--theme-border,#e4e4e7)', overflow: 'auto' }}>
            <WorkspaceFileTree
              jobId={jobId}
              token={token}
              apiBase={API}
              onSelect={setSelectedFile}
              selected={selectedFile}
            />
          </div>
          <div style={{ overflow: 'auto' }}>
            <WorkspaceFileViewer
              jobId={jobId}
              token={token}
              apiBase={API}
              file={selectedFile}
            />
          </div>
        </div>
      );
  }

  if (tab === 'Proof') {
    return noJobYet
      ? <EmptyState title="Proof" body="Trust bundle — tests, checks, verifications. Appears once the run produces evidence." />
      : <ProofPanel jobId={jobId} proof={proof} />;
  }

  if (tab === 'Logs') {
    return noJobYet
      ? <EmptyState title="Logs" body="Raw runtime events from the SSE stream. Developer view only." />
      : (
        <div style={{ height: '100%', overflow: 'auto' }}>
          <ExecutionTimeline job={job} steps={steps || []} events={events || []} />
        </div>
      );
  }

  if (tab === 'Capability') {
    return noJobYet
      ? <EmptyState title="Capability" body="Shows what this run needed (tools / skills / agents) vs what the current tier grants." />
      : (
        <div style={{ padding: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Capability</div>
          <div style={{ fontSize: 13, color: 'var(--theme-text-secondary,#52525b)' }}>
            Job <code>{jobId.slice(0, 8)}</code> · {isConnected ? 'live' : 'offline'} · {(steps || []).length} steps · {(events || []).length} events
          </div>
        </div>
      );
  }

  if (tab === 'Trust') {
    return noJobYet
      ? <EmptyState title="Trust" body="Proof score, test coverage, and reproducibility signals." />
      : (
        <div style={{ padding: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Trust</div>
          <div style={{ fontSize: 13, color: 'var(--theme-text-secondary,#52525b)' }}>
            {proof?.total_proof_items || 0} proof items · quality score {proof?.quality_score ?? 0}
          </div>
          <FailureDrawer jobId={jobId} job={job} events={events || []} />
        </div>
      );
  }

  return <EmptyState title="Pick a tab" body="" />;
}

function EmptyState({ title, body }) {
  return (
    <div style={{ padding: 16 }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--theme-text,#27272a)', marginBottom: 8 }}>{title}</div>
      <div className="tp-empty-state">
        <strong>Ready</strong>
        {body}
      </div>
    </div>
  );
}
