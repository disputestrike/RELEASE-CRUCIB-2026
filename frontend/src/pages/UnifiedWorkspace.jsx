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

/** E6: map `workspace_transcript` events (user + steer `assistant`) → chat rows. Orchestrator `brain_guidance` still mapped separately. */
function jobTranscriptLinesFromEvents(events, jobId) {
  if (!Array.isArray(events) || !jobId) return [];
  const rows = [];
  for (const ev of events) {
    const t = ev?.type || ev?.event_type;
    if (t !== 'workspace_transcript') continue;
    const p = ev.payload && typeof ev.payload === 'object' ? ev.payload : {};
    const role = p.role === 'assistant' ? 'assistant' : 'user';
    const text = String(p.text || p.body || '').trim();
    if (!text) continue;
    const created = ev.created_at;
    let ts = Date.now();
    if (typeof created === 'number') {
      ts = created < 1e12 ? created * 1000 : created;
    } else if (created) {
      const d = new Date(created);
      if (!Number.isNaN(d.getTime())) ts = d.getTime();
    }
    rows.push({
      id: ev.id || `wt_${rows.length}_${ts}`,
      body: text,
      role,
      jobId,
      pendingBind: false,
      ts,
    });
  }
  rows.sort((a, b) => (a.ts || 0) - (b.ts || 0));
  return rows;
}

export default function UnifiedWorkspace() {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const projectIdFromUrl = searchParams.get('projectId');
  const taskIdFromUrl = searchParams.get('taskId');
  const jobIdFromUrl = searchParams.get('jobId');
  const { token, user, loading: authLoading, ensureGuest } = useAuth();
  const { updateTask, addTask, tasks } = useTaskStore();
  const sessionBootstrapRef = useRef(false);
  const processedLocationHandoffRef = useRef(new Set());
  /** Same-tick handoff goal when router state + session can race with the autostart effect. */
  const handoffQueuedAutostartRef = useRef(null);
  const taskPromptHydratedForIdRef = useRef(null);
  /** Prevents double plan/run when URL params change during dashboard handoff autostart. */
  const workspaceAutostartDoneRef = useRef(false);
  /** Open Preview once per job when a run is in motion (does not fight tab changes on re-render). */
  const autoPreviewOnceForJobRef = useRef(null);
  /** E6: one-shot rehydrate of user lines from `workspace_transcript` after GET /events. */
  const transcriptRebuiltForJobRef = useRef(null);

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
  const [failureCalloutDismissed, setFailureCalloutDismissed] = useState(false);
  const failureRefreshOnceRef = useRef(null);
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

  const [workspacePullKey, setWorkspacePullKey] = useState(0);
  const [wsPaths, setWsPaths] = useState([]);
  const [wsListLoading, setWsListLoading] = useState(false);
  const [wsFileCache, setWsFileCache] = useState({});

  // ── Job-switch state reset ──────────────────────────────────────────────────
  // When the user clicks a different job in the sidebar, jobIdFromUrl changes.
  // Without this reset, the old job's stage/messages/plan stay visible while the
  // new job loads, making the UI appear frozen or showing stale data.
  const prevJobIdFromUrlRef = useRef(null);
  useEffect(() => {
    if (!jobIdFromUrl) return;
    if (prevJobIdFromUrlRef.current === jobIdFromUrl) return;
    const isFirstLoad = prevJobIdFromUrlRef.current === null;
    prevJobIdFromUrlRef.current = jobIdFromUrl;
    if (isFirstLoad) return; // don't reset on initial page load
    // Clear all job-specific state so the new job hydrates cleanly
    setGoal('');
    setPlan(null);
    setCapabilityNotice([]);
    setEstimate(null);
    setStage('input');
    setLoading(false);
    setError(null);
    setErrorRaw(null);
    setUserChatMessages([]);
    setFailedStep(null);
    setFailureCalloutDismissed(false);
    failureRefreshOnceRef.current = null;
    setActiveWsPath('');
    setWsPaths([]);
    setWsFileCache((prev) => {
      Object.values(prev).forEach((e) => {
        if (e?.blobUrl) { try { URL.revokeObjectURL(e.blobUrl); } catch (_) {} }
      });
      return {};
    });
    // Reset autostart guards so the new job can trigger its own autostart if needed
    workspaceAutostartDoneRef.current = false;
    autoPreviewOnceForJobRef.current = null;
    transcriptRebuiltForJobRef.current = null;
  }, [jobIdFromUrl]); // eslint-disable-line react-hooks/exhaustive-deps
  const [zipBusy, setZipBusy] = useState(false);

  const sandpackMergeFiles = useMemo(() => {
    const base = { ...DEFAULT_FILES, ...files };
    Object.entries(wsFileCache).forEach(([k, ent]) => {
      if (ent?.status === 'text' || ent?.status === 'markdown') {
        const slashed = toEditorPath(k);
        base[slashed] = { code: ent.text ?? '' };
      }
    });
    return base;
  }, [files, wsFileCache]);

  const { sandpackFiles, isFallback: sandpackIsFallback } = useMemo(
    () => computeSandpackFilesWithMeta(sandpackMergeFiles),
    [sandpackMergeFiles],
  );
  const sandpackDeps = useMemo(() => computeSandpackDeps(sandpackMergeFiles), [sandpackMergeFiles]);

  /** URL wins so stream/poll start on first paint when opening ?jobId=… (state hydrates a tick later). */
  const effectiveJobId = jobIdFromUrl || jobId;

  useEffect(() => {
    transcriptRebuiltForJobRef.current = null;
  }, [effectiveJobId]);

  const { job, latestFailure, milestoneBatch, repairQueueLen, steps, events, proof, isConnected, connectionMode, refresh } = useJobStream(
    effectiveJobId,
    token,
  );

  const effectiveProjectId = job?.project_id || projectIdFromUrl || null;

  const persistTranscriptLine = useCallback(
    (role, body) => {
      const r = role === 'assistant' ? 'assistant' : 'user';
      const t = (body || '').trim();
      if (!t || !token || !API) return;
      const jid = jobId || jobIdFromUrl;
      if (!jid) return;
      const headers = { Authorization: `Bearer ${token}` };
      void axios
        .post(
          `${API}/jobs/${encodeURIComponent(jid)}/transcript`,
          { role: r, body: t },
          { headers, timeout: 15000 },
        )
        .catch(() => {});
    },
    [token, API, jobId, jobIdFromUrl],
  );

  const appendUserChat = useCallback(
    (body) => {
      const id =
        typeof crypto !== 'undefined' && crypto.randomUUID
          ? crypto.randomUUID()
          : `uw_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
      const jidAt = jobId || jobIdFromUrl || null;
      // Dedup: if the very last user message has the same body+jobId, skip —
      // this eliminates the duplicate-initial-prompt bug on first run.
      setUserChatMessages((prev) => {
        const msg = { id, body, role: 'user', jobId: jidAt, pendingBind: !jidAt, ts: Date.now() };
        const key = `${msg.role}:${msg.jobId || ''}:${msg.body}`;
        if (prev.some((m) => `${m.role || 'user'}:${m.jobId || ''}:${m.body}` === key)) return prev;
        persistTranscriptLine('user', body);
        return [...prev, msg];
      });
    },
    [jobId, jobIdFromUrl, persistTranscriptLine],
  );

  const clearBuildError = useCallback(() => {
    setError(null);
    setErrorRaw(null);
  }, []);

  const applyBuildError = useCallback((raw) => {
    let text = '';
    if (typeof raw === 'string') text = raw;
    else if (raw && typeof raw === 'object' && raw.response) {
      const d = raw.response.data?.detail;
      text = detailToString(d) || raw.message || 'Request failed';
    } else if (raw instanceof Error) text = raw.message || String(raw);
    else text = String(raw);
    const { friendly } = formatWorkspaceBuildError(text);
    setError(friendly);
    setErrorRaw(text);
  }, []);

  const buildDisplayTitle = useMemo(() => {
    const g = (job?.goal || '').trim();
    if (g) return g.split('\n')[0].slice(0, 120);
    const last = [...userChatMessages].reverse().find((m) => m.body);
    if (last?.body) return String(last.body).split('\n')[0].slice(0, 120);
    return 'Build';
  }, [job?.goal, userChatMessages]);

  useEffect(() => {
    if (!effectiveJobId) return;
    setUserChatMessages((prev) => {
      let changed = false;
      const next = prev.map((m) => {
        if (m.pendingBind && !m.jobId) {
          changed = true;
          return { ...m, jobId: effectiveJobId, pendingBind: false };
        }
        return m;
      });
      return changed ? next : prev;
    });
  }, [effectiveJobId]);

  useEffect(() => {
    if (!taskIdFromUrl || !effectiveJobId) return;
    const patch = { jobId: effectiveJobId };
    const st = job?.status;
    if (st === 'completed') patch.status = 'completed';
    else if (st === 'failed' || st === 'cancelled') patch.status = 'failed';
    else if (st) patch.status = 'running';
    updateTask(taskIdFromUrl, patch);
  }, [taskIdFromUrl, effectiveJobId, job?.status, updateTask]);

  const isCompleted = job?.status === 'completed';
  const latestFailedStep = steps.find((s) => s.status === 'failed' && !failedStep);

  const completedStepCount = useMemo(
    () => steps.filter((s) => s.status === 'completed').length,
    [steps],
  );
  const lastPulledStepCount = useRef(0);
  const completedWorkspaceBumpRef = useRef(null);
  useEffect(() => {
    lastPulledStepCount.current = 0;
    completedWorkspaceBumpRef.current = null;
  }, [jobId, jobIdFromUrl]);

  useEffect(() => {
    if (!token || !API) return;
    if (!effectiveJobId && !effectiveProjectId) return;
    if (completedStepCount === 0) return;
    if (completedStepCount === lastPulledStepCount.current) return;
    lastPulledStepCount.current = completedStepCount;
    setWorkspacePullKey((k) => k + 1);
  }, [completedStepCount, effectiveProjectId, effectiveJobId, token]);

  useEffect(() => {
    if (job?.status !== 'completed' || !effectiveJobId) return;
    if (completedWorkspaceBumpRef.current === effectiveJobId) return;
    completedWorkspaceBumpRef.current = effectiveJobId;
    setWorkspacePullKey((k) => k + 1);
  }, [job?.status, effectiveJobId]);

  useEffect(() => {
    if (isCompleted && stage === 'running') setStage('completed');
  }, [isCompleted, stage]);

  const handleShare = useCallback(() => {
    const url = window.location.href;
    if (navigator.share) {
      navigator.share({ title: 'CrucibAI Workspace', url }).catch(() => {
        navigator.clipboard.writeText(url);
      });
    } else {
      navigator.clipboard.writeText(url);
    }
  }, []);

  useEffect(() => {
    if (!taskIdFromUrl || !token || !API) return;
    axios
      .get(`${API}/tasks/${taskIdFromUrl}`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        const task = r.data?.task || r.data;
        const taskFiles = task?.files || task?.doc?.files;
        if (!taskFiles || typeof taskFiles !== 'object') return;
        const loaded = Object.entries(taskFiles).reduce((acc, [path, content]) => {
          const key = path.startsWith('/') ? path : `/${path}`;
          acc[key] = { code: typeof content === 'string' ? content : content?.code || '' };
          return acc;
        }, {});
        if (Object.keys(loaded).length > 0) {
          setFiles(loaded);
          const pick =
            Object.keys(loaded)
              .sort()
              .find((k) => /App\.(jsx?|tsx?)$/i.test(k)) || Object.keys(loaded).sort()[0];
          setActiveWsPath(normalizeWorkspacePath(pick));
          setTreeRevealTick((t) => t + 1);
          setFilesReadyKey(`task_${taskIdFromUrl}_${Date.now()}`);
        }
      })
      .catch(() => {});
  }, [taskIdFromUrl, token]);

  useEffect(() => {
    if (!token || !API) return;
    const useJobWs = Boolean(effectiveJobId);
    if (!useJobWs && !effectiveProjectId) return;
    const headers = { Authorization: `Bearer ${token}` };
    const listUrl = useJobWs
      ? `${API}/jobs/${effectiveJobId}/workspace/files`
      : `${API}/projects/${effectiveProjectId}/workspace/files`;
    let cancelled = false;
    setWsListLoading(true);
    fetchAllWorkspaceFilePaths(listUrl, headers)
      .then((paths) => {
        if (cancelled) return;
        setWsPaths(paths);
        setFilesReadyKey(
          useJobWs ? `job_${effectiveJobId}_${Date.now()}` : `proj_${effectiveProjectId}_${Date.now()}`,
        );
        setActiveWsPath((cur) => {
          if (cur && paths.includes(cur)) return cur;
          const pick =
            paths.find((p) => /(^|\/)App\.(jsx?|tsx?)$/i.test(p)) ||
            paths.find((p) => /(^|\/)index\.(jsx?|tsx?)$/i.test(p)) ||
            paths[0] ||
            '';
          if (pick) setTreeRevealTick((t) => t + 1);
          return pick;
        });
      })
      .catch(() => {
        if (!cancelled) setWsPaths([]);
      })
      .finally(() => {
        if (!cancelled) setWsListLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [effectiveProjectId, effectiveJobId, token, workspacePullKey, API]);

  const traceByPath = useMemo(() => buildTraceIndexFromEvents(events, steps), [events, steps]);

  const loadWorkspaceFileBody = useCallback(
    async (posixPath) => {
      const key = normalizeWorkspacePath(posixPath);
      if (!key || !token || !API) return;
      const useJobWs = Boolean(effectiveJobId);
      if (!useJobWs && !effectiveProjectId) return;
      const headers = { Authorization: `Bearer ${token}` };
      const textBase = useJobWs
        ? `${API}/jobs/${effectiveJobId}/workspace/file`
        : `${API}/projects/${effectiveProjectId}/workspace/file`;
      const rawBase = useJobWs
        ? `${API}/jobs/${effectiveJobId}/workspace/file/raw`
        : `${API}/projects/${effectiveProjectId}/workspace/file/raw`;
      setWsFileCache((prev) => {
        const old = prev[key];
        if (old?.blobUrl) {
          try {
            URL.revokeObjectURL(old.blobUrl);
          } catch (_) {
            /* ignore */
          }
        }
        return { ...prev, [key]: { status: 'loading' } };
      });
      const kind = guessViewerKind(key);
      if (kind === 'image' || kind === 'binary') {
        try {
          const r = await fetch(`${rawBase}?path=${encodeURIComponent(key)}`, { headers });
          if (!r.ok) throw new Error((await r.text()) || r.statusText || `HTTP ${r.status}`);
          const blob = await r.blob();
          const blobUrl = URL.createObjectURL(blob);
          setWsFileCache((prev) => ({
            ...prev,
            [key]: { status: kind === 'image' ? 'image' : 'binary', blobUrl, contentType: r.headers.get('content-type') },
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

  // E4: pull file list when steps start or files are written (orchestrator may have new paths)
  useEffect(() => {
    if (!events.length) return;
    const last = events[events.length - 1];
    const t = last?.type || last?.event_type;
    if (!['step_started', 'file_written', 'file_write', 'workspace_files_updated'].includes(t)) return undefined;
    const id = setTimeout(() => setWorkspacePullKey((k) => k + 1), 450);
    return () => clearTimeout(id);
  }, [events]);

  // E6: rehydrate user lines from `workspace_transcript` before brain_guidance adds assistant text.
  useEffect(() => {
    if (!effectiveJobId || !token || !API) return;
    if (transcriptRebuiltForJobRef.current === effectiveJobId) return;
    const hasT = events.some((e) => (e?.type || e?.event_type) === 'workspace_transcript');
    if (!hasT) return;
    const fromJob = jobTranscriptLinesFromEvents(events, effectiveJobId);
    setUserChatMessages((prev) => {
      if (prev.length > 0) {
        const onlyHydrate = prev.every((m) => String(m.id || '').startsWith('hydrate-'));
        if (!onlyHydrate) {
          transcriptRebuiltForJobRef.current = effectiveJobId;
          return prev;
        }
      }
      if (fromJob.length === 0) {
        transcriptRebuiltForJobRef.current = effectiveJobId;
        return prev;
      }
      transcriptRebuiltForJobRef.current = effectiveJobId;
      return fromJob;
    });
  }, [API, events, effectiveJobId, token]);

  // Wire brain_guidance SSE events → live chat feed so the brain talks during builds
  // PERSISTENCE FIX: Process ALL brain_guidance events (not just the last) so that
  // navigating back to a workspace restores the full conversation history.
  const processedBrainEventIdsRef = useRef(new Set());
  useEffect(() => {
    // Reset processed set when job changes
    processedBrainEventIdsRef.current = new Set();
  }, [effectiveJobId]);
  useEffect(() => {
    if (!events.length) return;
    const brainEvents = events.filter((e) => {
      const t = e?.type || e?.event_type;
      return t === 'brain_guidance';
    });
    if (!brainEvents.length) return;
    const newMessages = [];
    for (const ev of brainEvents) {
      const evId = ev?.id || ev?.event_id || JSON.stringify(ev).slice(0, 80);
      if (processedBrainEventIdsRef.current.has(evId)) continue;
      processedBrainEventIdsRef.current.add(evId);
      const p = ev?.payload && typeof ev.payload === 'object'
        ? ev.payload
        : (() => { try { return JSON.parse(ev?.payload_json || '{}'); } catch { return {}; } })();
      const headline = p?.headline || '';
      const summary = p?.summary || '';
      const body = [headline, summary].filter(Boolean).join(' — ');
      if (!body.trim()) continue;
      const msgId = typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `brain_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
      newMessages.push({ id: msgId, body, role: 'assistant', jobId: effectiveJobId, pendingBind: false, ts: ev?.created_at ? new Date(ev.created_at).getTime() : Date.now() });
    }
    if (newMessages.length > 0) {
      setUserChatMessages((prev) => {
        // Dedupe by body+role to avoid duplicates on re-render
        const existingKeys = new Set(prev.map((m) => `${m.role}:${m.body}`));
        const toAdd = newMessages.filter((m) => !existingKeys.has(`${m.role}:${m.body}`));
        if (!toAdd.length) return prev;
        return [...prev, ...toAdd].sort((a, b) => (a.ts || 0) - (b.ts || 0));
      });
    }
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
        const namePreview = (trimmed || '').slice(0, 120) || 'Build';
        let createdTaskId = null;
        if (taskIdFromUrl) {
          updateTask(taskIdFromUrl, { jobId: newJid, name: namePreview, status: 'running' });
        } else {
          createdTaskId = addTask({
            name: namePreview,
            prompt: trimmed,
            status: 'running',
            type: 'build',
            jobId: newJid,
            createdAt: Date.now(),
            ...(projectIdFromUrl ? { linkedProjectId: projectIdFromUrl } : {}),
          });
        }
        setSearchParams(
          (prev) => {
            const next = new URLSearchParams(prev);
            if (newJid) next.set('jobId', newJid);
            if (createdTaskId) next.set('taskId', createdTaskId);
            if (projectIdFromUrl) next.set('projectId', projectIdFromUrl);
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
    [API, token, buildTargets, projectIdFromUrl, taskIdFromUrl, addTask, updateTask, setSearchParams, clearBuildError, applyBuildError],
  );

  /**
   * Phase 1: one Send = POST /orchestrator/plan then POST /orchestrator/run-auto (same job).
   * If already in plan review (e.g. run-auto failed), Send only approves / starts run.
   */
  const handleSend = async () => {
    if (!goal.trim() || authLoading || !token || !API) return;
    if (sendInFlightRef.current) return;
    const submitted = goal.trim();
    const activeJobId = jobId || jobIdFromUrl;

    const failedOrBlocked = steps.some((s) => s.status === 'failed' || s.status === 'blocked');
    /** Steer+resume whenever the job is terminal/blocked or steps failed (do not require quiescent workers — UI can lag). */
    const steerMode =
      Boolean(activeJobId) &&
      (job?.status === 'failed' ||
        job?.status === 'cancelled' ||
        job?.status === 'blocked' ||
        (failedOrBlocked && job?.status !== 'queued'));

    const seeminglyBusy = isWorkspaceLiveBuildPhase({ jobStatus: job?.status, stage });

    if (steerMode) {
      appendUserChat(submitted);
      setGoal('');
      clearBuildError();
      sendInFlightRef.current = true;
      setLoading(true);
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const res = await axios.post(
          `${API}/jobs/${encodeURIComponent(activeJobId)}/steer`,
          { message: submitted, resume: true },
          { headers, timeout: 15000 },
        );
        clearBuildError();
        const coachText = formatCoachReply(res.data?.guidance);
        if (coachText) {
          const aid =
            typeof crypto !== 'undefined' && crypto.randomUUID
              ? crypto.randomUUID()
              : `uw_coach_${Date.now()}`;
          setUserChatMessages((prev) => [
            ...prev,
            {
              id: aid,
              body: coachText,
              role: 'assistant',
              jobId: activeJobId,
              pendingBind: false,
              ts: Date.now(),
            },
          ]);
          persistTranscriptLine('assistant', coachText);
        }
        setStage('running');
        refresh();
      } catch (e) {
        setGoal(submitted);
        applyBuildError(detailToString(e.response?.data?.detail) || e.message || 'Steer / resume failed.');
      } finally {
        setLoading(false);
        sendInFlightRef.current = false;
      }
      return;
    }

    if (stage === 'plan' && activeJobId) {
      appendUserChat(submitted);
      setGoal('');
      clearBuildError();
      sendInFlightRef.current = true;
      try {
        await handleApprove();
      } finally {
        sendInFlightRef.current = false;
      }
      return;
    }
    if (seeminglyBusy && !steerMode) {
      if (!activeJobId) {
        setError('A run is already in progress. Wait for it to finish, or open another task from the sidebar.');
        setErrorRaw(null);
        return;
      }
      appendUserChat(submitted);
      setGoal('');
      clearBuildError();
      sendInFlightRef.current = true;
      setLoading(true);
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const res = await axios.post(
          `${API}/jobs/${encodeURIComponent(activeJobId)}/steer`,
          { message: submitted, resume: false },
          { headers, timeout: 15000 },
        );
        clearBuildError();
        const coachText = formatCoachReply(res.data?.guidance);
        if (coachText) {
          const aid =
            typeof crypto !== 'undefined' && crypto.randomUUID
              ? crypto.randomUUID()
              : `uw_coach_${Date.now()}`;
          setUserChatMessages((prev) => {
            const msg = {
              id: aid,
              body: coachText,
              role: 'assistant',
              jobId: activeJobId,
              pendingBind: false,
              ts: Date.now(),
            };
            const key = `${msg.role}:${msg.jobId || ''}:${msg.body}`;
            if (prev.some((m) => `${m.role}:${m.jobId || ''}:${m.body}` === key)) return prev;
            persistTranscriptLine('assistant', coachText);
            return [...prev, msg];
          });
        }
        refresh();
      } catch (e) {
        setGoal(submitted);
        applyBuildError(detailToString(e.response?.data?.detail) || e.message || 'Could not send message.');
      } finally {
        setLoading(false);
        sendInFlightRef.current = false;
      }
      return;
    }

    appendUserChat(submitted);
    setGoal('');
    clearBuildError();
    await runNewPlanAndAuto(submitted);
  };

  /** Home / dashboard: consume navigate(..., { state: { initialPrompt, autoStart } }). */
  useEffect(() => {
    const st = location.state;
    if (!st || typeof st.initialPrompt !== 'string') return;
    const raw = st.initialPrompt.trim();
    if (!raw) return;
    const key =
      typeof st.handoffNonce === 'number'
        ? `h_${st.handoffNonce}`
        : `${location.key || 'nav'}_${raw.slice(0, 48)}_${st.autoStart ? '1' : '0'}`;
    if (processedLocationHandoffRef.current.has(key)) return;
    processedLocationHandoffRef.current.add(key);

    if (st.autoStart) {
      workspaceAutostartDoneRef.current = false;
      try {
        sessionStorage.setItem('crucibai_autostart_goal', raw);
      } catch (_) {
        /* private mode / quota */
      }
    }
    setGoal(raw);
    navigate(
      { pathname: location.pathname, search: location.search || '' },
      { replace: true, state: {} },
    );
  }, [location.key, location.state, location.pathname, location.search, navigate]);

  /** After guest/session token + API base are ready, start build from dashboard handoff (one shot). */
  const locSearch = location.search;
  useEffect(() => {
    if (workspaceAutostartDoneRef.current) return;
    if (authLoading || !token || !API) return;
    if (sendInFlightRef.current) return;

    const urlParams = new URLSearchParams(locSearch);
    const autoStartUrl = urlParams.get('autoStart') === '1';

    let goalText = '';
    try {
      const fromHandoff = (handoffQueuedAutostartRef.current || '').trim();
      if (fromHandoff) {
        goalText = fromHandoff;
        handoffQueuedAutostartRef.current = null;
        try {
          sessionStorage.removeItem('crucibai_autostart_goal');
        } catch (_) { void 0; }
      } else {
        goalText = (sessionStorage.getItem('crucibai_autostart_goal') || '').trim();
        if (goalText) {
          try {
            sessionStorage.removeItem('crucibai_autostart_goal');
          } catch (_) { void 0; }
        }
      }
    } catch (_) {
      return;
    }
    if (!goalText && autoStartUrl) {
      const pq = (urlParams.get('prompt') || '').trim();
      if (pq) goalText = pq;
    }
    if (!goalText && autoStartUrl && taskIdFromUrl) {
      const t = tasks.find((x) => x.id === taskIdFromUrl);
      const p = t?.prompt != null ? String(t.prompt).trim() : '';
      if (p && t?.type === 'build') goalText = p;
    }
    if (!goalText) return;

    workspaceAutostartDoneRef.current = true;

    if (autoStartUrl || urlParams.get('prompt')) {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.delete('autoStart');
          next.delete('prompt');
          return next;
        },
        { replace: true },
      );
    }

    void (async () => {
      if (sendInFlightRef.current) return;
      try {
        appendUserChat(goalText);
        setGoal('');
        await runNewPlanAndAuto(goalText);
      } catch (_) {
        /* runNewPlanAndAuto surfaces errors via applyBuildError */
      }
    })();
  }, [token, authLoading, API, runNewPlanAndAuto, appendUserChat, locSearch, taskIdFromUrl, tasks, setSearchParams]);

  /** Sidebar reopen: `?taskId=` with no `jobId` — show stored build prompt in the composer (no auto-run). */
  // PERSISTENCE FIX: When navigating back via sidebar (?taskId=... but no jobId),
  // restore the jobId from the task store so the workspace rehydrates the full job state.
  useEffect(() => {
    if (!taskIdFromUrl || jobIdFromUrl) return;
    const task = tasks.find((t) => t.id === taskIdFromUrl);
    if (!task) return;
    // If the task has a stored jobId (set when build was started), restore it to URL
    if (task.jobId) {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set('jobId', task.jobId);
          return next;
        },
        { replace: true },
      );
      return;
    }
    // No jobId stored — task is pending (never started). Show the prompt in composer.
    if (taskPromptHydratedForIdRef.current === taskIdFromUrl) return;
    if (!task?.prompt?.trim() || task.type !== 'build') return;
    try {
      if ((sessionStorage.getItem('crucibai_autostart_goal') || '').trim()) return;
    } catch (_) { void 0; }
    if (goal.trim() || userChatMessages.length > 0) return;
    taskPromptHydratedForIdRef.current = taskIdFromUrl;
    setGoal(String(task.prompt).trim());
  }, [taskIdFromUrl, jobIdFromUrl, tasks, goal, userChatMessages.length, setSearchParams]);

  const handleCancel = async () => {
    const jid = jobId || jobIdFromUrl;
    if (!jid) return;
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.post(`${API}/jobs/${jid}/cancel`, {}, { headers, timeout: 10000 });
    } catch (_) {
      /* ignore */
    }
  };

  const handleResume = async () => {
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
    transcriptRebuiltForJobRef.current = null;
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

  useEffect(() => {
    if (job?.status !== 'failed' || !effectiveJobId) return;
    if (failureRefreshOnceRef.current === effectiveJobId) return;
    failureRefreshOnceRef.current = effectiveJobId;
    try {
      refresh?.();
    } catch (_) {
      /* ignore */
    }
  }, [job?.status, effectiveJobId, refresh]);

  const showFailureCallout = useMemo(() => {
    if (job?.status !== 'failed' || failureCalloutDismissed) return false;
    if (activePane === 'failure') return false;
    const hasLatest =
      latestFailure &&
      typeof latestFailure === 'object' &&
      (Boolean(latestFailure.error_message) ||
        (Array.isArray(latestFailure.issues) && latestFailure.issues.length > 0) ||
        Boolean(latestFailure.step_key));
    return Boolean(failureStep || hasLatest);
  }, [job?.status, failureCalloutDismissed, activePane, failureStep, latestFailure]);

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
                onPause={handleCancel}
                onResume={handleResume}
                onCancel={handleCancel}
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
                {effectiveJobId && (
                  <p className="uw-build-identity-sub">
                    This run is authoritative: job stream, workspace files, proof, and preview—not Home chat.
                  </p>
                )}
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
            />
            {(stage === 'input' || effectiveJobId) && (
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
              job?.status === 'failed' ||
              job?.status === 'cancelled' ||
              job?.status === 'blocked') && (
              <div className="arp-execution-area">
                {isCompleted && (
                  <BuildCompletionCard
                    job={job}
                    proof={proof}
                    apiBase={API}
                    token={token}
                    onOpenPreview={() => {
                      setActivePane('preview');
                      setRightCollapsed(false);
                    }}
                    onOpenProof={() => {
                      setActivePane('proof');
                      setRightCollapsed(false);
                    }}
                    onOpenCode={() => {
                      setActivePane('code');
                      setRightCollapsed(false);
                    }}
                    onDeployAgain={handleReset}
                  />
                )}

                {failureStep && activePane !== 'failure' && (
                  <FailureDrawer
                    step={failureStep}
                    onRetry={handleRetryStep}
                    onOpenCode={jumpStepToCode}
                    onPauseJob={handleCancel}
                    onClose={() => setFailedStep(null)}
                    openWorkspacePath={openWorkspacePath}
                  />
                )}
              </div>
            )}
          </div>

          <div className="arp-center-pane-composer">
            {error ? (
              <div className="uw-workspace-error-banner">
                <div className="uw-workspace-error-friendly">{error}</div>
                {errorRaw ? (
                  <details className="uw-workspace-error-details">
                    <summary className="uw-workspace-error-details-summary">Technical details</summary>
                    <pre className="uw-workspace-error-details-pre">{errorRaw}</pre>
                  </details>
                ) : null}
              </div>
            ) : null}
            {showFailureCallout && (
              <div className="uw-failure-callout" role="status">
                <div className="uw-failure-callout-text">
                  <strong>Run failed</strong>
                  {previewBlockedDetail ? (
                    <span className="uw-failure-callout-detail">
                      {String(previewBlockedDetail).slice(0, 200)}
                      {String(previewBlockedDetail).length > 200 ? '…' : ''}
                    </span>
                  ) : null}
                </div>
                <div className="uw-failure-callout-actions">
                  <button
                    type="button"
                    className="arp-topbar-btn"
                    onClick={() => {
                      setActivePane('failure');
                      setRightCollapsed(false);
                    }}
                  >
                    Open Failure
                  </button>
                  <button type="button" className="arp-topbar-btn uw-failure-callout-dismiss" onClick={() => setFailureCalloutDismissed(true)}>
                    Dismiss
                  </button>
                </div>
              </div>
            )}
            <WorkspaceStatusDock
              jobId={effectiveJobId}
              job={job}
              steps={steps}
              stage={stage}
              events={events}
              connectionMode={connectionMode}
              loading={loading}
            />
            <WorkspaceUserChat messages={userChatMessages} />
            <GoalComposer
              goal={goal}
              onGoalChange={setGoal}
              onSubmit={handleSend}
              loading={loading}
              error={null}
              errorRaw={null}
              token={token}
              onEstimateReady={setEstimate}
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
              inputPlaceholder={
                job?.status === 'failed' || job?.status === 'cancelled'
                  ? 'Tell us the fix — Enter sends; we continue this same run.'
                  : job?.status === 'blocked'
                    ? 'What should we do next? Enter sends and moves us forward.'
                    : isWorkspaceLiveBuildPhase({ jobStatus: job?.status, stage })
                      ? 'Steer anytime — Enter sends on this same run.'
                      : 'Goal or follow-up — Enter to send, Shift+Enter for a new line.'
              }
              composerVariant="workspace"
            />
          </div>
        </div>

        {!rightCollapsed && <ResizableDivider onResize={handleResize} onDoubleClick={handleResetWidth} />}

        <div className={`arp-right-pane ${rightCollapsed ? 'collapsed' : ''}`} style={!rightCollapsed ? { width: `${rightWidth}px` } : undefined}>
          <div className="arp-right-toggle" onClick={() => setRightCollapsed(!rightCollapsed)}>
            {rightCollapsed ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
          </div>

          {!rightCollapsed && (
            <>
              <div className="arp-right-toolbar">
                <button
                  type="button"
                  className="arp-topbar-btn arp-toolbar-icon-btn"
                  title="Preview"
                  aria-label="Preview"
                  onClick={() => {
                    setActivePane('preview');
                    setRightCollapsed(false);
                  }}
                >
                  <Eye size={16} />
                </button>
                <button
                  type="button"
                  className="arp-topbar-btn arp-toolbar-icon-btn"
                  title="Deploy — open preview when ready"
                  aria-label="Deploy"
                  onClick={() => {
                    setActivePane('preview');
                    setRightCollapsed(false);
                  }}
                >
                  <Rocket size={16} />
                </button>
                <button
                  type="button"
                  className="arp-topbar-btn arp-toolbar-icon-btn"
                  title="Proof"
                  aria-label="Proof"
                  onClick={() => {
                    setActivePane('proof');
                    setRightCollapsed(false);
                  }}
                >
                  <ShieldCheck size={16} />
                </button>
                <button
                  type="button"
                  className="arp-topbar-btn arp-toolbar-icon-btn"
                  title="Systems"
                  aria-label="Systems"
                  onClick={() => {
                    setActivePane('systems');
                    setRightCollapsed(false);
                  }}
                >
                  <Wrench size={16} />
                </button>
                <button
                  type="button"
                  className="arp-topbar-btn arp-toolbar-icon-btn arp-topbar-btn-share"
                  title="Share — copy link"
                  aria-label="Share"
                  onClick={handleShare}
                >
                  <Share2 size={16} />
                </button>
                <div className="arp-mode-switch" title="Simple vs Dev — which tools show in the right pane">
                  <button type="button" className={`arp-ux-btn ${uxMode === 'beginner' ? 'active' : ''}`} onClick={() => toggleUxMode('beginner')}>
                    Simple
                  </button>
                  <button type="button" className={`arp-ux-btn ${uxMode === 'pro' ? 'active' : ''}`} onClick={() => toggleUxMode('pro')}>
                    Dev
                  </button>
                </div>
                <SystemStatusHUD
                  isConnected={isConnected}
                  connectionMode={connectionMode}
                  activeAgentCount={activeAgentCount}
                  jobStatus={job?.status}
                  steps={steps}
                  healthLatencyMs={healthMs}
                  eventCount={events.length}
                  proofItemCount={proofItemCount}
                />
              </div>
              <div className="arp-pane-tabs">
                {visibleRightPanes.map((p) => (
                  <button key={p} type="button" className={`arp-pane-tab ${activePane === p ? 'active' : ''}`} onClick={() => setActivePane(p)}>
                    {p.charAt(0).toUpperCase() + p.slice(1)}
                  </button>
                ))}
              </div>
              {rightRailSubtitle ? (
                <div className="arp-right-context-line" title={rightRailSubtitle}>
                  {rightRailSubtitle}
                </div>
              ) : null}

              <div className="arp-pane-content">
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
                    apiBase={API}
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
                  <ProofPanel
                    proof={proof}
                    jobId={effectiveJobId}
                    onExport={() => {}}
                    openWorkspacePath={openWorkspacePath}
                    milestoneBatch={milestoneBatch}
                    repairQueueLen={repairQueueLen}
                  />
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
                {activePane === 'failure' &&
                  (failureStep ? (
                    <FailureDrawer
                      step={failureStep}
                      onRetry={handleRetryStep}
                      onOpenCode={jumpStepToCode}
                      onPauseJob={handleCancel}
                      onClose={() => setFailedStep(null)}
                      openWorkspacePath={openWorkspacePath}
                    />
                  ) : (
                    <div className="arp-failure-empty">No failed steps — all green.</div>
                  ))}
                {activePane === 'code' && uxMode === 'pro' && (
                  <div className="code-pane-wrap">
                    <div className="code-pane-actions">
                      {effectiveJobId && token ? (
                        <button
                          type="button"
                          className="arp-topbar-btn"
                          style={{ fontSize: 11 }}
                          disabled={zipBusy}
                          title="Handoff ZIP (omits outputs/). Append ?profile=full to the export URL for the complete tree."
                          onClick={handleDownloadWorkspaceZip}
                        >
                          <FileArchive size={12} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                          {zipBusy ? 'ZIP…' : 'Workspace ZIP'}
                        </button>
                      ) : null}
                      <span title="From API file list">{wsPaths.length ? `${wsPaths.length} paths` : '—'}</span>
                    </div>
                    <div className="code-pane-main">
                      <WorkspaceFileTree
                        paths={wsPaths}
                        selectedPath={activeWsPath}
                        onSelectPath={(p) => {
                          setActiveWsPath(p);
                          setTreeRevealTick((t) => t + 1);
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
          )}
        </div>
      </div>
    </div>
    </WorkspaceNavProvider>
  );
}
