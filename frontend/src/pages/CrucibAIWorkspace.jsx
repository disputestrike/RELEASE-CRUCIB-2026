/**
 * CrucibAI 10/10 workspace — single canonical /app/workspace experience.
 * Wires PDF-style event backbone + IndexedDB logs to real SSE, orchestrator, jobs, terminal, trust.
 */
import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Menu } from 'lucide-react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import { useTaskStore } from '../stores/useTaskStore';
import { useJobStream } from '../hooks/useJobStream';
import { computeSandpackFilesWithMeta } from '../workspace/sandpackFromFiles';
import EmotionalPeaks from '../components/EmotionalPeaks';
import CommandCenter from '../components/CommandCenter';
import InterruptibleFlow from '../components/InterruptibleFlow';
import ConsciousnessStream from '../components/ConsciousnessStream';
import RightPanel from '../components/RightPanel';
import AgentDebugPanel from '../workspace10/AgentDebugPanel';
import JobTerminalStrip from '../workspace10/JobTerminalStrip';
import { logWorkspaceEvent } from '../workspace10/agentLogs';
import { normalizeSseToWorkspaceEvent } from '../workspace10/normalizeSseEvent';
import { contextManager } from '../lib/contextManager';
import { memoryGraph } from '../lib/memoryGraph';
import { permissionEngine } from '../lib/permissionEngine';
import { runParallelSpawnProbe } from '../lib/spawnEngine';
import TrustPanel from '../components/TrustPanel';
import ToolCarousel from '../components/ToolCarousel';
import ChatStream from '../components/ChatStream';
import WorkspaceFusedRail from '../components/WorkspaceFusedRail';
import { useWorkspaceRail } from '../contexts/WorkspaceRailContext';
import { extractWorkspaceLaunchIntent } from '../utils/workspaceEntry';
import './CrucibAIWorkspace.css';

function useJobWorkspaceFiles(jobId, token) {
  const [files, setFiles] = useState([]);
  const [fileContent, setFileContent] = useState({});
  const loadFiles = useCallback(async () => {
    if (!jobId || !token) return;
    try {
      const res = await axios.get(`${API}/jobs/${jobId}/workspace/files`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setFiles(res.data?.files || []);
    } catch {
      setFiles([]);
    }
  }, [jobId, token]);

  const loadFileContent = useCallback(
    async (path) => {
      if (!jobId || !token || fileContent[path] !== undefined) return;
      try {
        const res = await axios.get(`${API}/jobs/${jobId}/workspace/file`, {
          headers: { Authorization: `Bearer ${token}` },
          params: { path },
        });
        setFileContent((prev) => ({ ...prev, [path]: res.data?.content || '' }));
      } catch {
        setFileContent((prev) => ({ ...prev, [path]: '// Could not load file' }));
      }
    },
    [jobId, token, fileContent],
  );

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  return { files, fileContent, loadFileContent, reloadFiles: loadFiles };
}

function normalizeListJobStatus(status) {
  const s = String(status || '').toLowerCase();
  if (s === 'complete') return 'completed';
  return s || 'pending';
}

function listJobToTaskEntry(j) {
  const jid = j?.id || j?.job_id;
  if (!jid) return null;
  const goalText = (j.goal || j.payload?.goal || j.name || 'Build').trim();
  const createdRaw = j.created_at || j.createdAt;
  let createdAt = Date.now();
  if (createdRaw) {
    const parsed = Date.parse(String(createdRaw));
    if (Number.isFinite(parsed)) createdAt = parsed;
  }
  return {
    id: `task_job_${jid}`,
    jobId: jid,
    name: goalText.slice(0, 120),
    prompt: goalText,
    status: normalizeListJobStatus(j.status),
    type: 'build',
    createdAt,
    linkedProjectId: j.project_id ?? j.payload?.project_id ?? null,
  };
}

export default function CrucibAIWorkspace() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { token } = useAuth();
  const { tasks, addTask, updateTask, setTasks } = useTaskStore();

  const jobIdFromUrl = searchParams.get('jobId');
  const projectIdFromUrl = searchParams.get('projectId');
  const [goal, setGoal] = useState('');
  const [activeJobId, setActiveJobId] = useState(jobIdFromUrl || null);
  const [stage, setStage] = useState(jobIdFromUrl ? 'running' : 'input');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activePane, setActivePane] = useState('stream');
  const [deployLoading, setDeployLoading] = useState(false);
  const [deployResult, setDeployResult] = useState(null);
  const [workflows, setWorkflows] = useState({});
  const [workflowsOpen, setWorkflowsOpen] = useState(false);
  const [workflowLoading, setWorkflowLoading] = useState(null);
  const [thinkingEffort, setThinkingEffort] = useState('medium');
  const [trust, setTrust] = useState(null);
  const [showDebug, setShowDebug] = useState(false);
  const [showSkill, setShowSkill] = useState(false);
  const [skillDesc, setSkillDesc] = useState('');
  const [skillBusy, setSkillBusy] = useState(false);
  const [showSimulation, setShowSimulation] = useState(false);
  const [simulationScenario, setSimulationScenario] = useState('');
  const [simulationPopulation, setSimulationPopulation] = useState(32);
  const [simulationRounds, setSimulationRounds] = useState(3);
  const [simulationBusy, setSimulationBusy] = useState(false);
  const [simulationRound, setSimulationRound] = useState(null);
  const [simulationPersonas, setSimulationPersonas] = useState([]);
  const [simulationRecommendation, setSimulationRecommendation] = useState(null);
  const [spawnBusy, setSpawnBusy] = useState(false);
  const [spawnMode, setSpawnMode] = useState('swan');
  const [spawnBranches, setSpawnBranches] = useState(24);
  const [downloadBusy, setDownloadBusy] = useState(false);
  /** Bumps when client memory / permission graph updates so TrustPanel re-reads stores. */
  const [insightTick, setInsightTick] = useState(0);
  const seenEventIdsRef = useRef(new Set());
  const buildInFlightRef = useRef(false);
  const processedLaunchRef = useRef(new Set());

  const { job, steps, events, proof, isConnected, connectionMode, refresh } = useJobStream(activeJobId, token);
  const { reloadFiles } = useJobWorkspaceFiles(activeJobId, token);

  useEffect(() => {
    if (!job) return;
    if (job.status === 'completed') {
      setStage('completed');
      if (activePane === 'stream') setActivePane('preview');
    } else if (job.status === 'failed') setStage('failed');
    else if (job.status === 'running' || job.status === 'pending') {
      setStage('running');
    }
  }, [job?.status, activePane]);

  useEffect(() => {
    if (stage === 'completed') reloadFiles();
  }, [stage, reloadFiles]);

  useEffect(() => {
    axios
      .get(`${API}/workflows`, token ? { headers: { Authorization: `Bearer ${token}` } } : {})
      .then((r) => setWorkflows(r.data?.workflows || {}))
      .catch(() => {});
  }, [token]);

  /** Merge server job list into the task store so History / recent builds stay aligned after refresh. */
  useEffect(() => {
    if (!token) return undefined;
    let cancelled = false;
    (async () => {
      try {
        const res = await axios.get(`${API}/jobs`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (cancelled) return;
        const rows = res.data?.jobs || [];
        const serverTasks = rows.map(listJobToTaskEntry).filter(Boolean);
        const byJobId = new Map(serverTasks.map((t) => [t.jobId, t]));
        setTasks((prev) => {
          const seen = new Set();
          const updated = prev.map((t) => {
            if (!t.jobId) return t;
            const srv = byJobId.get(t.jobId);
            if (!srv) return t;
            seen.add(t.jobId);
            return {
              ...t,
              status: srv.status,
              name: t.name || srv.name,
              linkedProjectId: t.linkedProjectId || srv.linkedProjectId,
            };
          });
          const extras = serverTasks.filter((st) => !seen.has(st.jobId) && !updated.some((t) => t.jobId === st.jobId));
          return [...extras, ...updated].slice(0, 200);
        });
      } catch {
        /* ignore — guest or backend down */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, setTasks]);

  /** Deep link from AgentMonitor: /app/workspace?projectId=… → pick latest job for that project. */
  useEffect(() => {
    if (!token || !projectIdFromUrl || jobIdFromUrl || activeJobId) return undefined;
    let cancelled = false;
    (async () => {
      try {
        const res = await axios.get(`${API}/jobs`, {
          headers: { Authorization: `Bearer ${token}` },
          params: { limit: 50 },
        });
        const jobs = res.data?.jobs || [];
        const match = jobs.find((j) => String(j.project_id) === String(projectIdFromUrl));
        if (!cancelled && match?.id) {
          setActiveJobId(match.id);
          const st = String(match.status || '').toLowerCase();
          if (st === 'completed' || st === 'complete') setStage('completed');
          else if (st === 'failed') setStage('failed');
          else setStage('running');
          setSearchParams(
            (p) => {
              const n = new URLSearchParams(p);
              n.set('jobId', match.id);
              return n;
            },
            { replace: true },
          );
        }
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, projectIdFromUrl, jobIdFromUrl, activeJobId, setSearchParams]);

  useEffect(() => {
    if (!activeJobId || !token) {
      setTrust(null);
      return undefined;
    }
    let cancelled = false;
    const loadTrust = async () => {
      try {
        const res = await axios.get(`${API}/jobs/${activeJobId}/trust-report`, {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 12000,
        });
        if (!cancelled) setTrust(res.data);
      } catch {
        if (!cancelled) setTrust(null);
      }
    };
    loadTrust();
    const t = setInterval(loadTrust, 20000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [activeJobId, token]);

  useEffect(() => {
    if (!activeJobId || !events?.length) return;
    events.forEach((ev) => {
      const id = ev.id || `${ev.type}-${ev.ts}-${JSON.stringify(ev.payload || {}).slice(0, 40)}`;
      if (seenEventIdsRef.current.has(id)) return;
      seenEventIdsRef.current.add(id);
      const normalized = normalizeSseToWorkspaceEvent(activeJobId, ev);
      if (normalized) void logWorkspaceEvent(normalized);
    });
  }, [events, activeJobId]);

  const previewUrl = useMemo(
    () =>
      job?.dev_server_url ||
      job?.preview_url ||
      job?.published_url ||
      job?.deploy_url ||
      (stage === 'completed' && activeJobId ? `/published/${encodeURIComponent(activeJobId)}/` : null),
    [job, stage, activeJobId],
  );

  const sandpackFiles = useMemo(
    () =>
      computeSandpackFilesWithMeta(
        Object.fromEntries(
          (steps || [])
            .filter((s) => s.output_files)
            .flatMap((s) => {
              try {
                return Object.entries(JSON.parse(s.output_files));
              } catch {
                return [];
              }
            }),
        ),
      ).sandpackFiles,
    [steps],
  );

  /** Flat path → source string for VirtualFS merge during parallel probe. */
  const flatSandpackFiles = useMemo(() => {
    const o = sandpackFiles || {};
    return Object.fromEntries(
      Object.entries(o).map(([p, f]) => [
        p,
        typeof f === 'object' && f != null && typeof f.code === 'string' ? f.code : String(f ?? ''),
      ]),
    );
  }, [sandpackFiles]);

  /** Same path as the composer: plan → persist task → run-auto (used by workflows when the server falls back). */
  const executePlanAndRun = useCallback(
    async (rawGoal, { displayName } = {}) => {
      const trimmed = String(rawGoal || '').trim();
      if (!trimmed || buildInFlightRef.current) return false;
      if (!token) {
        setError('Sign in to run a build.');
        setStage('failed');
        return false;
      }
      contextManager.addTurn('user', trimmed);
      buildInFlightRef.current = true;
      setLoading(true);
      setError(null);
      setStage('running');
      setActiveJobId(null);
      setDeployResult(null);
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const planRes = await axios.post(`${API}/orchestrator/plan`, { goal: trimmed, mode: 'auto' }, { headers });
        const jid = planRes.data.job_id;
        setActiveJobId(jid);
        setSearchParams(
          (p) => {
            const n = new URLSearchParams(p);
            n.set('jobId', jid);
            return n;
          },
          { replace: true },
        );
        const taskId = `task_${Date.now()}`;
        const label = (displayName || trimmed).slice(0, 80);
        addTask({
          id: taskId,
          name: label,
          prompt: trimmed,
          status: 'running',
          type: 'build',
          createdAt: Date.now(),
          jobId: jid,
        });
        await axios.post(`${API}/orchestrator/run-auto`, { job_id: jid }, { headers });
        setGoal('');
        void memoryGraph.save('session', `job:${jid}`, { goal: trimmed, projectId: projectIdFromUrl || job?.project_id }, 0.55);
        if (projectIdFromUrl) {
          void memoryGraph.save('project', `proj:${projectIdFromUrl}`, { goal: trimmed, jobId: jid }, 0.65);
        }
        setInsightTick((x) => x + 1);
        return true;
      } catch (e) {
        const detail = e.response?.data?.detail;
        setError(typeof detail === 'string' ? detail : detail?.message || e.message || 'Build failed');
        setStage('failed');
        return false;
      } finally {
        setLoading(false);
        buildInFlightRef.current = false;
      }
    },
    [token, addTask, setSearchParams, projectIdFromUrl, job?.project_id],
  );

  const { setWorkspaceRail, clearWorkspaceRail } = useWorkspaceRail();

  const onFuseNewTask = useCallback(() => {
    setActiveJobId(null);
    setStage('input');
    setGoal('');
    setSearchParams({}, { replace: true });
    setDeployResult(null);
    seenEventIdsRef.current = new Set();
  }, [setSearchParams]);

  const handleWorkflow = useCallback(
    async (workflowKey) => {
      setWorkflowLoading(workflowKey);
      setWorkflowsOpen(false);
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const res = await axios.post(
          `${API}/workflows/run`,
          { workflow_key: workflowKey, project_id: job?.project_id || null },
          { headers },
        );
        if (res.data.success && res.data.job_id) {
          const jid = res.data.job_id;
          setActiveJobId(jid);
          setStage('running');
          setSearchParams(
            (p) => {
              const n = new URLSearchParams(p);
              n.set('jobId', jid);
              return n;
            },
            { replace: true },
          );
          const goalText = String(res.data.goal || '').trim();
          addTask({
            id: `task_${Date.now()}`,
            name: String(res.data.workflow || workflowKey).slice(0, 80),
            prompt: goalText || String(res.data.workflow || workflowKey),
            status: 'running',
            type: 'build',
            createdAt: Date.now(),
            jobId: jid,
          });
        } else if (res.data.fallback && String(res.data.goal || '').trim()) {
          const ok = await executePlanAndRun(String(res.data.goal).trim(), {
            displayName: res.data.workflow || workflowKey,
          });
          if (!ok) setWorkflowsOpen(true);
        } else {
          setError(res.data?.error || 'Workflow could not be started.');
          setWorkflowsOpen(true);
        }
      } catch (e) {
        setError(e.response?.data?.detail || e.message);
        setWorkflowsOpen(true);
      } finally {
        setWorkflowLoading(null);
      }
    },
    [token, job?.project_id, setSearchParams, addTask, executePlanAndRun],
  );

  useEffect(() => {
    setWorkspaceRail(
      <WorkspaceFusedRail
        onNewTask={onFuseNewTask}
        workflows={workflows}
        workflowsOpen={workflowsOpen}
        onToggleWorkflows={() => setWorkflowsOpen((o) => !o)}
        workflowLoading={workflowLoading}
        onRunWorkflow={handleWorkflow}
      />,
    );
    return () => clearWorkspaceRail();
  }, [
    setWorkspaceRail,
    clearWorkspaceRail,
    onFuseNewTask,
    workflows,
    workflowsOpen,
    workflowLoading,
    handleWorkflow,
  ]);

  const handleSend = useCallback(
    async (overrideText) => {
      const raw = (overrideText || goal).trim();
      if (!raw || loading) return;
      const trimmed =
        thinkingEffort === 'high'
          ? `[thinking:high] ${raw}`
          : thinkingEffort === 'low'
            ? `[thinking:low] ${raw}`
            : raw;

      const isRunning = stage === 'running' || job?.status === 'running' || job?.status === 'pending';
      if (isRunning && activeJobId) {
        try {
          const headers = { Authorization: `Bearer ${token}` };
          contextManager.addTurn('user', trimmed);
          await axios.post(
            `${API}/jobs/${activeJobId}/steer`,
            { message: trimmed, resume: false },
            { headers },
          );
          contextManager.addTurn('tool', `Steer delivered to job ${String(activeJobId).slice(0, 8)}…`);
          setGoal('');
        } catch (e) {
          setError(e.response?.data?.detail || e.message);
        }
        return;
      }

      await executePlanAndRun(trimmed);
    },
    [goal, loading, stage, job?.status, activeJobId, token, executePlanAndRun, thinkingEffort],
  );

  useEffect(() => {
    if (!token) return;
    if (activeJobId) return;

    const intent = extractWorkspaceLaunchIntent({
      locationState: location.state,
      search: location.search,
    });

    if (!intent.prompt || !intent.autoStart) return;
    const key = intent.handoffKey || `fallback:${location.search}`;
    if (processedLaunchRef.current.has(key)) return;
    processedLaunchRef.current.add(key);

    setGoal(intent.prompt);
    void handleSend(intent.prompt);

    if (intent.hasPromptInQuery) {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.delete('prompt');
          next.delete('autoStart');
          return next;
        },
        { replace: true },
      );
    }
  }, [token, activeJobId, location.state, location.search, handleSend, setSearchParams]);

  const handleDeploy = useCallback(async () => {
    if (!activeJobId || !job?.project_id || deployLoading) return;
    const gate = await permissionEngine.check('railway.deploy', 0.78);
    if (gate.mode === 'block') {
      setError(gate.reason);
      return;
    }
    setDeployLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.post(
        `${API}/projects/${job.project_id}/deploy/railway`,
        { job_id: activeJobId },
        { headers },
      );
      setDeployResult(res.data);
      await permissionEngine.update('railway.deploy', 'allow', 0.78, true);
      setInsightTick((x) => x + 1);
    } catch (e) {
      setDeployResult({ error: e.response?.data?.detail || e.message });
    } finally {
      setDeployLoading(false);
    }
  }, [activeJobId, job?.project_id, deployLoading, token]);

  const handleDownloadWorkspaceZip = useCallback(async () => {
    if (!activeJobId || !token) {
      setError('Sign in to download the workspace bundle.');
      return;
    }
    const gate = await permissionEngine.check('workspace.download_zip', 0.42);
    if (gate.mode === 'block') {
      setError(gate.reason);
      return;
    }
    setDownloadBusy(true);
    try {
      const res = await axios.get(`${API}/jobs/${activeJobId}/workspace/download`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob',
      });
      const cd = res.headers['content-disposition'] || res.headers['Content-Disposition'];
      let filename = `crucibai-build-${String(activeJobId).slice(0, 8)}.zip`;
      if (cd && typeof cd === 'string') {
        const m = cd.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)["']?/i) || cd.match(/filename="([^"]+)"/i);
        if (m?.[1]) filename = decodeURIComponent(m[1].trim());
      }
      const url = window.URL.createObjectURL(res.data instanceof Blob ? res.data : new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.rel = 'noopener';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      await permissionEngine.update('workspace.download_zip', 'allow', 0.42, true);
      setInsightTick((x) => x + 1);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Download failed');
    } finally {
      setDownloadBusy(false);
    }
  }, [activeJobId, token]);

  const handleSpawnProbe = useCallback(async () => {
    if (!activeJobId) return;
    const gate = await permissionEngine.check('workspace.parallel_probe', 0.52);
    if (gate.mode === 'block') {
      setError(gate.reason);
      return;
    }
    setSpawnBusy(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const merged = await runParallelSpawnProbe({
        jobId: activeJobId,
        task: goal || job?.goal || 'parallel workspace probe',
        currentFiles: flatSandpackFiles,
        axios,
        API,
        token,
        createDiskLayers: true,
        branches: Number.isFinite(Number(spawnBranches)) ? Number(spawnBranches) : 24,
        mode: spawnMode,
        postSpawn: (body) => axios.post(`${API}/spawn/run`, body, { headers }),
      });
      const results = merged.subagentResults || [];
      results.forEach((r) => {
        void logWorkspaceEvent({
          type: r.status === 'failed' ? 'subagent.failed' : 'subagent.complete',
          jobId: activeJobId,
          timestamp: Date.now(),
          payload: { subagentId: r.id, result: r.result },
        });
      });
      if (merged.mergeConflicts?.length) {
        void logWorkspaceEvent({
          type: 'issue.detected',
          jobId: activeJobId,
          timestamp: Date.now(),
          payload: {
            title: `Virtual merge: ${merged.mergeConflicts.length} overlapping paths`,
            severity: 'low',
            files: merged.mergeConflicts,
          },
        });
      }
      await permissionEngine.update('workspace.parallel_probe', 'allow', 0.52, true);
      setInsightTick((x) => x + 1);
      refresh();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setSpawnBusy(false);
    }
  }, [activeJobId, token, goal, job?.goal, refresh, flatSandpackFiles, spawnBranches, spawnMode]);

  const runScenarioSimulation = useCallback(async () => {
    if (!activeJobId || !token || !simulationScenario.trim()) return;
    setSimulationBusy(true);
    setSimulationRound(null);
    setSimulationPersonas([]);
    setSimulationRecommendation(null);
    try {
      const response = await fetch(`${API}/spawn/simulate/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          jobId: activeJobId,
          scenario: simulationScenario.trim(),
          population_size: Number.isFinite(Number(simulationPopulation)) ? Math.max(3, Math.min(256, Math.floor(Number(simulationPopulation)))) : 32,
          rounds: Number.isFinite(Number(simulationRounds)) ? Math.max(1, Math.min(8, Math.floor(Number(simulationRounds)))) : 3,
          agent_roles: ['architect', 'backend', 'security', 'ux', 'devops'],
          priors: {
            cost_sensitive: 0.3,
            security_first: 0.4,
            speed_first: 0.3,
          },
        }),
      });
      if (!response.ok || !response.body) {
        throw new Error(`Simulation failed (${response.status})`);
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, idx).trim();
          buffer = buffer.slice(idx + 1);
          if (!line) continue;
          let payload;
          try {
            payload = JSON.parse(line);
          } catch {
            continue;
          }
          if (payload.type === 'simulation.update') {
            setSimulationRound({
              round: payload.round,
              clusters: payload.clusters,
              sentiment_shift: payload.sentiment_shift,
              consensus_emerging: payload.consensus_emerging,
            });
          }
          if (payload.type === 'simulation.completed') {
            setSimulationRecommendation(payload.recommendation || null);
            setSimulationPersonas(Array.isArray(payload.personas) ? payload.personas : []);
          }
        }
      }
      setShowSimulation(false);
    } catch (e) {
      setError(e.message || 'Simulation failed');
    } finally {
      setSimulationBusy(false);
    }
  }, [activeJobId, token, simulationScenario, simulationPopulation, simulationRounds]);

  const applySimulationRecommendation = useCallback(async () => {
    if (!activeJobId || !token || !simulationRecommendation?.recommended_action) return;
    try {
      await axios.post(
        `${API}/jobs/${activeJobId}/steer`,
        {
          message: `Apply simulation recommendation: ${simulationRecommendation.recommended_action}`,
          resume: true,
        },
        { headers: { Authorization: `Bearer ${token}` } },
      );
      setSimulationRecommendation(null);
      setSimulationRound(null);
      setSimulationPersonas([]);
      refresh();
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Could not apply recommendation');
    }
  }, [activeJobId, token, simulationRecommendation, refresh]);

  const normalizedSimulationPopulation = Number.isFinite(Number(simulationPopulation))
    ? Math.max(3, Math.min(256, Math.floor(Number(simulationPopulation))))
    : 32;
  const normalizedSimulationRounds = Number.isFinite(Number(simulationRounds))
    ? Math.max(1, Math.min(8, Math.floor(Number(simulationRounds))))
    : 3;

  const carouselTools = useMemo(
    () => {
      const items = [];
      if (activeJobId) {
        items.push({
          id: 'parallel_probe',
          name: 'workspace.parallel_probe',
          label: spawnBusy ? 'Probe…' : `SWAN probe (${spawnBranches})`,
          risk: 0.52,
          disabled: spawnBusy,
          title: 'Parallel SWAN branch probe (VirtualFS + optional disk worktrees)',
          onClick: () => {
            void handleSpawnProbe();
          },
        });
      }
      if (stage === 'completed' && activeJobId) {
        items.push({
          id: 'download_zip',
          name: 'workspace.download_zip',
          label: downloadBusy ? 'ZIP…' : 'Download ZIP',
          risk: 0.42,
          disabled: downloadBusy || !token,
          title: 'Download workspace bundle',
          onClick: () => {
            void handleDownloadWorkspaceZip();
          },
        });
      }
      if (stage === 'completed' && activeJobId && job?.project_id && !deployResult) {
        items.push({
          id: 'railway_deploy',
          name: 'railway.deploy',
          label: deployLoading ? 'Deploy…' : 'Deploy',
          risk: 0.78,
          disabled: deployLoading,
          title: 'Deploy to Railway',
          onClick: () => {
            void handleDeploy();
          },
        });
      }
      return items;
    },
    [
      activeJobId,
      stage,
      token,
      spawnBusy,
      downloadBusy,
      deployLoading,
      deployResult,
      job?.project_id,
      handleSpawnProbe,
      handleDownloadWorkspaceZip,
      handleDeploy,
    ],
  );

  const generateSkill = async () => {
    if (!skillDesc.trim()) return;
    setSkillBusy(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.post(`${API}/skills/generate`, { description: skillDesc.trim() }, { headers });
      const skill = res.data;
      const list = JSON.parse(localStorage.getItem('crucibai_skills') || '[]');
      list.push(skill);
      localStorage.setItem('crucibai_skills', JSON.stringify(list));
      setShowSkill(false);
      setSkillDesc('');
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setSkillBusy(false);
    }
  };

  const isRunning = stage === 'running' || loading;
  const totalSteps = steps?.length || 0;
  const completedSteps = steps?.filter((s) => s.status === 'completed').length || 0;
  const brainMessages = useMemo(
    () =>
      (events || [])
        .filter((e) => (e.type || e.event_type) === 'brain_guidance')
        .map((e) => {
          const p = e.payload?.payload || e.payload || {};
          return p.summary || p.headline || null;
        })
        .filter(Boolean)
        .slice(-4),
    [events],
  );

  const trustQuality =
    trust?.trust_score ??
    trust?.production_readiness_score ??
    trust?.class_weighted_score ??
    proof?.quality_score ??
    null;
  const trustSecurity = trust?.truth_status === 'failed' ? 'failed' : trust?.truth_status === 'partial' ? 'warning' : 'passed';

  return (
    <div className="c10-root" data-testid="crucib-workspace-root">
      <ChatStream
        events={events}
        jobId={activeJobId}
        isRunning={isRunning}
        simulation={simulationRound}
        simulationPersonas={simulationPersonas}
        simulationRecommendation={simulationRecommendation}
        onSimulationContinue={() => {
          if (!simulationBusy) {
            void runScenarioSimulation();
          }
        }}
        onSimulationStop={() => setSimulationBusy(false)}
        onApplyRecommendation={applySimulationRecommendation}
      />
      <EmotionalPeaks job={job} steps={steps} proof={proof} stage={stage} />

      <header className="c10-header">
        <div className="c10-header-left">
          <button type="button" className="c10-btn" onClick={() => navigate('/app')} aria-label="Open dashboard" title="Home">
            <Menu size={18} strokeWidth={2} aria-hidden />
          </button>
          <span className="c10-title">Workspace</span>
          <span className="c10-live">
            <span className={`c10-dot ${isConnected ? 'on' : ''}`} />
            {isConnected && connectionMode === 'stream' ? 'Live' : connectionMode === 'polling' ? 'Polling' : 'Offline'}
          </span>
        </div>
        <div className="c10-header-actions">
          <button type="button" className="c10-btn" onClick={() => setShowSkill(true)}>
            New skill
          </button>
          <button type="button" className="c10-btn" onClick={() => setShowDebug(true)}>
            Debug logs
          </button>
          {deployResult?.deploy_url && (
            <a className="c10-btn c10-btn-primary" href={deployResult.deploy_url} target="_blank" rel="noopener noreferrer">
              Live
            </a>
          )}
          {activeJobId && (
            <button type="button" className="c10-btn" onClick={onFuseNewTask}>
              New build
            </button>
          )}
        </div>
      </header>

      <TrustPanel
        trustQuality={trustQuality}
        trustSecurity={trustSecurity}
        proofTotal={proof?.total_proof_items ?? null}
        insightTick={insightTick}
      />

      <div className="c10-body">
        <PanelGroup direction="horizontal" className="c10-panel-group" autoSaveId="crucib-workspace-split">
          <Panel defaultSize={58} minSize={32} className="c10-panel c10-panel--center">
            <section className="c10-center">
              <div className="c10-chat-scroll">
                {error && (
                  <div className="c10-alert c10-alert--error" role="alert">
                    {typeof error === 'string' ? error : JSON.stringify(error)}
                  </div>
                )}
                {(job?.goal || (isRunning && goal)) && (
                  <div className="c10-goal-banner">{job?.goal || goal}</div>
                )}
                {stage === 'input' && !job && (
                  <div className="c10-empty-hero">
                    <h2 className="c10-empty-title">What do you want to build?</h2>
                    <p className="c10-empty-copy">
                      Describe it below. CrucibAI plans, runs agents on the real orchestrator, and streams progress here.
                    </p>
                  </div>
                )}
                {(isRunning || stage === 'completed' || stage === 'failed') && (
                  <div className="c10-brain-block">
                    {brainMessages.map((msg, idx) => (
                      <p key={idx} className="c10-brain-line">
                        {msg}
                      </p>
                    ))}
                    {brainMessages.length === 0 && isRunning && (
                      <p className="c10-brain-muted">
                        {completedSteps === 0
                          ? 'Starting execution from your approved plan…'
                          : `${completedSteps}/${totalSteps || '?'} steps complete — continuing.`}
                      </p>
                    )}
                    {stage === 'completed' && (
                      <p className="c10-brain-success">Build complete. Preview and proof are available on the right.</p>
                    )}
                    {stage === 'failed' && <p className="c10-brain-fail">Build failed — use steering or retry.</p>}
                  </div>
                )}
              </div>

              <div className="c10-effort">
                <label htmlFor="c10-thinking">Thinking effort</label>
                <select
                  id="c10-thinking"
                  value={thinkingEffort}
                  onChange={(e) => setThinkingEffort(e.target.value)}
                  disabled={isRunning}
                >
                  <option value="low">Fast</option>
                  <option value="medium">Balanced</option>
                  <option value="high">Deep</option>
                </select>
                <label htmlFor="c10-spawn-mode">Spawn mode</label>
                <select
                  id="c10-spawn-mode"
                  value={spawnMode}
                  onChange={(e) => setSpawnMode(e.target.value)}
                  disabled={spawnBusy}
                >
                  <option value="swan">SWAN</option>
                  <option value="classic">Classic</option>
                </select>
                <label htmlFor="c10-spawn-branches">Branches</label>
                <input
                  id="c10-spawn-branches"
                  type="number"
                  min={1}
                  value={spawnBranches}
                  onChange={(e) => {
                    const n = Number(e.target.value);
                    setSpawnBranches(Number.isFinite(n) ? Math.max(1, Math.floor(n)) : 1);
                  }}
                  disabled={spawnBusy}
                  style={{
                    width: 88,
                    borderRadius: 6,
                    border: '1px solid var(--theme-border)',
                    background: 'var(--theme-select)',
                    color: 'var(--theme-select-text)',
                    padding: '4px 8px',
                    fontSize: 12,
                  }}
                />
              </div>

              <InterruptibleFlow
                jobId={activeJobId}
                steps={steps}
                isRunning={isRunning}
                token={token}
                onSimulateScenario={() => setShowSimulation(true)}
              />
              <CommandCenter
                onSubmit={({ text }) => {
                  if (text) {
                    setGoal(text);
                    setTimeout(() => handleSend(text), 0);
                  }
                }}
                isRunning={isRunning}
                placeholder={isRunning ? 'Steer the build…' : 'Describe your app…'}
                toolCarousel={<ToolCarousel tools={carouselTools} disabled={loading} />}
              />
            </section>
          </Panel>
          <PanelResizeHandle className="c10-resize-handle" />
          <Panel defaultSize={42} minSize={28} className="c10-panel c10-panel--right">
            <section className="c10-right">
              <div className="c10-pane-tabs">
                {[
                  { id: 'stream', label: 'Live stream' },
                  { id: 'preview', label: 'Preview & code' },
                ].map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    className={`c10-pane-tab ${activePane === t.id ? 'active' : ''}`}
                    onClick={() => setActivePane(t.id)}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              <div className="c10-right-main">
                {activePane === 'stream' && (
                  <div className="c10-right-stream-wrap">
                    <ConsciousnessStream events={events} steps={steps} isRunning={isRunning} proof={proof} />
                  </div>
                )}
                {activePane === 'preview' && (
                  <RightPanel
                    jobId={activeJobId}
                    token={token}
                    steps={steps}
                    isRunning={isRunning}
                    previewUrl={previewUrl}
                    sandpackFiles={sandpackFiles}
                    simulationRecommendation={simulationRecommendation}
                    onApplySimulationRecommendation={applySimulationRecommendation}
                    onRejectSimulationRecommendation={() => setSimulationRecommendation(null)}
                  />
                )}
              </div>
              <JobTerminalStrip projectId={job?.project_id} token={token} />
            </section>
          </Panel>
        </PanelGroup>
      </div>

      {showDebug && <AgentDebugPanel onClose={() => setShowDebug(false)} />}

      {showSkill && (
        <div className="c10-skill-backdrop" role="presentation" onClick={() => !skillBusy && setShowSkill(false)}>
          <div className="c10-skill-modal" role="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Generate skill from description</h3>
            <textarea value={skillDesc} onChange={(e) => setSkillDesc(e.target.value)} placeholder="Describe the reusable workflow…" />
            <div className="c10-skill-actions">
              <button type="button" className="c10-btn" onClick={() => setShowSkill(false)} disabled={skillBusy}>
                Cancel
              </button>
              <button type="button" className="c10-btn c10-btn-primary" onClick={generateSkill} disabled={skillBusy || !skillDesc.trim()}>
                {skillBusy ? 'Generating…' : 'Generate'}
              </button>
            </div>
          </div>
        </div>
      )}
      {showSimulation && (
        <div className="c10-skill-backdrop" role="presentation" onClick={() => !simulationBusy && setShowSimulation(false)}>
          <div className="c10-skill-modal" role="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Simulate scenario</h3>
            <textarea
              value={simulationScenario}
              onChange={(e) => setSimulationScenario(e.target.value)}
              placeholder="What if we remove Stripe and use Lemon Squeezy?"
            />
            <div style={{ display: 'flex', gap: 12, marginTop: 10 }}>
              <label style={{ display: 'grid', gap: 4, fontSize: 12, color: 'var(--theme-muted)' }}>
                Population
                <input
                  type="number"
                  min={3}
                  max={256}
                  value={normalizedSimulationPopulation}
                  onChange={(e) => setSimulationPopulation(e.target.value)}
                  disabled={simulationBusy}
                />
              </label>
              <label style={{ display: 'grid', gap: 4, fontSize: 12, color: 'var(--theme-muted)' }}>
                Rounds
                <input
                  type="number"
                  min={1}
                  max={8}
                  value={normalizedSimulationRounds}
                  onChange={(e) => setSimulationRounds(e.target.value)}
                  disabled={simulationBusy}
                />
              </label>
            </div>
            <div style={{ marginTop: 8, fontSize: 11, color: 'var(--theme-muted)' }}>
              Clustered simulation runs with persona priors and streamed round updates.
            </div>
            <div className="c10-skill-actions">
              <button type="button" className="c10-btn" onClick={() => setShowSimulation(false)} disabled={simulationBusy}>
                Cancel
              </button>
              <button
                type="button"
                className="c10-btn c10-btn-primary"
                onClick={() => {
                  void runScenarioSimulation();
                }}
                disabled={simulationBusy || !simulationScenario.trim()}
              >
                {simulationBusy ? 'Simulating…' : 'Start Simulation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
