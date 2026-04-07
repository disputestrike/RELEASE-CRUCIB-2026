/**
 * UnifiedWorkspace — default /app/workspace: Auto Runner shell + classic files/preview/build.
 * Tokens: ../styles/unified-workspace-tokens.css (scoped .uw-root).
 */
import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { useAuth, API } from '../App';
import { useTaskStore } from '../stores/useTaskStore';
import axios from 'axios';
import Editor from '@monaco-editor/react';
import { useJobStream } from '../hooks/useJobStream';
import {
  PlayCircle,
  FolderKanban,
  Briefcase,
  Bot,
  FileCode2,
  Rocket,
  BarChart3,
  Store,
  Settings,
  ChevronLeft,
  ChevronRight,
  Eye,
  ShieldCheck,
  Share2,
} from 'lucide-react';
import AutoRunnerPanel from '../components/AutoRunner/AutoRunnerPanel';
import GoalComposer from '../components/AutoRunner/GoalComposer';
import PlanApproval from '../components/AutoRunner/PlanApproval';
import RunnerScopeTrack from '../components/AutoRunner/RunnerScopeTrack';
import ExecutionTimeline from '../components/AutoRunner/ExecutionTimeline';
import ProofPanel from '../components/AutoRunner/ProofPanel';
import SystemExplorer from '../components/AutoRunner/SystemExplorer';
import FailureDrawer from '../components/AutoRunner/FailureDrawer';
import BuildReplay from '../components/AutoRunner/BuildReplay';
import BuildCompletionCard from '../components/AutoRunner/BuildCompletionCard';
import SystemStatusHUD from '../components/AutoRunner/SystemStatusHUD';
import PreviewPanel from '../components/AutoRunner/PreviewPanel';
import ResizableDivider from '../components/AutoRunner/ResizableDivider';
import { DEFAULT_FILES } from '../components/workspace/constants';
import { computeSandpackFilesWithMeta, computeSandpackDeps } from '../workspace/sandpackFromFiles';
import { API_BASE } from '../apiBase';
import '../styles/unified-workspace-tokens.css';
import './AutoRunnerPage.css';

const WORKSPACE_NAV = [
  { key: 'auto_runner', label: 'Auto-Runner', Icon: PlayCircle, route: null },
  { key: 'projects', label: 'Projects', Icon: FolderKanban, route: '/app' },
  { key: 'jobs', label: 'Jobs', Icon: Briefcase, route: '/app/monitoring' },
  { key: 'agents', label: 'Agents', Icon: Bot, route: '/app/agents' },
];
const SYSTEM_NAV = [
  { key: 'files', label: 'Files', Icon: FileCode2, route: null, pane: 'code' },
  { key: 'deploys', label: 'Deploys', Icon: Rocket, route: 'classic' },
  { key: 'metrics', label: 'Metrics', Icon: BarChart3, route: '/app/monitoring' },
  { key: 'marketplace', label: 'Marketplace', Icon: Store, route: '/app/skills/marketplace' },
  { key: 'settings', label: 'Settings', Icon: Settings, route: '/app/settings' },
];

const RIGHT_ORDER = ['proof', 'explorer', 'replay', 'failure', 'preview', 'timeline', 'code'];

export default function UnifiedWorkspace() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const projectIdFromUrl = searchParams.get('projectId');
  const taskIdFromUrl = searchParams.get('taskId');
  const jobIdFromUrl = searchParams.get('jobId');
  const { token, user, loading: authLoading, ensureGuest } = useAuth();
  const sessionBootstrapRef = useRef(false);

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

  const { tasks: storeTasks, addTask, updateTask } = useTaskStore();

  const [uxMode, setUxMode] = useState(() => localStorage.getItem('crucibai_ux_mode') || 'pro');
  const toggleUxMode = (m) => {
    setUxMode(m);
    localStorage.setItem('crucibai_ux_mode', m);
  };

  const [leftCollapsed, setLeftCollapsed] = useState(() => localStorage.getItem('crucibai_left_collapsed') === 'true');
  const [rightCollapsed, setRightCollapsed] = useState(() => localStorage.getItem('crucibai_right_collapsed') === 'true');
  useEffect(() => {
    localStorage.setItem('crucibai_left_collapsed', leftCollapsed);
  }, [leftCollapsed]);
  useEffect(() => {
    localStorage.setItem('crucibai_right_collapsed', rightCollapsed);
  }, [rightCollapsed]);

  const [leftWidth, setLeftWidth] = useState(() => parseInt(localStorage.getItem('crucibai_left_width') || '240', 10));
  useEffect(() => {
    localStorage.setItem('crucibai_left_width', String(leftWidth));
  }, [leftWidth]);

  const [rightWidth, setRightWidth] = useState(() => parseInt(localStorage.getItem('crucibai_right_width') || '440', 10));
  useEffect(() => {
    localStorage.setItem('crucibai_right_width', rightWidth);
  }, [rightWidth]);

  const handleLeftResize = useCallback((delta) => {
    setLeftWidth((w) => {
      const minLeft = 200;
      const inner = typeof window !== 'undefined' ? window.innerWidth : 1280;
      const maxLeft = Math.max(minLeft, Math.floor(inner * 0.45));
      return Math.min(maxLeft, Math.max(minLeft, w + delta));
    });
  }, []);
  const handleResetLeftWidth = useCallback(() => setLeftWidth(240), []);

  const handleResize = useCallback((delta) => {
    setRightWidth((w) => {
      const minRight = 200;
      const minCenter = 240;
      const div = 10;
      const leftW = leftCollapsed ? 72 : leftWidth;
      const divLeft = leftCollapsed ? 0 : div;
      const inner = typeof window !== 'undefined' ? window.innerWidth : 1440;
      const maxRight = Math.max(minRight, inner - leftW - divLeft - div - minCenter);
      return Math.min(maxRight, Math.max(minRight, w + delta));
    });
  }, [leftCollapsed, leftWidth]);
  const handleResetWidth = useCallback(() => setRightWidth(440), []);

  const [goal, setGoal] = useState('');
  const [continuationNotes, setContinuationNotes] = useState('');
  const [autoMode, setAutoMode] = useState('guided');
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
  const [activeNav, setActiveNav] = useState('auto_runner');
  const [failedStep, setFailedStep] = useState(null);
  const [buildJobs, setBuildJobs] = useState([]);

  const fetchBuildJobHistory = useCallback(() => {
    if (!token || !API) return;
    axios
      .get(`${API}/orchestrator/build-jobs`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { limit: 30 },
      })
      .then((r) => setBuildJobs(r.data?.jobs || []))
      .catch(() => {});
  }, [token]);

  useEffect(() => {
    fetchBuildJobHistory();
  }, [fetchBuildJobHistory, jobId]);

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
  const [activeFile, setActiveFile] = useState('/App.js');
  const [filesReadyKey, setFilesReadyKey] = useState('uw-default');
  const [iterPrompt, setIterPrompt] = useState('');
  const [iterBuilding, setIterBuilding] = useState(false);

  const [workspacePullKey, setWorkspacePullKey] = useState(0);

  const { sandpackFiles, isFallback: sandpackIsFallback } = useMemo(() => computeSandpackFilesWithMeta(files), [files]);
  const sandpackDeps = useMemo(() => computeSandpackDeps(files), [files]);

  /** URL wins so stream/poll start on first paint when opening ?jobId=… (state hydrates a tick later). */
  const effectiveJobId = jobIdFromUrl || jobId;
  const { job, steps, events, proof, isConnected, refresh } = useJobStream(effectiveJobId, token);

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

  const previewStatus = isCompleted ? 'ready' : stage === 'running' || iterBuilding ? 'building' : 'idle';
  const previewUrl = job?.preview_url || null;

  const projectSlug = effectiveProjectId
    ? `project-${String(effectiveProjectId).slice(0, 8)}…`
    : user?.email?.split('@')[0] || user?.name || 'proof-service';

  const handleNav = (item) => {
    setActiveNav(item.key);
    if (item.key === 'auto_runner') return;
    if (item.route === 'classic') {
      navigate(`/app/workspace-classic${location.search}`);
      return;
    }
    if (item.route) navigate(item.route);
    if (item.pane) {
      setActivePane(item.pane);
      setRightCollapsed(false);
    }
  };

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
          setActiveFile(Object.keys(loaded).sort().find((k) => k.includes('App')) || Object.keys(loaded).sort()[0]);
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
    const fileUrl = (path) =>
      useJobWs
        ? `${API}/jobs/${effectiveJobId}/workspace/file`
        : `${API}/projects/${effectiveProjectId}/workspace/file`;
    axios
      .get(listUrl, { headers })
      .then((r) => {
        const list = r.data?.files || [];
        if (list.length === 0) return;
        return Promise.all(
          list.map((path) =>
            axios
              .get(fileUrl(path), { params: { path }, headers })
              .then((f) => ({ path: f.data.path, content: f.data.content }))
              .catch(() => null),
          ),
        ).then((results) => {
          const loaded = results.filter(Boolean).reduce((acc, { path, content }) => {
            const key = path.startsWith('/') ? path : `/${path}`;
            acc[key] = { code: content };
            return acc;
          }, {});
          if (Object.keys(loaded).length > 0) {
            // Merge so backend-only trees do not wipe Sandpack (computeSandpackFiles ignores .py, etc.).
            setFiles((prev) => ({ ...prev, ...loaded }));
            setActiveFile((cur) => {
              if (cur) {
                const normalized = cur.startsWith('/') ? cur : `/${cur}`;
                if (loaded[normalized]) return normalized;
              }
              const keys = Object.keys(loaded).sort();
              return keys.find((k) => /App\.(jsx?|tsx?)$/i.test(k)) || keys[0] || cur;
            });
            setFilesReadyKey(
              useJobWs ? `job_${effectiveJobId}_${Date.now()}` : `proj_${effectiveProjectId}_${Date.now()}`,
            );
          }
        });
      })
      .catch(() => {});
  }, [effectiveProjectId, effectiveJobId, token, workspacePullKey]);

  const reloadWorkspaceFromServer = useCallback(() => {
    lastPulledStepCount.current = 0;
    setWorkspacePullKey((k) => k + 1);
  }, []);

  const handleGeneratePlan = async () => {
    if (!goal.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const cont = continuationNotes.trim();
      const planGoal = cont
        ? `${goal.trim()}\n\n--- Continuation / next phase (${new Date().toISOString()}) ---\n${cont}`
        : goal.trim();
      const res = await axios.post(
        `${API}/orchestrator/plan`,
        { goal: planGoal, mode: autoMode, build_target: buildTarget },
        { headers },
      );
      setPlan(res.data.plan);
      setCapabilityNotice(Array.isArray(res.data.capability_notice) ? res.data.capability_notice : []);
      if (res.data.build_target_meta) setBuildTargetMeta(res.data.build_target_meta);
      else if (res.data.build_target && buildTargets.length) {
        setBuildTargetMeta(buildTargets.find((t) => t.id === res.data.build_target) || null);
      }
      setEstimate(res.data.estimate);
      setJobId(res.data.job_id);
      setStage('plan');
      setContinuationNotes('');
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (res.data.job_id) next.set('jobId', res.data.job_id);
          return next;
        },
        { replace: true },
      );
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to generate plan.');
    } finally {
      setLoading(false);
    }
  };

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
    setContinuationNotes('');
    setPlan(null);
    setCapabilityNotice([]);
    setBuildTarget('vite_react');
    setBuildTargetMeta(null);
    setEstimate(null);
    setJobId(null);
    setStage('input');
    setError(null);
    setFailedStep(null);
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.delete('jobId');
        return next;
      },
      { replace: true },
    );
  };

  const openBuildJob = useCallback(
    (id) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set('jobId', id);
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const runIterativeBuild = async () => {
    if (!iterPrompt.trim() || iterBuilding) return;
    setIterBuilding(true);
    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
    const sessionId = taskIdFromUrl || `task_${Date.now()}`;
    const existingTask = storeTasks.find((t) => String(t.id) === String(taskIdFromUrl));
    try {
      const res = await fetch(`${API}/ai/build/iterative`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ message: iterPrompt.trim(), session_id: sessionId }),
      });
      if (!res.ok || !res.body) throw new Error(`Build failed (${res.status})`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      while (!done) {
        const { value, done: streamDone } = await reader.read();
        if (streamDone) break;
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split('\n').filter(Boolean)) {
          let ev;
          try {
            ev = JSON.parse(line);
          } catch {
            continue;
          }
          if (ev.type === 'step_complete' && ev.files) {
            setFiles((prev) => ({ ...prev, ...ev.files }));
            setFilesReadyKey(`iter_${Date.now()}`);
          }
          if (ev.type === 'done') {
            done = true;
            const built = ev.files || {};
            setFiles((prev) => {
              const merged = { ...prev, ...built };
              const taskPayload = {
                id: sessionId,
                name: iterPrompt.slice(0, 80) || 'Build',
                prompt: iterPrompt,
                status: 'completed',
                type: 'build',
                files: merged,
                createdAt: existingTask?.createdAt || Date.now(),
              };
              if (existingTask) updateTask(sessionId, taskPayload);
              else addTask(taskPayload);
              return merged;
            });
            const u = new URL(window.location.href);
            u.searchParams.set('taskId', sessionId);
            window.history.replaceState({}, '', u.toString());
            setActivePane('preview');
            break;
          }
        }
      }
    } catch (e) {
      setError(e.message || 'Iterative build failed');
    } finally {
      setIterBuilding(false);
    }
  };

  const handleCodeChange = (value) => {
    setFiles((prev) => ({
      ...prev,
      [activeFile]: { code: value },
    }));
  };

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

  const effectiveBuildTargetId = useMemo(
    () => plan?.crucib_build_target || buildTarget,
    [plan?.crucib_build_target, buildTarget],
  );
  const effectiveBuildTargetMeta = useMemo(() => {
    if (buildTargetMeta && buildTargetMeta.id === effectiveBuildTargetId) return buildTargetMeta;
    const row = buildTargets.find((t) => t.id === effectiveBuildTargetId);
    return row || buildTargetMeta;
  }, [effectiveBuildTargetId, buildTargetMeta, buildTargets]);

  return (
    <div className={`uw-root arp-root arp-ux-${uxMode}`}>
      <div className="arp-topbar">
        <div className="arp-topbar-left">
          <span className="arp-logo">CrucibAI</span>
          <div className="arp-breadcrumb">
            <span className="arp-bc-strong">{projectSlug}</span>
            <span className="arp-bc-sep">/</span>
            <code className="arp-env-pill">production</code>
          </div>
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

        <div className="arp-topbar-center">
          <AutoRunnerPanel
            mode={autoMode}
            onModeChange={setAutoMode}
            jobId={effectiveJobId}
            jobStatus={job?.status}
            onRun={() => handleApprove()}
            onPause={handleCancel}
            onResume={handleResume}
            onCancel={handleCancel}
            budget={estimate}
          />
        </div>

        <div className="arp-topbar-right">
          <button
            type="button"
            className="arp-topbar-btn"
            title="Preview"
            onClick={() => {
              setActivePane('preview');
              setRightCollapsed(false);
            }}
          >
            <Eye size={14} />
            <span className="arp-topbar-btn-label">Preview</span>
          </button>
          <button
            type="button"
            className="arp-topbar-btn"
            title="Full deploy tools (classic workspace)"
            onClick={() => navigate(`/app/workspace-classic${location.search}`)}
          >
            <Rocket size={14} />
            <span className="arp-topbar-btn-label">Deploy</span>
          </button>
          <button
            type="button"
            className="arp-topbar-btn"
            title="Proof"
            onClick={() => {
              setActivePane('proof');
              setRightCollapsed(false);
            }}
          >
            <ShieldCheck size={14} />
            <span className="arp-topbar-btn-label">Proof</span>
          </button>
          <button type="button" className="arp-topbar-btn arp-topbar-btn-share" title="Copy link" onClick={handleShare}>
            <Share2 size={14} />
            <span className="arp-topbar-btn-label">Share</span>
          </button>

          <div className="arp-mode-switch">
            <button type="button" className={`arp-ux-btn ${uxMode === 'beginner' ? 'active' : ''}`} onClick={() => toggleUxMode('beginner')}>
              Beginner
            </button>
            <button type="button" className={`arp-ux-btn ${uxMode === 'pro' ? 'active' : ''}`} onClick={() => toggleUxMode('pro')}>
              Pro
            </button>
          </div>

          <button
            type="button"
            className="arp-topbar-btn"
            title="Open classic workspace (full IDE)"
            onClick={() => navigate(`/app/workspace-classic${location.search}`)}
          >
            <span className="arp-topbar-btn-label">Classic</span>
          </button>

          <SystemStatusHUD
            isConnected={isConnected}
            activeAgentCount={activeAgentCount}
            jobStatus={job?.status}
            steps={steps}
            healthLatencyMs={healthMs}
            eventCount={events.length}
            proofItemCount={proofItemCount}
          />
        </div>
      </div>

      {token && buildJobs.length > 0 && (
        <div className="arp-recent-builds" aria-label="Recent Auto-Runner jobs">
          <span className="arp-recent-label">Recent builds</span>
          <div className="arp-recent-scroll">
            {buildJobs.map((j) => {
              const g = j.goal || '';
              const label = g.length > 56 ? `${g.slice(0, 56)}…` : g || j.id || '';
              const active = j.id === effectiveJobId;
              return (
                <button
                  key={j.id}
                  type="button"
                  className={`arp-recent-chip ${active ? 'active' : ''} st-${j.status || 'unknown'}`}
                  title={j.goal || j.id}
                  onClick={() => openBuildJob(j.id)}
                >
                  <span className="arp-recent-chip-status" aria-hidden />
                  <span className="arp-recent-chip-text">{label || j.id}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      <div className="arp-layout">
        <div
          className={`arp-left-rail ${leftCollapsed ? 'collapsed' : ''}`}
          style={!leftCollapsed ? { width: leftWidth, minWidth: leftWidth, maxWidth: leftWidth } : undefined}
        >
          <div
            className="arp-rail-toggle"
            role="button"
            tabIndex={0}
            aria-expanded={!leftCollapsed}
            aria-label={leftCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setLeftCollapsed(!leftCollapsed);
              }
            }}
            onClick={() => setLeftCollapsed(!leftCollapsed)}
          >
            {leftCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
          </div>
          <nav className="arp-nav">
            {!leftCollapsed && <div className="arp-nav-section-label">Workspace</div>}
            {WORKSPACE_NAV.map(({ key, label, Icon, ...rest }) => (
              <button
                key={key}
                type="button"
                className={`arp-nav-item ${activeNav === key ? 'active' : ''}`}
                onClick={() => handleNav({ key, label, Icon, ...rest })}
                title={leftCollapsed ? label : undefined}
              >
                <Icon size={16} />
                {!leftCollapsed && <span className="arp-nav-label">{label}</span>}
              </button>
            ))}
            {!leftCollapsed && <div className="arp-nav-section-label arp-nav-section-label-system">System</div>}
            {SYSTEM_NAV.map(({ key, label, Icon, ...rest }) => (
              <button
                key={key}
                type="button"
                className={`arp-nav-item ${activeNav === key ? 'active' : ''}`}
                onClick={() => handleNav({ key, label, Icon, ...rest })}
                title={leftCollapsed ? label : undefined}
              >
                <Icon size={16} />
                {!leftCollapsed && <span className="arp-nav-label">{label}</span>}
              </button>
            ))}
          </nav>
        </div>

        {!leftCollapsed && (
          <ResizableDivider invertDelta onResize={handleLeftResize} onDoubleClick={handleResetLeftWidth} />
        )}

        <div className="arp-center-pane">
          <RunnerScopeTrack buildTargetId={effectiveBuildTargetId} buildTargetMeta={effectiveBuildTargetMeta} />
          {/* Always show input - never hide it */}
          <>
            <GoalComposer
              goal={goal}
              onGoalChange={setGoal}
              onSubmit={handleGeneratePlan}
              loading={loading}
              error={error}
              token={token}
              onEstimateReady={setEstimate}
              authLoading={authLoading}
              onRetrySession={() => {
                sessionBootstrapRef.current = false;
                ensureGuest();
              }}
              buildTarget={buildTarget}
              onBuildTargetChange={setBuildTarget}
              buildTargets={buildTargets}
              continuationNotes={continuationNotes}
              onContinuationChange={setContinuationNotes}
            />
            <div className="iterative-strip">
              <h3>Iterative build (classic API)</h3>
              <p style={{ margin: '0 0 8px', fontSize: 12, color: 'var(--text-muted)' }}>
                Streams file updates into the preview panel. Full Monaco, deploy ZIP, and Pro panels remain in{' '}
                <button
                  type="button"
                  className="classic-link"
                  style={{
                    background: 'none',
                    border: 'none',
                    padding: 0,
                    cursor: 'pointer',
                    color: 'var(--state-info)',
                    textDecoration: 'underline',
                  }}
                  onClick={() => navigate(`/app/workspace-classic${location.search}`)}
                >
                  Classic workspace
                </button>
                .
              </p>
              <textarea
                value={iterPrompt}
                onChange={(e) => setIterPrompt(e.target.value)}
                placeholder="e.g. Build a proof-validation microservice with REST API and tests…"
              />
              <div className="iterative-strip-actions">
                <button type="button" className="primary" disabled={iterBuilding || !iterPrompt.trim()} onClick={runIterativeBuild}>
                  {iterBuilding ? 'Building…' : 'Run iterative build'}
                </button>
              </div>
            </div>
          </>

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

              <ExecutionTimeline
                steps={steps}
                events={events}
                job={job}
                onRetryStep={handleRetryStep}
                onJumpToCode={() => setActivePane('code')}
                isConnected={isConnected}
              />

              {failureStep && activePane !== 'failure' && (
                <FailureDrawer
                  step={failureStep}
                  onRetry={handleRetryStep}
                  onOpenCode={() => setActivePane('code')}
                  onPauseJob={handleCancel}
                  onClose={() => setFailedStep(null)}
                />
              )}
            </div>
          )}
        </div>

        {!rightCollapsed && <ResizableDivider onResize={handleResize} onDoubleClick={handleResetWidth} />}

        <div className={`arp-right-pane ${rightCollapsed ? 'collapsed' : ''}`} style={!rightCollapsed ? { width: `${rightWidth}px` } : undefined}>
          <div className="arp-right-toggle" onClick={() => setRightCollapsed(!rightCollapsed)}>
            {rightCollapsed ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
          </div>

          {!rightCollapsed && (
            <>
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
                    onJumpToCode={() => setActivePane('code')}
                    isConnected={isConnected}
                  />
                )}
                {activePane === 'proof' && <ProofPanel proof={proof} jobId={effectiveJobId} onExport={() => {}} />}
                {activePane === 'explorer' && uxMode === 'pro' && (
                  <SystemExplorer steps={steps} proof={proof} job={job} projectId={effectiveProjectId} token={token} />
                )}
                {activePane === 'replay' && uxMode === 'pro' && <BuildReplay events={events} steps={steps} />}
                {activePane === 'failure' &&
                  (failureStep ? (
                    <FailureDrawer
                      step={failureStep}
                      onRetry={handleRetryStep}
                      onOpenCode={() => setActivePane('code')}
                      onPauseJob={handleCancel}
                      onClose={() => setFailedStep(null)}
                    />
                  ) : (
                    <div className="arp-failure-empty">No failed steps — all green.</div>
                  ))}
                {activePane === 'code' && uxMode === 'pro' && (
                  <div className="code-pane-wrap">
                    <div className="code-pane-tabs">
                      {Object.keys(files)
                        .sort()
                        .map((fp) => (
                          <button key={fp} type="button" className={activeFile === fp ? 'active' : ''} onClick={() => setActiveFile(fp)}>
                            {fp.replace(/^\//, '')}
                          </button>
                        ))}
                    </div>
                    <div className="code-pane-editor">
                      <Editor
                        height="100%"
                        theme="vs-dark"
                        path={activeFile}
                        language={
                          activeFile.endsWith('.css')
                            ? 'css'
                            : activeFile.endsWith('.json')
                              ? 'json'
                              : activeFile.endsWith('.html')
                                ? 'html'
                                : activeFile.endsWith('.tsx') || activeFile.endsWith('.ts')
                                  ? 'typescript'
                                  : 'javascript'
                        }
                        value={files[activeFile]?.code || ''}
                        onChange={handleCodeChange}
                        options={{ minimap: { enabled: false }, fontSize: 13, wordWrap: 'on' }}
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
  );
}
