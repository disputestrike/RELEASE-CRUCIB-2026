/**
 * UnifiedWorkspace — default /app/workspace: Auto Runner shell + classic files/preview/build.
 * Tokens: ../styles/unified-workspace-tokens.css (scoped .uw-root).
 */
import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { useSearchParams, useLocation, useNavigate } from 'react-router-dom';
import { useAuth, API } from '../App';
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
import SystemStatusHUD from '../components/AutoRunner/SystemStatusHUD';
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
import { API_BASE } from '../apiBase';
import '../styles/unified-workspace-tokens.css';
import './AutoRunnerPage.css';

const RIGHT_ORDER = ['proof', 'explorer', 'replay', 'failure', 'preview', 'timeline', 'code'];

export default function UnifiedWorkspace() {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const projectIdFromUrl = searchParams.get('projectId');
  const taskIdFromUrl = searchParams.get('taskId');
  const jobIdFromUrl = searchParams.get('jobId');
  const { token, user, loading: authLoading, ensureGuest } = useAuth();
  const sessionBootstrapRef = useRef(false);
  const processedLocationHandoffRef = useRef(new Set());

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
  const [activePane, setActivePane] = useState('proof');
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
        if (j.goal) setGoal(j.goal);
        const st = j.status;
        if (st === 'planned') {
          try {
            const pr = await axios.get(`${API}/jobs/${jobIdFromUrl}/plan-draft`, { headers });
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
  const { job, steps, events, proof, isConnected, connectionMode, refresh } = useJobStream(effectiveJobId, token);

  const effectiveProjectId = job?.project_id || projectIdFromUrl || null;

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

  const previewStatus = isCompleted ? 'ready' : stage === 'running' || job?.status === 'running' ? 'building' : 'idle';
  const previewUrl =
    job?.preview_url ||
    job?.published_url ||
    job?.deploy_url ||
    (isCompleted && effectiveJobId ? `/published/${encodeURIComponent(effectiveJobId)}/` : null);

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
        const r = await axios.get(textBase, { params: { path: key }, headers });
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
      const res = await fetch(`${API}/jobs/${encodeURIComponent(effectiveJobId)}/export/full.zip`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const errText = await res.text().catch(() => '');
        throw new Error(errText || res.statusText || `HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `crucibai-job-${effectiveJobId}-full.zip`;
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
      return;
    }
    setLoading(true);
    setStage('running');
    setError(null);
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.post(`${API}/orchestrator/run-auto`, { job_id: jid }, { headers });
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
      setError(msg);
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
      if (!trimmed || authLoading || !token) return;
      if (sendInFlightRef.current) return;
      sendInFlightRef.current = true;
      setLoading(true);
      setError(null);
      const headers = { Authorization: `Bearer ${token}` };
      const planBody = { goal: trimmed, mode: 'auto', build_target: null };
      const pid = (projectIdFromUrl || '').trim();
      if (pid) planBody.project_id = pid;
      try {
        const res = await axios.post(`${API}/orchestrator/plan`, planBody, { headers });
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
          await axios.post(`${API}/orchestrator/run-auto`, { job_id: newJid }, { headers });
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
          setError(msg);
          setStage('plan');
        }
      } catch (e) {
        setError(e.response?.data?.detail || 'Failed to generate plan.');
      } finally {
        setLoading(false);
        sendInFlightRef.current = false;
      }
    },
    [API, token, authLoading, buildTargets, projectIdFromUrl, setSearchParams],
  );

  /**
   * Phase 1: one Send = POST /orchestrator/plan then POST /orchestrator/run-auto (same job).
   * If already in plan review (e.g. run-auto failed), Send only approves / starts run.
   */
  const handleSend = async () => {
    if (!goal.trim() || authLoading || !token) return;
    if (sendInFlightRef.current) return;
    const jidExisting = jobId || jobIdFromUrl;
    if (stage === 'plan' && jidExisting) {
      sendInFlightRef.current = true;
      try {
        await handleApprove();
      } finally {
        sendInFlightRef.current = false;
      }
      return;
    }
    if (stage === 'running' || job?.status === 'running' || job?.status === 'queued') {
      setError('A run is already in progress. Wait for it to finish, or open another task from the sidebar.');
      return;
    }

    await runNewPlanAndAuto(goal.trim());
  };

  /** Home / dashboard: consume navigate(..., { state: { initialPrompt, autoStart } }). */
  useEffect(() => {
    const st = location.state;
    if (!st || typeof st.initialPrompt !== 'string') return;
    const raw = st.initialPrompt.trim();
    if (!raw) return;
    const key = typeof location.key === 'string' && location.key ? location.key : `handoff_${raw.slice(0, 40)}`;
    if (processedLocationHandoffRef.current.has(key)) return;
    processedLocationHandoffRef.current.add(key);

    setGoal(raw);
    if (st.autoStart) {
      try {
        sessionStorage.setItem('crucibai_autostart_goal', raw);
      } catch (_) {
        /* private mode / quota */
      }
    }
    navigate(
      { pathname: location.pathname, search: location.search || '' },
      { replace: true, state: {} },
    );
  }, [location.key, location.state, location.pathname, location.search, navigate]);

  /** After guest/session token is ready, start build from dashboard handoff (one shot). */
  useEffect(() => {
    if (authLoading || !token) return;
    let goalText = '';
    try {
      goalText = (sessionStorage.getItem('crucibai_autostart_goal') || '').trim();
      if (goalText) sessionStorage.removeItem('crucibai_autostart_goal');
    } catch (_) {
      return;
    }
    if (!goalText) return;
    void runNewPlanAndAuto(goalText);
  }, [token, authLoading, runNewPlanAndAuto]);

  const handleCancel = async () => {
    const jid = jobId || jobIdFromUrl;
    if (!jid) return;
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.post(`${API}/jobs/${jid}/cancel`, {}, { headers });
    } catch (_) {
      /* ignore */
    }
  };

  const handleResume = async () => {
    const jid = jobId || jobIdFromUrl;
    if (!jid) return;
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.post(`${API}/jobs/${jid}/resume`, {}, { headers });
    } catch (_) {
      /* ignore */
    }
  };

  const handleRetryStep = async (step) => {
    const jid = jobId || jobIdFromUrl;
    if (!jid || !step) return;
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.post(`${API}/jobs/${jid}/retry-step/${step.id}`, {}, { headers });
      setFailedStep(null);
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
    setError(null);
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
    if (uxMode === 'beginner' && (p === 'explorer' || p === 'replay' || p === 'code')) return false;
    return true;
  });

  const failureStep = failedStep || latestFailedStep;

  const proofItemCount = useMemo(() => {
    if (!proof) return 0;
    if (typeof proof.total_proof_items === 'number') return proof.total_proof_items;
    return Object.values(proof.bundle || {}).reduce((s, arr) => s + (arr?.length || 0), 0);
  }, [proof]);

  return (
    <WorkspaceNavProvider value={workspaceNavValue}>
    <div className={`uw-root arp-root arp-ux-${uxMode}`} data-testid="unified-workspace-root">
      <div className="arp-layout arp-layout--no-inner-rail">
        <div className="arp-center-pane arp-center-pane--composer-bottom">
          <div className="arp-center-toolbar">
            <div className="arp-center-toolbar-left">
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
            </div>
            <div className="arp-center-toolbar-center">
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
              openWorkspacePath={openWorkspacePath}
            />

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

            {(stage === 'running' || stage === 'completed') && (
              <div className="arp-execution-area">
                {isCompleted && (
                  <BuildCompletionCard
                    job={job}
                    proof={proof}
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
            <GoalComposer
              goal={goal}
              onGoalChange={setGoal}
              onSubmit={handleSend}
              loading={loading}
              error={error}
              token={token}
              onEstimateReady={setEstimate}
              authLoading={authLoading}
              buildTarget={buildTarget}
              onBuildTargetChange={setBuildTarget}
              buildTargets={buildTargets}
              showExecutionTargets={false}
              showContinuation={false}
              showQuickChips={false}
              showComposerHeader={false}
              composerSubtitle={null}
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

              <div className="arp-pane-content">
                {activePane === 'preview' && (
                  <PreviewPanel
                    previewUrl={previewUrl}
                    status={previewStatus}
                    sandpackFiles={sandpackFiles}
                    sandpackDeps={sandpackDeps}
                    filesReadyKey={filesReadyKey}
                    sandpackIsFallback={sandpackIsFallback}
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
                  <ProofPanel proof={proof} jobId={effectiveJobId} onExport={() => {}} openWorkspacePath={openWorkspacePath} />
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
                          title="Download sealed workspace ZIP"
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
