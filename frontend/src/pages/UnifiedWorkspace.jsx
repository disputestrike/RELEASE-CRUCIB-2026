/**
 * UnifiedWorkspace — default /app/workspace: Auto Runner shell + classic files/preview/build.
 * Tokens: ../styles/unified-workspace-tokens.css (scoped .uw-root).
 */
import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { useSearchParams, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import axios from 'axios';
import { useJobStream } from '../hooks/useJobStream';
import {
  Rocket,
  ChevronLeft,
  ChevronRight,
  Eye,
  ShieldCheck,
  Share2,
  FileArchive,
  Wrench,
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
import WorkspaceActivityFeed from '../components/AutoRunner/WorkspaceActivityFeed';
import WorkspaceUserChat from '../components/AutoRunner/WorkspaceUserChat';
import WorkspaceStatusDock from '../components/AutoRunner/WorkspaceStatusDock';
import BrainGuidancePanel from '../components/AutoRunner/BrainGuidancePanel';
import SystemStatusHUD from '../components/AutoRunner/SystemStatusHUD';
import WorkspaceSystemsPanel from '../components/AutoRunner/WorkspaceSystemsPanel';
import PreviewPanel from '../components/AutoRunner/PreviewPanel';
import ResizableDivider from '../components/AutoRunner/ResizableDivider';
import WorkspaceFileTree from '../components/AutoRunner/WorkspaceFileTree';
import WorkspaceFileViewer from '../components/AutoRunner/WorkspaceFileViewer';
import { DEFAULT_FILES } from '../components/workspace/constants';
import { computeSandpackFilesWithMeta, computeSandpackDeps } from '../workspace/sandpackFromFiles';
import {
  normalizeWorkspacePath,
  fetchAllWorkspaceFilePaths,
  buildTraceIndexFromEvents,
  guessViewerKind,
  toEditorPath,
} from '../workspace/workspaceFileUtils';
import { WorkspaceNavProvider } from '../workspace/WorkspaceNavContext';
import { detailToString, formatWorkspaceBuildError } from '../workspace/workspaceErrorUtils';
import { API_BASE } from '../apiBase';
import { useTaskStore } from '../stores/useTaskStore';
import {
  deriveRightRailSubtitle,
  isWorkspaceLiveBuildPhase,
  selectWorkspacePreviewStatus,
} from '../workspace/workspaceLiveUi';
import '../styles/unified-workspace-tokens.css';
import './AutoRunnerPage.css';
import '../components/workspace-v4/workspace-v4.css';

const RIGHT_ORDER = ['preview', 'proof', 'systems', 'explorer', 'replay', 'failure', 'timeline', 'code'];

function sanitizePane(raw) {
  const pane = String(raw || '').trim().toLowerCase();
  return RIGHT_ORDER.includes(pane) ? pane : 'preview';
}

function formatCoachReply(guidance) {
  if (!guidance || typeof guidance !== 'object') return '';
  const lines = [];
  if (guidance.headline) lines.push(String(guidance.headline));
  if (guidance.summary && guidance.summary !== guidance.headline) lines.push(String(guidance.summary));
  const steps = Array.isArray(guidance.next_steps) ? guidance.next_steps : [];
  if (steps.length) lines.push(steps.map((s, i) => `${i + 1}. ${s}`).join('\n'));
  return lines.join('\n\n').trim();
}

export default function UnifiedWorkspace() {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const projectIdFromUrl = searchParams.get('projectId');
  const taskIdFromUrl = searchParams.get('taskId');
  const jobIdFromUrl = searchParams.get('jobId');
  const { token, user, loading: authLoading, ensureGuest } = useAuth();
  const { updateTask, tasks } = useTaskStore();
  const sessionBootstrapRef = useRef(false);
  const processedLocationHandoffRef = useRef(new Set());
  /** Same-tick handoff goal when router state + session can race with the autostart effect. */
  const handoffQueuedAutostartRef = useRef(null);
  const taskPromptHydratedForIdRef = useRef(null);
  /** Prevents double plan/run when URL params change during dashboard handoff autostart. */
  const workspaceAutostartDoneRef = useRef(false);
  /** Open Preview once per job when a run is in motion (does not fight tab changes on re-render). */
  const autoPreviewOnceForJobRef = useRef(null);

  useEffect(() => {
    if (authLoading) return;
    if (token) {
      sessionBootstrapRef.current = false;
      return;
    }
    if (sessionBootstrapRef.current) return;
    sessionBootstrapRef.current = true;
    ensureGuest().catch(() => {
      sessionBootstrapRef.current = false;
    });
  }, [authLoading, token, ensureGuest]);

  const [healthMs, setHealthMs] = useState(null);
  useEffect(() => {
    let alive = true;
    const ping = async () => {
      const t0 = performance.now();
      try {
        await axios.get(`${API_BASE}/health`, { timeout: 8000 });
        if (alive) setHealthMs(Math.round(performance.now() - t0));
      } catch {
        if (alive) setHealthMs(null);
      }
    };
    ping();
    const id = setInterval(ping, 10000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const [uxMode, setUxMode] = useState(() => localStorage.getItem('crucibai_ux_mode') || 'pro');
  const toggleUxMode = (m) => {
    setUxMode(m);
    localStorage.setItem('crucibai_ux_mode', m);
  };

  const [rightCollapsed, setRightCollapsed] = useState(() => localStorage.getItem('crucibai_right_collapsed') === 'true');
  useEffect(() => {
    localStorage.setItem('crucibai_right_collapsed', rightCollapsed);
  }, [rightCollapsed]);

  const [rightWidth, setRightWidth] = useState(() => parseInt(localStorage.getItem('crucibai_right_width') || '440', 10));
  useEffect(() => {
    localStorage.setItem('crucibai_right_width', String(rightWidth));
  }, [rightWidth]);

  const handleResize = useCallback((delta) => {
    setRightWidth((w) => {
      const minRight = 200;
      const minCenter = 280;
      const div = 10;
      const inner = typeof window !== 'undefined' ? window.innerWidth : 1440;
      const sidebarReserve = 300;
      const maxRight = Math.max(minRight, inner - sidebarReserve - div - minCenter);
      return Math.min(maxRight, Math.max(minRight, w + delta));
    });
  }, []);
  const handleResetWidth = useCallback(() => setRightWidth(440), []);

  const [editorColorMode, setEditorColorMode] = useState(() =>
    typeof document !== 'undefined' && document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark',
  );
  useEffect(() => {
    const read = () =>
      setEditorColorMode(document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark');
    read();
    const obs = new MutationObserver(read);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => obs.disconnect();
  }, []);

  const [goal, setGoal] = useState('');
  const [plan, setPlan] = useState(null);
  const [capabilityNotice, setCapabilityNotice] = useState([]);
  const [buildTargets, setBuildTargets] = useState([]);
  const [buildTarget, setBuildTarget] = useState('vite_react');
  const [buildTargetMeta, setBuildTargetMeta] = useState(null);
  const [estimate, setEstimate] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [stage, setStage] = useState('input');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  /** Full server / API text for expandable “Technical details” under GoalComposer. */
  const [errorRaw, setErrorRaw] = useState(null);
  /** User prompts sent from the composer — shown as bubbles above activity (input stays empty after send). */
  const [userChatMessages, setUserChatMessages] = useState([]);
  const [activePane, setActivePane] = useState(() => sanitizePane(searchParams.get('panel')));
  const [failedStep, setFailedStep] = useState(null);
  useEffect(() => {
    if (!API) return;
    axios
      .get(`${API}/orchestrator/build-targets`)
      .then((r) => {
        const list = r.data?.targets || [];
        setBuildTargets(list);
      })
      .catch(() => setBuildTargets([]));
  }, []);

  useEffect(() => {
    const id = plan?.crucib_build_target;
    if (!id || !buildTargets.length) return;
    const row = buildTargets.find((t) => t.id === id);
    if (row) {
      setBuildTarget(id);
      setBuildTargetMeta(row);
    }
  }, [plan, buildTargets]);

  useEffect(() => {
    if (!jobIdFromUrl || !token || !API) return;
    if (jobIdFromUrl === jobId) return;
    const headers = { Authorization: `Bearer ${token}` };
    axios
      .get(`${API}/jobs/${jobIdFromUrl}`, { headers })
      .then(async (r) => {
        const j = r.data?.job ?? r.data;
        if (!j || typeof j !== 'object') return;
        setJobId(jobIdFromUrl);
        if (j.goal) {
          const g = String(j.goal).trim();
          if (g) {
            const hid = `hydrate-${jobIdFromUrl}`;
            setUserChatMessages((prev) => {
              if (prev.some((m) => m.id === hid)) return prev;
              return [...prev, { id: hid, body: g, jobId: jobIdFromUrl, pendingBind: false, ts: Date.now() }];
            });
          }
        }
        setGoal('');
        const st = j.status;
        if (st === 'planned') {
          try {
            const pr = await axios.get(`${API}/jobs/${jobIdFromUrl}/plan-draft`, { headers, timeout: 15000 });
            if (pr.data?.plan) setPlan(pr.data.plan);
          } catch {
            setPlan(null);
          }
          setStage('plan');
        } else if (['approved', 'queued', 'running', 'blocked'].includes(st)) {
          setStage('running');
        } else {
          setStage('completed');
        }
      })
      .catch(() => {});
  }, [jobIdFromUrl, token, jobId]);

  const [files, setFiles] = useState(DEFAULT_FILES);
  /** API workspace selection (posix, no leading slash) — tree + viewer source of truth. */
  const [activeWsPath, setActiveWsPath] = useState('');
  const [treeRevealTick, setTreeRevealTick] = useState(0);
  const [filesReadyKey, setFilesReadyKey] = useState('uw-default');
  const [wsPaths, setWsPaths] = useState([]);
  const [wsFileCache, setWsFileCache] = useState({});
  const [workspacePullKey, setWorkspacePullKey] = useState(0);
  const [zipBusy, setZipBusy] = useState(false);

  const effectiveJobId = jobId || jobIdFromUrl;
  const effectiveProjectId = projectIdFromUrl;

  const {
    job,
    steps,
    events,
    milestoneBatch,
    repairQueueLen,
    latestFailure,
    latestFailedStep,
    isCompleted,
    connectionMode,
    refresh,
    taskProgress,
    actionChips,
    controller,
  } = useJobStream(effectiveJobId, token);

  const buildDisplayTitle = useMemo(() => {
    if (job?.name) return job.name;
    if (job?.goal) return job.goal;
    if (plan?.goal) return plan.goal;
    if (goal) return goal;
    return 'Untitled build';
  }, [job?.name, job?.goal, plan?.goal, goal]);

  const clearBuildError = useCallback(() => {
    setError(null);
    setErrorRaw(null);
  }, []);

  const applyBuildError = useCallback((msg) => {
    const fmt = formatWorkspaceBuildError(msg);
    setError(fmt.message);
    setErrorRaw(fmt.raw);
  }, []);

  const lastPulledStepCount = useRef(0);
  useEffect(() => {
    if (!effectiveJobId || !token || !API) return;
    const headers = { Authorization: `Bearer ${token}` };
    fetchAllWorkspaceFilePaths(API, effectiveJobId, headers)
      .then((paths) => setWsPaths(paths))
      .catch(() => setWsPaths([]));
  }, [effectiveJobId, token, API, workspacePullKey]);

  const traceByPath = useMemo(() => buildTraceIndexFromEvents(events), [events]);

  const loadWorkspaceFileBody = useCallback(
    async (key) => {
      if (!effectiveJobId || !token || !API) return;
      const headers = { Authorization: `Bearer ${token}` };
      const textBase = `${API}/jobs/${encodeURIComponent(effectiveJobId)}/workspace/file`;
      const rawBase = `${API}/jobs/${encodeURIComponent(effectiveJobId)}/workspace/file/raw`;
      const isBinary = guessViewerKind(key) === 'binary';
      if (isBinary) {
        try {
          const r = await fetch(`${rawBase}?path=${encodeURIComponent(key)}`, { headers });
          if (!r.ok) throw new Error((await r.text()) || r.statusText);
          const blob = await r.blob();
          const blobUrl = URL.createObjectURL(blob);
          const isImg = (r.headers.get('content-type') || '').startsWith('image/');
          setWsFileCache((prev) => ({
            ...prev,
            [key]: { status: isImg ? 'image' : 'binary', blobUrl, contentType: r.headers.get('content-type') },
          }));
        } catch (e) {
          setWsFileCache((prev) => ({
            ...prev,
            [key]: { status: 'error', error: e instanceof Error ? e.message : String(e) },
          }));
        }
        return;
      }
      try {
        const r = await axios.get(textBase, { params: { path: key }, headers, timeout: 15000 });
        const text = r.data?.content ?? '';
        const pathReturned = normalizeWorkspacePath(r.data?.path || key);
        const md = pathReturned.endsWith('.md') || key.endsWith('.md');
        setWsFileCache((prev) => ({
          ...prev,
          [pathReturned]: { status: md ? 'markdown' : 'text', text },
        }));
      } catch (e) {
        if (e.response?.status === 400) {
          try {
            const r = await fetch(`${rawBase}?path=${encodeURIComponent(key)}`, { headers });
            if (!r.ok) throw new Error((await r.text()) || r.statusText);
            const blob = await r.blob();
            const blobUrl = URL.createObjectURL(blob);
            const isImg = (r.headers.get('content-type') || '').startsWith('image/');
            setWsFileCache((prev) => ({
              ...prev,
              [key]: { status: isImg ? 'image' : 'binary', blobUrl, contentType: r.headers.get('content-type') },
            }));
          } catch (e2) {
            setWsFileCache((prev) => ({
              ...prev,
              [key]: { status: 'error', error: e2 instanceof Error ? e2.message : String(e2) },
            }));
          }
        } else {
          setWsFileCache((prev) => ({
            ...prev,
            [key]: { status: 'error', error: e instanceof Error ? e.message : String(e) },
          }));
        }
      }
    },
    [API, token, effectiveJobId, effectiveProjectId],
  );

  const openWorkspacePath = useCallback((rawPath) => {
    const key = normalizeWorkspacePath(rawPath);
    setActivePane('code');
    setRightCollapsed(false);
    if (!key) return;
    setActiveWsPath(key);
    setTreeRevealTick((t) => t + 1);
  }, []);

  /** AgentMonitor → workspace: Link with `state: { openWorkspacePath }` (posix path). */
  useEffect(() => {
    if (authLoading || !token) return;
    const st = location.state;
    if (!st || typeof st.openWorkspacePath !== 'string') return;
    const raw = st.openWorkspacePath.trim();
    if (!raw) return;
    const key = `openWsPath_${location.key || 'k'}_${raw}`;
    if (processedLocationHandoffRef.current.has(key)) return;
    processedLocationHandoffRef.current.add(key);
    openWorkspacePath(raw);
    navigate(
      { pathname: location.pathname, search: location.search || '' },
      { replace: true, state: {} },
    );
  }, [authLoading, token, location.key, location.state, location.pathname, location.search, navigate, openWorkspacePath]);

  useEffect(() => {
    if (!activeWsPath) return;
    loadWorkspaceFileBody(activeWsPath);
  }, [activeWsPath, workspacePullKey, loadWorkspaceFileBody]);

  useEffect(() => {
    const last = events.length ? events[events.length - 1] : null;
    const t = last?.type || last?.event_type;
    if (t !== 'dag_node_completed') return undefined;
    const id = setTimeout(() => setWorkspacePullKey((k) => k + 1), 600);
    return () => clearTimeout(id);
  }, [events]);

  // Wire brain_guidance SSE events → live chat feed so the brain talks during builds
  const lastBrainEventIdRef = useRef(null);
  useEffect(() => {
    if (!events.length) return;
    const last = events[events.length - 1];
    const t = last?.type || last?.event_type;
    if (t !== 'brain_guidance') return;
    // dedupe — only push if this is a new event
    const evId = last?.id || last?.event_id || JSON.stringify(last).slice(0, 80);
    if (lastBrainEventIdRef.current === evId) return;
    lastBrainEventIdRef.current = evId;
    // parse payload
    const p = last?.payload && typeof last.payload === 'object'
      ? last.payload
      : (() => { try { return JSON.parse(last?.payload_json || '{}'); } catch { return {}; } })();
    const headline = p?.headline || '';
    const summary = p?.summary || '';
    const body = [headline, summary].filter(Boolean).join(' — ');
    if (!body.trim()) return;
    const msgId = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `brain_${Date.now()}`;
    setUserChatMessages((prev) => [
      ...prev,
      { id: msgId, body, role: 'assistant', jobId: effectiveJobId, pendingBind: false, ts: Date.now() },
    ]);
  }, [events, effectiveJobId]);

  const prevJobStatusRef = useRef(null);
  useEffect(() => {
    prevJobStatusRef.current = null;
  }, [effectiveJobId]);
  useEffect(() => {
    const st = job?.status;
    if (st === 'failed' && prevJobStatusRef.current !== 'failed') {
      setWorkspacePullKey((k) => k + 1);
    }
    prevJobStatusRef.current = st;
  }, [job?.status]);

  const reloadWorkspaceFromServer = useCallback(() => {
    lastPulledStepCount.current = 0;
    setWorkspacePullKey((k) => k + 1);
  }, []);

  const handleDownloadWorkspaceZip = useCallback(async () => {
    if (!effectiveJobId || !token || !API) return;
    setZipBusy(true);
    try {
      const res = await fetch(
        `${API}/jobs/${encodeURIComponent(effectiveJobId)}/export/full.zip?profile=handoff`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!res.ok) {
        const errText = await res.text().catch(() => '');
        throw new Error(errText || res.statusText || `HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `crucibai-job-${effectiveJobId}-handoff.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : 'Download failed');
    } finally {
      setZipBusy(false);
    }
  }, [effectiveJobId, token, API]);

  const workspaceNavValue = useMemo(
    () => ({
      openWorkspacePath,
      traceForPath: (p) => traceByPath[normalizeWorkspacePath(p)] || null,
    }),
    [openWorkspacePath, traceByPath],
  );

  const sendInFlightRef = useRef(false);

  const handleApprove = async () => {
    const jid = jobId || jobIdFromUrl;
    if (!jid) {
      setError('No job to run — generate a plan first (or open a valid job link).');
      setErrorRaw(null);
      return;
    }
    setLoading(true);
    setStage('running');
    clearBuildError();
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.post(`${API}/orchestrator/run-auto`, { job_id: jid }, { headers, timeout: 15000 });
    } catch (e) {
      const d = e.response?.data?.detail;
      let msg = 'Failed to start job.';
      if (d && typeof d === 'object' && !Array.isArray(d)) {
        if (Array.isArray(d.issues)) msg = d.issues.join(' ');
        else if (d.message) msg = String(d.message);
        else if (d.error === 'runtime_unsatisfied') {
          msg = 'Runtime check failed: install Python and Node.js on the host running the API, then retry.';
        }
      } else if (typeof d === 'string') msg = d;
      else if (Array.isArray(d)) msg = d.map((x) => (typeof x === 'string' ? x : JSON.stringify(x))).join('; ');
      applyBuildError(msg);
      setStage('plan');
    } finally {
      setLoading(false);
    }
  };

  /**
   * POST /orchestrator/plan then POST /orchestrator/run-auto for a concrete goal string
   * (used by composer Send and by dashboard handoff auto-start).
   */
  const runNewPlanAndAuto = useCallback(
    async (goalText) => {
      const trimmed = (goalText || '').trim();
      // Do not gate on authLoading here: handoff/autostart can race a one-frame loading flip while token is valid.
      if (!trimmed || !token || !API) return;
      if (sendInFlightRef.current) return;
      sendInFlightRef.current = true;
      setLoading(true);
      clearBuildError();
      const headers = { Authorization: `Bearer ${token}` };
      const planBody = { goal: trimmed, mode: 'auto', build_target: null };
      const pid = (projectIdFromUrl || '').trim();
      if (pid) planBody.project_id = pid;
      try {
        const res = await axios.post(`${API}/orchestrator/plan`, planBody, { headers, timeout: 30000 });
        const newJid = res.data.job_id;
        setPlan(res.data.plan);
        setCapabilityNotice(Array.isArray(res.data.capability_notice) ? res.data.capability_notice : []);
        if (res.data.build_target_meta) setBuildTargetMeta(res.data.build_target_meta);
        else if (res.data.build_target && buildTargets.length) {
          setBuildTargetMeta(buildTargets.find((t) => t.id === res.data.build_target) || null);
        }
        if (res.data.build_target) setBuildTarget(res.data.build_target);
        setEstimate(res.data.estimate);
        setJobId(newJid);
        setSearchParams(
          (prev) => {
            const next = new URLSearchParams(prev);
            if (newJid) next.set('jobId', newJid);
            return next;
          },
          { replace: true },
        );

        try {
          await axios.post(`${API}/orchestrator/run-auto`, { job_id: newJid }, { headers, timeout: 15000 });
          setStage('running');
        } catch (e) {
          const d = e.response?.data?.detail;
          let msg = 'Failed to start job.';
          if (d && typeof d === 'object' && !Array.isArray(d)) {
            if (Array.isArray(d.issues)) msg = d.issues.join(' ');
            else if (d.message) msg = String(d.message);
            else if (d.error === 'runtime_unsatisfied') {
              msg = 'Runtime check failed: install Python and Node.js on the host running the API, then retry.';
            }
          } else if (typeof d === 'string') msg = d;
          else if (Array.isArray(d)) msg = d.map((x) => (typeof x === 'string' ? x : JSON.stringify(x))).join('; ');
          applyBuildError(msg);
          setStage('plan');
        }
      } catch (e) {
        applyBuildError(
          detailToString(e.response?.data?.detail) || e.message || 'Failed to generate plan.',
        );
      } finally {
        setLoading(false);
        sendInFlightRef.current = false;
      }
    },
    [API, token, buildTargets, projectIdFromUrl, setSearchParams, clearBuildError, applyBuildError],
  );

  /**
   * Phase 1: one Send = POST /orchestrator/plan then POST /orchestrator/run-auto (same job).
   */
  const handleComposerSend = async (text) => {
    const trimmed = (text || '').trim();
    if (!trimmed) return;
    setGoal('');
    appendUserChat(trimmed);
    await runNewPlanAndAuto(trimmed);
  };

  const appendUserChat = useCallback((body) => {
    const msgId = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `user_${Date.now()}`;
    setUserChatMessages((prev) => [
      ...prev,
      { id: msgId, body, role: 'user', jobId: effectiveJobId, pendingBind: true, ts: Date.now() },
    ]);
  }, [effectiveJobId]);

  const locSearch = location.search;
  useEffect(() => {
    if (authLoading || !token || !API) return;
    const sp = new URLSearchParams(locSearch);
    const st = location.state;
    const prompt = (st?.initialPrompt || sp.get('prompt') || '').trim();
    const autoStart = st?.autoStart || sp.get('autoStart') === '1';
    const handoffKey = st?.handoffNonce ? `state:${st.handoffNonce}` : `query:${prompt}:${autoStart}`;

    if (!prompt) return;
    if (processedLocationHandoffRef.current.has(handoffKey)) return;
    processedLocationHandoffRef.current.add(handoffKey);

    (async () => {
      if (autoStart) {
        handoffQueuedAutostartRef.current = prompt;
        await runNewPlanAndAuto(prompt);
      } else {
        setGoal(prompt);
      }
      navigate(
        { pathname: location.pathname, search: location.search || '' },
        { replace: true, state: {} },
      );
    })();
  }, [token, authLoading, API, runNewPlanAndAuto, appendUserChat, locSearch, taskIdFromUrl, tasks, setSearchParams]);

  /** Sidebar reopen: `?taskId=` with no `jobId` — show stored build prompt in the composer (no auto-run). */
  useEffect(() => {
    if (!taskIdFromUrl) {
      taskPromptHydratedForIdRef.current = null;
      return;
    }
    if (taskIdFromUrl === taskPromptHydratedForIdRef.current) return;
    const task = tasks.find((t) => t.id === taskIdFromUrl);
    if (!task?.prompt?.trim() || task.type !== 'build' || task.status !== 'pending') return;
    
    // If we have a goal or chat, don't overwrite
    if (goal.trim() || userChatMessages.length > 0) return;
    
    taskPromptHydratedForIdRef.current = taskIdFromUrl;
    setGoal(String(task.prompt).trim());
    
    // If task is marked for autostart, trigger it
    if (task.autoStart && !workspaceAutostartDoneRef.current && !jobIdFromUrl) {
      workspaceAutostartDoneRef.current = true;
      runNewPlanAndAuto(task.prompt);
    }
  }, [taskIdFromUrl, jobIdFromUrl, tasks, goal, userChatMessages.length, runNewPlanAndAuto]);

  const handleCancelJob = async () => {
    const jid = jobId || jobIdFromUrl;
    if (!jid) return;
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.post(`${API}/jobs/${jid}/cancel`, {}, { headers, timeout: 10000 });
    } catch (_) {
      /* ignore */
    }
  };

  const handleResumeJob = async () => {
    const jid = jobId || jobIdFromUrl;
    if (!jid) return;
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.post(`${API}/jobs/${jid}/resume`, {}, { headers, timeout: 10000 });
    } catch (_) {
      /* ignore */
    }
  };

  const handleRetryStep = async (step) => {
    const jid = jobId || jobIdFromUrl;
    if (!jid || !step) return;
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.post(`${API}/jobs/${encodeURIComponent(jid)}/retry-step/${encodeURIComponent(step.id)}`, {}, { headers, timeout: 15000 });
      setFailedStep(null);
      if (job?.status === 'failed') {
        await axios.post(`${API}/jobs/${encodeURIComponent(jid)}/resume`, {}, { headers, timeout: 15000 });
        setStage('running');
      }
      refresh();
    } catch (_) {
      /* ignore */
    }
  };

  const handleReset = () => {
    setGoal('');
    setPlan(null);
    setCapabilityNotice([]);
    setBuildTarget('vite_react');
    setBuildTargetMeta(null);
    setEstimate(null);
    setJobId(null);
    setStage('input');
    clearBuildError();
    setUserChatMessages([]);
    setFailedStep(null);
    setActiveWsPath('');
    setWsPaths([]);
    setWsFileCache((prev) => {
      Object.values(prev).forEach((e) => {
        if (e?.blobUrl) {
          try {
            URL.revokeObjectURL(e.blobUrl);
          } catch (_) {
            /* ignore */
          }
        }
      });
      return {};
    });
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.delete('jobId');
        return next;
      },
      { replace: true },
    );
  };

  const handleCodeChange = (value) => {
    if (!activeWsPath) return;
    const fk = toEditorPath(activeWsPath);
    setFiles((prev) => ({ ...prev, [fk]: { code: value } }));
    setWsFileCache((prev) => {
      const k = normalizeWorkspacePath(activeWsPath);
      const e = prev[k];
      if (!e || (e.status !== 'text' && e.status !== 'markdown')) return prev;
      return { ...prev, [k]: { ...e, text: value } };
    });
  };

  const jumpStepToCode = useCallback(
    (step) => {
      let raw =
        (step?.output_files && step.output_files[0]) ||
        (step?.diagnosis && step.diagnosis.specific_file) ||
        '';
      if (typeof raw === 'string') {
        const m = raw.match(/^(.+\.[a-z0-9]+):(\d+)$/i);
        if (m) [, raw] = m;
      }
      openWorkspacePath(raw);
    },
    [openWorkspacePath],
  );

  const activeAgentCount = [...new Set(steps.filter((s) => s.status === 'running').map((s) => s.agent_name))].length;

  const visibleRightPanes = RIGHT_ORDER.filter((p) => {
    if (uxMode === 'beginner' && (p === 'systems' || p === 'explorer' || p === 'replay' || p === 'code')) return false;
    return true;
  });

  useEffect(() => {
    const paneFromUrl = sanitizePane(searchParams.get('panel'));
    setActivePane((cur) => (cur === paneFromUrl ? cur : paneFromUrl));
  }, [searchParams]);

  useEffect(() => {
    if (visibleRightPanes.includes(activePane)) return;
    setActivePane(visibleRightPanes[0] || 'preview');
  }, [visibleRightPanes, activePane]);

  // Re-hydrate data-bearing panes when the user switches into them — prevents
  // empty Proof/Failure/Timeline/Preview tabs when tab was switched mid-stream.
  useEffect(() => {
    if (!effectiveJobId) return;
    if (activePane === 'proof') {
      try { refresh && refresh(); } catch (_) { /* ignore */ }
    } else if (activePane === 'failure') {
      try { refresh && refresh(); } catch (_) { /* ignore */ }
    } else if (activePane === 'timeline') {
      try { refresh && refresh(); } catch (_) { /* ignore */ }
    } else if (activePane === 'preview') {
      try { refresh && refresh(); } catch (_) { /* ignore */ }
      try { setWorkspacePullKey((k) => k + 1); } catch (_) { /* ignore */ }
    }
  }, [activePane, effectiveJobId, refresh]);

  const failureStep = failedStep || latestFailedStep;

  const previewBlockedDetail = useMemo(() => {
    const fromStep = failureStep?.error_message || failureStep?.step_key;
    if (latestFailure && typeof latestFailure === 'object') {
      const issues = Array.isArray(latestFailure.issues) ? latestFailure.issues : [];
      const first = issues[0] ? String(issues[0]).trim().slice(0, 260) : '';
      const err = latestFailure.error_message ? String(latestFailure.error_message).trim().slice(0, 260) : '';
      const sk = latestFailure.step_key ? `${latestFailure.step_key}: ` : '';
      const reason = latestFailure.failure_reason ? ` (${latestFailure.failure_reason})` : '';
      const core = first || err;
      if (core) return `${sk}${core}${reason}`.trim();
    }
    if (fromStep) return String(fromStep);
    return 'Build stopped — open Failure or steer below, then Resume.';
  }, [latestFailure, failureStep]);

  const previewStatus = selectWorkspacePreviewStatus({
    jobStatus: job?.status,
    stage,
    isCompleted,
  });
  const previewUrl =
    job?.dev_server_url ||
    job?.preview_url ||
    job?.published_url ||
    job?.deploy_url ||
    (isCompleted && effectiveJobId ? `/published/${encodeURIComponent(effectiveJobId)}/` : null);

  const proofItemCount = useMemo(() => {
    if (!proof) return 0;
    if (typeof proof.total_proof_items === 'number') return proof.total_proof_items;
    return Object.values(proof.bundle || {}).reduce((s, arr) => s + (arr?.length || 0), 0);
  }, [proof]);

  const rightRailSubtitle = useMemo(() => deriveRightRailSubtitle(events, steps), [events, steps]);

  useEffect(() => {
    if (!effectiveJobId || isCompleted) return;
    const js = job?.status;
    if (js === 'failed' || js === 'cancelled' || js === 'blocked') return;
    if (!isWorkspaceLiveBuildPhase({ jobStatus: js, stage })) return;
    if (autoPreviewOnceForJobRef.current === effectiveJobId) return;
    autoPreviewOnceForJobRef.current = effectiveJobId;
    setActivePane('preview');
    setRightCollapsed(false);
  }, [effectiveJobId, isCompleted, job?.status, stage]);

  return (
    <WorkspaceNavProvider value={workspaceNavValue}>
    <div className={`uw-root arp-root arp-ux-${uxMode}`} data-testid="unified-workspace-root">
      <div className="arp-layout arp-layout--no-inner-rail">
        <div className="arp-center-pane arp-center-pane--composer-bottom">
          <div className="arp-center-toolbar uw-center-headline">
            <div className="uw-center-headline-brand" aria-label="Crucible product version">
              <span className="uw-center-headline-name">Crucible</span>
              <span className="uw-center-headline-version">1.0</span>
            </div>
            <div className="uw-center-headline-actions">
              {(effectiveProjectId || effectiveJobId) && token && (
                <button
                  type="button"
                  className="arp-topbar-btn"
                  style={{ fontSize: 11 }}
                  title="Reload files from server"
                  onClick={reloadWorkspaceFromServer}
                >
                  Sync
                </button>
              )}
              <AutoRunnerPanel
                mode="auto"
                jobId={effectiveJobId}
                jobStatus={job?.status}
                onRun={() => handleApprove()}
                onPause={handleCancelJob}
                onResume={handleResumeJob}
                onCancel={handleCancelJob}
                budget={estimate}
                showRunButton={false}
                showModeSelector={false}
              />
            </div>
          </div>

          <div className="arp-center-pane-scroll">
            {(effectiveJobId || effectiveProjectId) && (
              <div className="uw-build-identity" aria-label="Active build">
                <div className="uw-build-identity-title">{buildDisplayTitle}</div>
              </div>
            )}
            <BrainGuidancePanel
              jobId={effectiveJobId}
              workspaceStage={stage}
              jobHydrating={Boolean(effectiveJobId && !job && loading)}
              events={events}
              jobStatus={job?.status}
              failureStep={failureStep}
              proof={proof}
              latestFailure={latestFailure}
              milestoneBatch={milestoneBatch}
              repairQueueLen={repairQueueLen}
              steps={steps}
              taskProgress={taskProgress}
              actionChips={actionChips}
              controller={controller}
            />
            {stage === 'input' && (
              <WorkspaceActivityFeed
                stage={stage}
                plan={plan}
                job={job}
                steps={steps}
                events={events}
                effectiveJobId={effectiveJobId}
                loading={loading}
                connectionMode={connectionMode}
                fallbackGoal={goal}
                hideGoalEcho={userChatMessages.length > 0}
                openWorkspacePath={openWorkspacePath}
                taskProgress={taskProgress}
                actionChips={actionChips}
                controller={controller}
              />
            )}

            {stage === 'plan' && plan && (
              <PlanApproval
                plan={plan}
                estimate={estimate}
                capabilityNotice={capabilityNotice}
                buildTargetMeta={buildTargetMeta}
                onApprove={() => handleApprove()}
                onRunAuto={() => handleApprove()}
                onEdit={() => setStage('input')}
                loading={loading}
              />
            )}

            {(stage === 'running' ||
              stage === 'completed' ||
              stage === 'plan' ||
              stage === 'input') && (
              <ExecutionTimeline
                jobId={effectiveJobId}
                steps={steps}
                events={events}
                onJumpToCode={jumpStepToCode}
                onRetryStep={handleRetryStep}
              />
            )}

            {isCompleted && (
              <BuildCompletionCard
                job={job}
                onDownload={handleDownloadWorkspaceZip}
                zipBusy={zipBusy}
              />
            )}
          </div>

          <div className="arp-center-composer">
            <GoalComposer
              goal={goal}
              setGoal={setGoal}
              onSend={handleComposerSend}
              loading={loading}
              stage={stage}
              jobStatus={job?.status}
            />
          </div>
        </div>

        <ResizableDivider onResize={handleResize} onReset={handleResetWidth} />

        <div
          className={`arp-right-pane ${rightCollapsed ? 'collapsed' : ''}`}
          style={{ width: rightCollapsed ? 0 : rightWidth }}
        >
          <div className="arp-right-pane-inner">
            <div className="arp-right-pane-header">
              <div className="arp-right-pane-tabs">
                {visibleRightPanes.map((p) => (
                  <button
                    key={p}
                    className={`arp-right-pane-tab ${activePane === p ? 'active' : ''}`}
                    onClick={() => setActivePane(p)}
                  >
                    {p === 'preview' && <Eye size={14} />}
                    {p === 'proof' && <ShieldCheck size={14} />}
                    {p === 'systems' && <Wrench size={14} />}
                    {p === 'explorer' && <FileArchive size={14} />}
                    <span className="arp-right-pane-tab-label">{p}</span>
                  </button>
                ))}
              </div>
              <button
                className="arp-right-pane-toggle"
                onClick={() => setRightCollapsed(!rightCollapsed)}
              >
                {rightCollapsed ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
              </button>
            </div>

            <div className="arp-right-pane-content">
              {activePane === 'preview' && (
                <PreviewPanel
                  url={previewUrl}
                  status={previewStatus}
                  blockedDetail={previewBlockedDetail}
                  onRetry={() => handleApprove()}
                  taskProgress={taskProgress}
                  actionChips={actionChips}
                  controller={controller}
                />
              )}
              {activePane === 'proof' && <ProofPanel jobId={effectiveJobId} proof={proof} />}
              {activePane === 'systems' && (
                <WorkspaceSystemsPanel
                  jobId={effectiveJobId}
                  events={events}
                  steps={steps}
                  taskProgress={taskProgress}
                  actionChips={actionChips}
                  controller={controller}
                />
              )}
              {activePane === 'explorer' && (
                <div className="uw-explorer-layout">
                  <WorkspaceFileTree
                    paths={wsPaths}
                    activePath={activeWsPath}
                    onSelect={openWorkspacePath}
                    revealTick={treeRevealTick}
                  />
                  <div className="uw-explorer-viewer">
                    <WorkspaceFileViewer
                      path={activeWsPath}
                      cache={wsFileCache}
                      onCodeChange={handleCodeChange}
                      colorMode={editorColorMode}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <WorkspaceStatusDock
        jobId={effectiveJobId}
        job={job}
        steps={steps}
        stage={stage}
        events={events}
        connectionMode={connectionMode}
        loading={loading}
        taskProgress={taskProgress}
        actionChips={actionChips}
        controller={controller}
      />

      <SystemStatusHUD healthMs={healthMs} />

      <FailureDrawer
        failure={failureStep}
        onRetry={() => handleRetryStep(failureStep)}
        onClose={() => setFailedStep(null)}
      />
    </div>
    </WorkspaceNavProvider>
  );
}
