import { useMemo, useState, useEffect, useRef, useCallback } from "react";
import { useSearchParams, useNavigate, useLocation, Link } from "react-router-dom";
import axios from "axios";
import Editor from "@monaco-editor/react";
import { SandpackProvider, SandpackPreview } from "@codesandbox/sandpack-react";
import SandpackErrorBoundary from "../components/SandpackErrorBoundary";
import "../components/SandpackErrorBoundary.css";
import { Globe, Rocket, Download, Loader2 } from "lucide-react";
import { API, useAuth } from "../App";
import { useTaskStore } from "../stores/useTaskStore";
import { computeSandpackFiles, computeSandpackDeps } from "../workspace/sandpackFromFiles";
import {
  DEFAULT_FILES,
  ConsolePanel,
  normalizeWorkspacePath,
  isWorkspaceDbPath,
  isWorkspaceDocPath,
  docSortKey,
  extractSqlTableNames,
  WorkspaceProPanels,
} from "../components/workspace";
import "./WorkspaceManus.css";

const ALL_TABS = [
  "preview",
  "code",
  "files",
  "console",
  "database",
  "dashboard",
  "docs",
  "analytics",
  "agents",
  "deploy",
  "graph",
  "passes",
  "sandbox",
];

const PRO_ONLY_TABS = new Set(["database", "docs", "analytics", "agents", "passes", "sandbox"]);

const DEFAULT_STEP_GROUPS = [
  "Planning",
  "Architecture",
  "Frontend",
  "Backend",
  "Validation",
  "Deploy",
];

function formatDeployErr(e) {
  const d = e.response?.data?.detail;
  if (typeof d === "string") return d;
  if (d && typeof d === "object") return d.message || JSON.stringify(d);
  return e.message;
}

export default function WorkspaceManus() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const taskIdFromUrl = searchParams.get("taskId");
  const projectIdFromUrl = searchParams.get("projectId");
  const { token, user, refreshUser } = useAuth();
  const { tasks: storeTasks, addTask, updateTask } = useTaskStore();

  const existingTask = useMemo(
    () => storeTasks.find((t) => String(t.id) === String(taskIdFromUrl)),
    [storeTasks, taskIdFromUrl],
  );

  const [mode, setMode] = useState("guided");
  const [tab, setTab] = useState("preview");
  const [prompt, setPrompt] = useState(existingTask?.prompt || "");
  const [isBuilding, setIsBuilding] = useState(false);
  const [buildPct, setBuildPct] = useState(0);
  const [messages, setMessages] = useState(
    existingTask?.messages || [
      {
        role: "assistant",
        content:
          "Describe what to build. I will plan, generate files, and keep the execution steps visible.",
      },
    ],
  );
  const [steps, setSteps] = useState(
    DEFAULT_STEP_GROUPS.map((s, i) => ({
      id: `default-${i}`,
      name: s,
      status: "pending",
      detail: "",
    })),
  );
  const [logs, setLogs] = useState([]);
  const [consoleFilter, setConsoleFilter] = useState("all");
  const [files, setFiles] = useState(existingTask?.files && Object.keys(existingTask.files).length ? existingTask.files : DEFAULT_FILES);
  const [activeFile, setActiveFile] = useState("/App.js");
  const [filesReadyKey, setFilesReadyKey] = useState("default");
  const [versions, setVersions] = useState([]);

  const [buildHistoryList, setBuildHistoryList] = useState([]);
  const [buildHistoryLoading, setBuildHistoryLoading] = useState(false);
  const [buildTimelineEvents, setBuildTimelineEvents] = useState([]);
  const [buildEventsErr, setBuildEventsErr] = useState(null);
  const [serverDbSnapshots, setServerDbSnapshots] = useState([]);
  const [serverDbLoading, setServerDbLoading] = useState(false);
  const [serverDbErr, setServerDbErr] = useState(null);
  const [serverDocSnapshots, setServerDocSnapshots] = useState([]);
  const [serverDocsLoading, setServerDocsLoading] = useState(false);
  const [serverDocsErr, setServerDocsErr] = useState(null);
  const [docsSelectedPath, setDocsSelectedPath] = useState(null);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsErr, setAnalyticsErr] = useState(null);
  const [agentApiStatuses, setAgentApiStatuses] = useState([]);
  const [agentsActivity, setAgentsActivity] = useState([]);
  const [projectSandboxLogs, setProjectSandboxLogs] = useState([]);
  const [projectSandboxLoading, setProjectSandboxLoading] = useState(false);
  const [projectSandboxErr, setProjectSandboxErr] = useState(null);
  const [projectBuildProgress, setProjectBuildProgress] = useState({
    phase: 0,
    agent: "",
    progress: 0,
    status: "",
    tokens_used: 0,
  });
  const [currentPhase, setCurrentPhase] = useState("");

  const [showDeployModal, setShowDeployModal] = useState(false);
  const [projectLiveUrl, setProjectLiveUrl] = useState(null);
  const [deployTokensHint, setDeployTokensHint] = useState({ has_vercel: false, has_netlify: false });
  const [deployZipBusy, setDeployZipBusy] = useState(false);
  const [deployOneClickBusy, setDeployOneClickBusy] = useState(null);
  const [publishCustomDomain, setPublishCustomDomain] = useState("");
  const [publishRailwayUrl, setPublishRailwayUrl] = useState("");
  const [publishSaveBusy, setPublishSaveBusy] = useState(false);
  const [deployRailwayBusy, setDeployRailwayBusy] = useState(false);
  const [deployRailwaySteps, setDeployRailwaySteps] = useState(null);
  const [deployRailwayDashboard, setDeployRailwayDashboard] = useState(null);
  const [deployRailwayErr, setDeployRailwayErr] = useState(null);

  const workspaceFilesLoadedForProject = useRef(null);
  const [workspacePullKey, setWorkspacePullKey] = useState(0);
  const reloadWorkspaceFromServer = useCallback(() => {
    workspaceFilesLoadedForProject.current = null;
    setWorkspacePullKey((k) => k + 1);
  }, []);

  const sandpackFiles = useMemo(() => computeSandpackFiles(files), [files]);
  const sandpackDeps = useMemo(() => computeSandpackDeps(files), [files]);

  const localMdDocs = useMemo(
    () =>
      Object.entries(files)
        .filter(([k]) => isWorkspaceDocPath(k))
        .map(([path, f]) => ({
          path: path.startsWith("/") ? path.slice(1) : path,
          content: f?.code || "",
          source: "editor",
        })),
    [files],
  );

  const mergedDocFiles = useMemo(() => {
    const sortFn = (a, b) => docSortKey(a.path) - docSortKey(b.path) || String(a.path).localeCompare(String(b.path));
    const editor = localMdDocs.map((d) => ({ ...d, source: "editor" })).sort(sortFn);
    if (!projectIdFromUrl) return editor;
    const serv = serverDocSnapshots.map((d) => ({ path: d.path, content: d.content || "", source: "server" })).sort(sortFn);
    const sn = new Set(serv.map((d) => normalizeWorkspacePath(d.path)));
    const uniqEditor = editor.filter((d) => !sn.has(normalizeWorkspacePath(d.path)));
    return [...serv, ...uniqEditor].sort(sortFn);
  }, [projectIdFromUrl, serverDocSnapshots, localMdDocs]);

  const localDbEntries = useMemo(
    () =>
      Object.entries(files)
        .filter(([k]) => isWorkspaceDbPath(k))
        .map(([k, f]) => ({
          path: k.startsWith("/") ? k.slice(1) : k,
          displayKey: k.startsWith("/") ? k : `/${k}`,
          content: f?.code || "",
          source: "editor",
        })),
    [files],
  );

  const dbPanelMerge = useMemo(() => {
    const serverNorm = new Set(serverDbSnapshots.map((s) => normalizeWorkspacePath(s.path)));
    const editorOnly = localDbEntries.filter((e) => !serverNorm.has(normalizeWorkspacePath(e.path)));
    const sqlBlob = [...serverDbSnapshots, ...editorOnly.map((e) => ({ content: e.content }))]
      .map((x) => x.content)
      .join("\n");
    return {
      editorOnly,
      inferredTables: [...new Set(extractSqlTableNames(sqlBlob))],
      hasRows: serverDbSnapshots.length > 0 || localDbEntries.length > 0,
    };
  }, [serverDbSnapshots, localDbEntries]);

  const filteredConsoleLogs = useMemo(() => {
    if (consoleFilter === "all") return logs;
    return logs.filter((log) => {
      const t = log.type || "info";
      const a = (log.agent || "").toLowerCase();
      if (consoleFilter === "error") return t === "error";
      if (consoleFilter === "build") return a === "build";
      if (consoleFilter === "system") return a === "system" || !log.agent;
      return true;
    });
  }, [logs, consoleFilter]);

  const visibleTabs = useMemo(
    () => (mode === "pro" ? ALL_TABS : ALL_TABS.filter((t) => !PRO_ONLY_TABS.has(t))),
    [mode],
  );

  useEffect(() => {
    if (mode === "guided" && PRO_ONLY_TABS.has(tab)) setTab("preview");
  }, [mode, tab]);

  const addLog = useCallback((message, type = "info", agent = null) => {
    const now = new Date();
    const time = `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}:${now.getSeconds().toString().padStart(2, "0")}`;
    setLogs((prev) => [...prev, { message, type, time, agent }]);
  }, []);

  useEffect(() => {
    addLog("Workspace ready. Build output and API logs appear here.", "info", "system");
  }, [addLog]);

  useEffect(() => {
    const stateFiles = location.state?.initialFiles;
    if (stateFiles && typeof stateFiles === "object" && Object.keys(stateFiles).length > 0) {
      setFiles(stateFiles);
    }
  }, [location.state]);

  useEffect(() => {
    if (!projectIdFromUrl || !token || !API) return;
    setBuildHistoryLoading(true);
    axios
      .get(`${API}/projects/${projectIdFromUrl}/build-history`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => setBuildHistoryList(r.data?.build_history || []))
      .catch(() => setBuildHistoryList([]))
      .finally(() => setBuildHistoryLoading(false));
  }, [projectIdFromUrl, token, API]);

  useEffect(() => {
    if (!projectIdFromUrl || !token || !API) {
      setProjectLiveUrl(null);
      setPublishCustomDomain("");
      setPublishRailwayUrl("");
      return;
    }
    axios
      .get(`${API}/projects/${projectIdFromUrl}`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        const p = r.data?.project;
        setProjectLiveUrl(p?.live_url || null);
        setPublishCustomDomain(typeof p?.custom_domain === "string" ? p.custom_domain : "");
        setPublishRailwayUrl(typeof p?.railway_project_url === "string" ? p.railway_project_url : "");
      })
      .catch(() => {
        setProjectLiveUrl(null);
        setPublishCustomDomain("");
        setPublishRailwayUrl("");
      });
  }, [projectIdFromUrl, token, API]);

  useEffect(() => {
    if (!showDeployModal || !token || !API) return;
    axios
      .get(`${API}/users/me/deploy-tokens`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => setDeployTokensHint({ has_vercel: !!r.data?.has_vercel, has_netlify: !!r.data?.has_netlify }))
      .catch(() => setDeployTokensHint({ has_vercel: false, has_netlify: false }));
  }, [showDeployModal, token, API]);

  useEffect(() => {
    if (!showDeployModal) {
      setDeployRailwaySteps(null);
      setDeployRailwayDashboard(null);
      setDeployRailwayErr(null);
    }
  }, [showDeployModal]);

  useEffect(() => {
    if (!projectIdFromUrl || !token || !API) {
      setBuildTimelineEvents([]);
      setBuildEventsErr(null);
      return undefined;
    }
    let cancelled = false;
    let es = null;
    let pollId = null;
    const clearPoll = () => {
      if (pollId != null) {
        clearInterval(pollId);
        pollId = null;
      }
    };
    const fetchSnapshot = () => {
      axios
        .get(`${API}/projects/${projectIdFromUrl}/events/snapshot`, {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 12000,
        })
        .then((r) => {
          if (cancelled) return;
          const list = r.data?.events;
          setBuildTimelineEvents(Array.isArray(list) ? list : []);
          setBuildEventsErr(null);
        })
        .catch((e) => {
          if (cancelled) return;
          const st = e?.response?.status;
          setBuildEventsErr(st === 404 ? "Project not found or no access." : "Could not load build events.");
        });
    };
    const startPolling = (ms) => {
      clearPoll();
      fetchSnapshot();
      pollId = setInterval(fetchSnapshot, ms);
    };
    axios
      .get(`${API}/projects/${projectIdFromUrl}/events/snapshot`, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 12000,
      })
      .then((r) => {
        if (cancelled) return;
        const list = Array.isArray(r.data?.events) ? r.data.events : [];
        setBuildTimelineEvents(list);
        setBuildEventsErr(null);
        const maxId = list.length ? Math.max(...list.map((e) => Number(e?.id) || 0)) : -1;
        const lastId = maxId + 1;
        const base = API.replace(/\/$/, "");
        const url = `${base}/projects/${encodeURIComponent(projectIdFromUrl)}/events?last_id=${lastId}&access_token=${encodeURIComponent(token)}`;
        try {
          es = new EventSource(url);
          es.onmessage = (event) => {
            if (cancelled) return;
            try {
              const ev = JSON.parse(event.data);
              if (ev?.type === "stream_end") {
                es?.close();
                return;
              }
              if (ev == null || typeof ev.id !== "number") return;
              setBuildTimelineEvents((prev) => {
                if (prev.some((x) => x.id === ev.id)) return prev;
                return [...prev, ev];
              });
            } catch (_) {
              /* ignore */
            }
          };
          es.onerror = () => {
            if (cancelled) return;
            try {
              es?.close();
            } catch (_) {
              /* ignore */
            }
            es = null;
            startPolling(isBuilding ? 3000 : 8000);
          };
        } catch (_) {
          startPolling(isBuilding ? 2000 : 5000);
        }
      })
      .catch((e) => {
        if (cancelled) return;
        const st = e?.response?.status;
        setBuildEventsErr(st === 404 ? "Project not found or no access." : "Could not load build events.");
        startPolling(isBuilding ? 2000 : 5000);
      });
    return () => {
      cancelled = true;
      clearPoll();
      try {
        es?.close();
      } catch (_) {
        /* ignore */
      }
    };
  }, [projectIdFromUrl, token, API, isBuilding]);

  useEffect(() => {
    setServerDbSnapshots([]);
    setServerDbErr(null);
    setServerDocSnapshots([]);
    setServerDocsErr(null);
    setDocsSelectedPath(null);
    setAnalyticsData(null);
    setAnalyticsErr(null);
  }, [projectIdFromUrl]);

  useEffect(() => {
    if (tab !== "database" || !projectIdFromUrl || !token || !API) return undefined;
    let cancelled = false;
    setServerDbLoading(true);
    setServerDbErr(null);
    const headers = { Authorization: `Bearer ${token}` };
    axios
      .get(`${API}/projects/${projectIdFromUrl}/workspace/files`, { headers, timeout: 15000 })
      .then(async (r) => {
        const paths = (r.data?.files || []).filter(isWorkspaceDbPath).slice(0, 30);
        const chunks = await Promise.all(
          paths.map((path) =>
            axios
              .get(`${API}/projects/${projectIdFromUrl}/workspace/file`, { params: { path }, headers, timeout: 12000 })
              .then((res) => ({ path: res.data.path, content: res.data.content || "", source: "server" }))
              .catch(() => null),
          ),
        );
        if (!cancelled) setServerDbSnapshots(chunks.filter(Boolean));
      })
      .catch((e) => {
        if (!cancelled) setServerDbErr(typeof e?.response?.data?.detail === "string" ? e.response.data.detail : e?.message || "Load failed");
      })
      .finally(() => {
        if (!cancelled) setServerDbLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tab, projectIdFromUrl, token, API]);

  useEffect(() => {
    if (tab !== "docs" || !projectIdFromUrl || !token || !API) return undefined;
    let cancelled = false;
    setServerDocsLoading(true);
    setServerDocsErr(null);
    const headers = { Authorization: `Bearer ${token}` };
    axios
      .get(`${API}/projects/${projectIdFromUrl}/workspace/files`, { headers, timeout: 15000 })
      .then(async (r) => {
        const paths = (r.data?.files || []).filter(isWorkspaceDocPath).slice(0, 35);
        const sorted = [...paths].sort((a, b) => docSortKey(a) - docSortKey(b) || a.localeCompare(b));
        const chunks = await Promise.all(
          sorted.map((path) =>
            axios
              .get(`${API}/projects/${projectIdFromUrl}/workspace/file`, { params: { path }, headers, timeout: 12000 })
              .then((res) => ({ path: res.data.path, content: res.data.content || "", source: "server" }))
              .catch(() => null),
          ),
        );
        if (!cancelled) setServerDocSnapshots(chunks.filter(Boolean));
      })
      .catch((e) => {
        if (!cancelled) setServerDocsErr(typeof e?.response?.data?.detail === "string" ? e.response.data.detail : e?.message || "Load failed");
      })
      .finally(() => {
        if (!cancelled) setServerDocsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tab, projectIdFromUrl, token, API]);

  useEffect(() => {
    if (tab !== "analytics" || !token || !API) return undefined;
    let cancelled = false;
    setAnalyticsLoading(true);
    setAnalyticsErr(null);
    const headers = { Authorization: `Bearer ${token}` };
    Promise.all([
      axios.get(`${API}/jobs`, { headers, timeout: 12000 }),
      axios.get(`${API}/tokens/usage`, { headers, timeout: 12000 }),
    ])
      .then(([jobsRes, tokRes]) => {
        if (!cancelled) {
          setAnalyticsData({
            jobs: jobsRes.data?.jobs || [],
            tokens: tokRes.data || null,
          });
        }
      })
      .catch((e) => {
        if (!cancelled) setAnalyticsErr(e?.message || "Failed to load analytics");
      })
      .finally(() => {
        if (!cancelled) setAnalyticsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tab, token, API]);

  useEffect(() => {
    if (tab !== "docs" || mergedDocFiles.length === 0) return;
    setDocsSelectedPath((prev) => {
      if (!prev) return mergedDocFiles[0].path;
      const np = normalizeWorkspacePath(prev);
      const hit = mergedDocFiles.find((d) => normalizeWorkspacePath(d.path) === np);
      return hit ? hit.path : mergedDocFiles[0].path;
    });
  }, [tab, mergedDocFiles]);

  useEffect(() => {
    const agentsPoll = tab === "agents" || isBuilding;
    if (!agentsPoll || !projectIdFromUrl || !token || !API) return undefined;
    let cancelled = false;
    const headers = { Authorization: `Bearer ${token}` };
    const run = () => {
      axios
        .get(`${API}/agents/status/${projectIdFromUrl}`, { headers, timeout: 12000 })
        .then((r) => {
          if (!cancelled) setAgentApiStatuses(Array.isArray(r.data?.statuses) ? r.data.statuses : []);
        })
        .catch(() => {
          if (!cancelled) setAgentApiStatuses([]);
        });
    };
    run();
    const id = setInterval(run, 4000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [tab, isBuilding, projectIdFromUrl, token, API]);

  useEffect(() => {
    if (tab !== "sandbox" || !projectIdFromUrl || !token || !API) return undefined;
    let cancelled = false;
    setProjectSandboxLoading(true);
    setProjectSandboxErr(null);
    const headers = { Authorization: `Bearer ${token}` };
    const run = () => {
      axios
        .get(`${API}/projects/${projectIdFromUrl}/logs`, { headers, timeout: 15000 })
        .then((r) => {
          if (!cancelled) setProjectSandboxLogs(Array.isArray(r.data?.logs) ? r.data.logs : []);
        })
        .catch((e) => {
          if (!cancelled) {
            setProjectSandboxLogs([]);
            setProjectSandboxErr(typeof e?.response?.data?.detail === "string" ? e.response.data.detail : e?.message || "Failed to load logs");
          }
        })
        .finally(() => {
          if (!cancelled) setProjectSandboxLoading(false);
        });
    };
    run();
    const id = setInterval(run, 8000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [tab, projectIdFromUrl, token, API]);

  useEffect(() => {
    if (token) {
      axios
        .get(`${API}/agents/activity`, { headers: { Authorization: `Bearer ${token}` } })
        .then((r) => setAgentsActivity(r.data.activities || []))
        .catch(() => {});
    }
  }, [token, messages.length]);

  useEffect(() => {
    if (!taskIdFromUrl || !token || !API) return;
    axios
      .get(`${API}/tasks/${taskIdFromUrl}`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        const task = r.data?.task || r.data;
        const taskFiles = task?.files || task?.doc?.files;
        if (!taskFiles || Object.keys(taskFiles).length === 0) return;
        const loaded = Object.entries(taskFiles).reduce((acc, [path, content]) => {
          const key = path.startsWith("/") ? path : `/${path}`;
          acc[key] = { code: typeof content === "string" ? content : content?.code || "" };
          return acc;
        }, {});
        if (Object.keys(loaded).length > 0) {
          setFiles(loaded);
          setActiveFile(Object.keys(loaded).sort().find((k) => k.includes("App")) || Object.keys(loaded).sort()[0]);
          setTimeout(() => {
            const vId = `task_${taskIdFromUrl}_${Date.now()}`;
            setFilesReadyKey(`fk_${vId}`);
            setTab("preview");
          }, 500);
        }
      })
      .catch(() => {});
  }, [taskIdFromUrl, token, API]);

  useEffect(() => {
    if (!projectIdFromUrl || !token || !API || workspaceFilesLoadedForProject.current === projectIdFromUrl) return;
    const headers = { Authorization: `Bearer ${token}` };
    axios
      .get(`${API}/projects/${projectIdFromUrl}/workspace/files`, { headers })
      .then((r) => {
        const list = r.data?.files || [];
        if (list.length === 0) return;
        workspaceFilesLoadedForProject.current = projectIdFromUrl;
        return Promise.all(
          list.map((path) =>
            axios.get(`${API}/projects/${projectIdFromUrl}/workspace/file`, { params: { path }, headers }).then((f) => ({ path: f.data.path, content: f.data.content })).catch(() => null),
          ),
        ).then((results) => {
          const loaded = results.filter(Boolean).reduce((acc, { path, content }) => {
            const key = path.startsWith("/") ? path : `/${path}`;
            acc[key] = { code: content };
            return acc;
          }, {});
          if (Object.keys(loaded).length > 0) {
            setFiles(loaded);
            setActiveFile((current) => (current && loaded[current] ? current : Object.keys(loaded).sort()[0]));
            setTimeout(() => {
              const vId = `reload_${projectIdFromUrl}_${Date.now()}`;
              setFilesReadyKey(`fk_${vId}`);
              setTab("preview");
            }, 500);
          }
        });
      })
      .catch(() => {});
  }, [projectIdFromUrl, token, API, workspacePullKey]);

  useEffect(() => {
    if (!projectIdFromUrl || !API) return;
    const wsBase = (API || "").replace(/^http/, "ws").replace(/\/api\/?$/, "");
    const wsUrl = `${wsBase}/ws/projects/${projectIdFromUrl}/progress`;
    let ws;
    let reconnectTimeout;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 10;
    const baseDelay = 1000;
    const connect = () => {
      try {
        ws = new WebSocket(wsUrl);
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setProjectBuildProgress({
              phase: data.phase ?? 0,
              agent: data.agent ?? "",
              progress: data.progress ?? 0,
              status: data.status ?? "",
              tokens_used: data.tokens_used ?? 0,
            });
            if (data.agent && data.status) {
              setAgentsActivity((prev) => {
                const existing = prev.findIndex((a) => a.name === data.agent);
                const entry = { name: data.agent, status: data.status, phase: data.phase, progress: data.progress, updated: Date.now() };
                if (existing >= 0) {
                  const next = [...prev];
                  next[existing] = entry;
                  return next;
                }
                return [...prev, entry];
              });
            }
            if (data.type === "build_completed" && data.status === "completed") {
              const deployFiles = data.deploy_files;
              if (deployFiles && Object.keys(deployFiles).length > 0) {
                const next = {};
                for (const [filePath, content] of Object.entries(deployFiles)) {
                  const key = filePath.startsWith("/") ? filePath : `/${filePath}`;
                  next[key] = { code: content };
                }
                setFiles((prev) => ({ ...prev, ...next }));
                const main =
                  next["/src/App.jsx"] || next["/App.js"] || next["/App.jsx"];
                if (main) {
                  setActiveFile(
                    next["/src/App.jsx"] ? "/src/App.jsx" : next["/App.js"] ? "/App.js" : "/App.jsx",
                  );
                }
                setVersions((v) => [{ id: `v_${Date.now()}`, prompt: "Orchestration build", files: { ...next }, time: new Date().toLocaleTimeString() }, ...v]);
                addLog("Build completed! Files loaded into preview.", "success", "deploy");
                setTab("preview");
                setBuildPct(100);
                setIsBuilding(false);
                if (refreshUser) refreshUser();
              } else if (token) {
                const headers = { Authorization: `Bearer ${token}` };
                axios
                  .get(`${API}/projects/${projectIdFromUrl}/deploy/files`, { headers })
                  .then((r) => {
                    const f = r.data?.files || {};
                    if (Object.keys(f).length > 0) {
                      const loaded = {};
                      for (const [filePath, content] of Object.entries(f)) {
                        const key = filePath.startsWith("/") ? filePath : `/${filePath}`;
                        loaded[key] = { code: content };
                      }
                      setFiles((prev) => ({ ...prev, ...loaded }));
                      setVersions((v) => [{ id: `v_${Date.now()}`, prompt: "Orchestration build", files: { ...loaded }, time: new Date().toLocaleTimeString() }, ...v]);
                      setTab("preview");
                      addLog("Build completed! Files loaded from server.", "success", "deploy");
                    }
                  })
                  .catch(() => {});
                setBuildPct(100);
                setIsBuilding(false);
              } else {
                setBuildPct(100);
                setIsBuilding(false);
              }
            }
          } catch (_) {
            /* ignore */
          }
        };
        ws.onclose = () => {
          if (reconnectAttempts < maxReconnectAttempts) {
            const delay = Math.min(baseDelay * Math.pow(2, reconnectAttempts), 30000);
            reconnectAttempts++;
            reconnectTimeout = setTimeout(connect, delay);
          }
        };
        ws.onerror = () => {
          try {
            ws?.close();
          } catch (_) {
            /* ignore */
          }
        };
        reconnectAttempts = 0;
      } catch (_) {
        /* ignore */
      }
    };
    connect();
    return () => {
      clearTimeout(reconnectTimeout);
      try {
        if (ws) ws.close();
      } catch (_) {
        /* ignore */
      }
    };
  }, [projectIdFromUrl, API, token, addLog, refreshUser]);

  const updateStep = (name, status, detail = "") => {
    setSteps((prev) => {
      const idx = prev.findIndex((s) => s.name.toLowerCase() === String(name).toLowerCase());
      if (idx === -1) return [...prev, { id: `step-${Date.now()}`, name, status, detail }];
      const next = [...prev];
      next[idx] = { ...next[idx], status, detail: detail || next[idx].detail };
      return next;
    });
  };

  const exportFilesPayload = () => {
    const out = {};
    Object.entries(files).forEach(([name, { code }]) => {
      out[name] = code || "";
    });
    return out;
  };

  const downloadCode = () => {
    Object.entries(files).forEach(([name, { code }]) => {
      const blob = new Blob([code], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name.replace("/", "");
      a.click();
    });
    addLog("Files downloaded", "success", "export");
  };

  const handleExportDeploy = async () => {
    try {
      const res = await axios.post(`${API}/export/deploy`, { files: exportFilesPayload() }, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "crucibai-deploy.zip";
      a.click();
      URL.revokeObjectURL(url);
      addLog("Deploy ZIP downloaded.", "success", "export");
    } catch (e) {
      addLog(`Export failed: ${e.message}`, "error", "export");
    }
  };

  const downloadServerDeployZip = async () => {
    if (!projectIdFromUrl || !token) {
      addLog("Open a saved project to download the server deploy package.", "warning", "export");
      return;
    }
    setDeployZipBusy(true);
    try {
      const res = await axios.get(`${API}/projects/${projectIdFromUrl}/deploy/zip`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: "blob",
        timeout: 120000,
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "crucibai-deploy.zip";
      a.click();
      URL.revokeObjectURL(url);
      addLog("Deploy ZIP downloaded from project.", "success", "export");
    } catch (e) {
      addLog(`Server deploy ZIP: ${formatDeployErr(e)}`, "error", "export");
    } finally {
      setDeployZipBusy(false);
    }
  };

  const oneClickDeployPlatform = async (platform) => {
    if (!projectIdFromUrl || !token) {
      addLog("Save as a project first, then deploy.", "warning", "export");
      return;
    }
    setDeployOneClickBusy(platform);
    try {
      const res = await axios.post(`${API}/projects/${projectIdFromUrl}/deploy/${platform}`, {}, { headers: { Authorization: `Bearer ${token}` }, timeout: 120000 });
      const u = res.data?.url;
      if (u) {
        setProjectLiveUrl(u);
        addLog(`Live: ${u}`, "success", "export");
      } else {
        addLog(`${platform} deploy finished — check your dashboard for the URL.`, "info", "export");
      }
    } catch (e) {
      addLog(`${platform}: ${formatDeployErr(e)}`, "error", "export");
    } finally {
      setDeployOneClickBusy(null);
    }
  };

  const savePublishSettings = async () => {
    if (!projectIdFromUrl || !token) {
      addLog("Open a saved project to save publish settings.", "warning", "export");
      return;
    }
    setPublishSaveBusy(true);
    try {
      await axios.patch(
        `${API}/projects/${projectIdFromUrl}/publish-settings`,
        { custom_domain: publishCustomDomain.trim(), railway_project_url: publishRailwayUrl.trim() },
        { headers: { Authorization: `Bearer ${token}` } },
      );
      addLog("Publish settings saved.", "success", "export");
    } catch (e) {
      addLog(`Publish settings: ${formatDeployErr(e)}`, "error", "export");
    } finally {
      setPublishSaveBusy(false);
    }
  };

  const prepareRailwayDeploy = async () => {
    if (!projectIdFromUrl || !token) {
      addLog("Save as a project first.", "warning", "export");
      return;
    }
    setDeployRailwayBusy(true);
    setDeployRailwayErr(null);
    setDeployRailwaySteps(null);
    setDeployRailwayDashboard(null);
    try {
      const res = await axios.post(`${API}/projects/${projectIdFromUrl}/deploy/railway`, {}, { headers: { Authorization: `Bearer ${token}` }, timeout: 120000 });
      setDeployRailwaySteps(Array.isArray(res.data?.steps) ? res.data.steps : []);
      setDeployRailwayDashboard(typeof res.data?.dashboard_url === "string" ? res.data.dashboard_url : null);
      addLog("Railway package validated.", "success", "export");
    } catch (e) {
      setDeployRailwayErr(formatDeployErr(e));
      addLog(`Railway: ${formatDeployErr(e)}`, "error", "export");
    } finally {
      setDeployRailwayBusy(false);
    }
  };

  const handleCodeChange = (value) => {
    setFiles((prev) => ({
      ...prev,
      [activeFile]: { code: value },
    }));
  };

  const runBuild = async () => {
    if (!prompt.trim() || isBuilding) return;
    setIsBuilding(true);
    setBuildPct(2);
    setMessages((m) => [...m, { role: "user", content: prompt }]);
    addLog("Build started", "info", "build");
    updateStep("Planning", "running", "Creating build plan");

    const headers = {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
    const sessionId = taskIdFromUrl || `task_${Date.now()}`;
    try {
      const res = await fetch(`${API}/ai/build/iterative`, {
        method: "POST",
        headers,
        body: JSON.stringify({ message: prompt, session_id: sessionId }),
      });
      if (!res.ok || !res.body) throw new Error(`Build failed (${res.status})`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let streamDone = false;

      while (!streamDone) {
        const { value, done: rDone } = await reader.read();
        if (rDone) break;
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n").filter(Boolean);
        for (const line of lines) {
          let ev;
          try {
            ev = JSON.parse(line);
          } catch {
            continue;
          }
          if (ev.type === "start") {
            updateStep("Planning", "completed", `Build kind: ${ev.build_kind || "fullstack"}`);
            updateStep("Architecture", "running", "Executing iterative passes");
            setBuildPct(10);
            addLog(`Build kind: ${ev.build_kind || "fullstack"}`, "info", "build");
          }
          if (ev.type === "step_complete") {
            const stepName = ev.step || "Frontend";
            updateStep(stepName, "completed", `${Object.keys(ev.files || {}).length} files generated`);
            setFiles((prev) => ({ ...prev, ...(ev.files || {}) }));
            setBuildPct((p) => Math.min(90, p + 15));
            addLog(`Step completed: ${stepName}`, "info", "build");
          }
          if (ev.type === "done") {
            streamDone = true;
            const built = ev.files || {};
            setFiles((prev) => {
              const merged = { ...prev, ...built };
              setVersions((v) => [
                { id: `v_${Date.now()}`, prompt: prompt.slice(0, 80), files: merged, time: new Date().toLocaleTimeString() },
                ...v,
              ]);
              setMessages((m) => {
                const assistantMsg = { role: "assistant", content: `Done. Built ${Object.keys(built).length} files.` };
                const nextMessages = [...m, assistantMsg];
                const taskPayload = {
                  id: sessionId,
                  name: prompt.slice(0, 80) || "Build Task",
                  prompt,
                  status: "completed",
                  type: "build",
                  files: merged,
                  messages: nextMessages,
                  createdAt: existingTask?.createdAt || Date.now(),
                };
                if (existingTask) updateTask(sessionId, taskPayload);
                else addTask(taskPayload);
                return nextMessages;
              });
              return merged;
            });
            setBuildPct(100);
            updateStep("Deploy", "completed", "Workspace ready for preview and deploy");
            addLog(`Build complete: ${Object.keys(built).length} files`, "success", "build");
            setFilesReadyKey(`fk_${Date.now()}`);
            const newUrl = new URL(window.location.href);
            newUrl.searchParams.set("taskId", sessionId);
            window.history.replaceState({}, "", newUrl.toString());
            break;
          }
          if (ev.type === "error") {
            throw new Error(ev.error || "Build stream error");
          }
        }
      }
    } catch (e) {
      addLog(`Error: ${e.message}`, "error", "build");
      setMessages((m) => [...m, { role: "assistant", content: `Build failed: ${e.message}` }]);
      updateStep("Validation", "failed", e.message);
    } finally {
      setIsBuilding(false);
    }
  };

  const proPanel = (
    <WorkspaceProPanels
      activePanel={tab}
      projectIdFromUrl={projectIdFromUrl}
      token={token}
      serverDbErr={serverDbErr}
      serverDbLoading={serverDbLoading}
      serverDbSnapshots={serverDbSnapshots}
      dbPanelMerge={dbPanelMerge}
      setFiles={setFiles}
      setActiveFile={setActiveFile}
      setActivePanel={setTab}
      serverDocsErr={serverDocsErr}
      serverDocsLoading={serverDocsLoading}
      mergedDocFiles={mergedDocFiles}
      docsSelectedPath={docsSelectedPath}
      setDocsSelectedPath={setDocsSelectedPath}
      analyticsErr={analyticsErr}
      analyticsLoading={analyticsLoading}
      analyticsData={analyticsData}
      buildHistoryList={buildHistoryList}
      buildTimelineEvents={buildTimelineEvents}
      agentsActivity={agentsActivity}
      agentApiStatuses={agentApiStatuses}
      projectSandboxErr={projectSandboxErr}
      projectSandboxLoading={projectSandboxLoading}
      projectSandboxLogs={projectSandboxLogs}
      files={files}
      versions={versions}
      buildHistoryLoading={buildHistoryLoading}
      isBuilding={isBuilding}
      sandpackFiles={sandpackFiles}
      projectBuildProgress={projectBuildProgress}
      currentPhase={currentPhase}
    />
  );

  return (
    <div className="mw-shell">
      <div className="mw-center">
        <div className="mw-header">
          <div>
            <h1 className="mw-title">CrucibAI Workspace</h1>
            <p className="mw-subtitle">
              {projectIdFromUrl ? `Project ${projectIdFromUrl.slice(0, 8)}…` : "Task-first build flow with visible execution"}
            </p>
          </div>
          <div className="mw-header-right">
            <span className="mw-badge">{isBuilding ? `Building ${buildPct}%` : "Idle"}</span>
            <div className="mw-mode">
              <button type="button" className={mode === "guided" ? "active" : ""} onClick={() => setMode("guided")}>
                Guided
              </button>
              <button type="button" className={mode === "pro" ? "active" : ""} onClick={() => setMode("pro")}>
                Pro
              </button>
            </div>
          </div>
        </div>

        <div className="mw-content">
          <div className="mw-transcript">
            {messages.map((m, i) => (
              <div key={`${m.role}-${i}`} className={`mw-msg ${m.role}`}>
                <div className="mw-msg-role">{m.role === "user" ? "You" : "CrucibAI"}</div>
                <div className="mw-msg-body">{m.content}</div>
              </div>
            ))}
          </div>
          <div className="mw-steps">
            {steps.map((s) => (
              <div key={s.id} className={`mw-step ${s.status}`}>
                <div className="mw-step-name">{s.name}</div>
                <div className="mw-step-meta">
                  {s.status}
                  {s.detail ? ` · ${s.detail}` : ""}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mw-composer">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Build me a multi-page website with dashboard, database, and deploy flow..."
          />
          <div className="mw-composer-actions">
            <button type="button" onClick={() => navigate("/app")} className="ghost">
              Back to chat
            </button>
            {projectIdFromUrl && token && (
              <button type="button" className="ghost" onClick={reloadWorkspaceFromServer}>
                Reload workspace
              </button>
            )}
            <button type="button" onClick={runBuild} disabled={isBuilding || !prompt.trim()}>
              {isBuilding ? "Building..." : "Build"}
            </button>
          </div>
        </div>
      </div>

      <div className="mw-right">
        <div className="mw-tabs">
          {visibleTabs.map((t) => (
            <button key={t} type="button" className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
        </div>
        <div className="mw-panel">
          {tab === "preview" && (
            <SandpackProvider
              key={filesReadyKey}
              files={sandpackFiles}
              theme={document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark"}
              template="react"
              customSetup={{ dependencies: sandpackDeps }}
              options={{
                externalResources: [
                  "https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css",
                  "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
                ],
                autoReload: true,
                recompileMode: "delayed",
                recompileDelay: 500,
              }}
            >
              <SandpackErrorBoundary
                onError={(e) => {
                  addLog(`Preview error: ${e}`, "error", "preview");
                }}
              >
                <div style={{ flex: 1, minHeight: 320, display: "flex", flexDirection: "column", background: "var(--theme-surface2, #111)" }}>
                  <SandpackPreview showOpenInCodeSandbox={false} style={{ flex: 1, minHeight: 300, width: "100%" }} />
                </div>
              </SandpackErrorBoundary>
            </SandpackProvider>
          )}

          {tab === "code" && (
            <div className="flex flex-col h-full min-h-0">
              <div
                className="flex overflow-x-auto shrink-0 border-b"
                style={{ background: "var(--theme-surface, #18181B)", borderColor: "var(--theme-border, rgba(255,255,255,0.07))" }}
              >
                {Object.keys(files).map((fp) => (
                  <button
                    key={fp}
                    type="button"
                    onClick={() => setActiveFile(fp)}
                    className="px-3 py-2 text-xs whitespace-nowrap shrink-0 border-r transition"
                    style={{
                      background: activeFile === fp ? "var(--theme-bg, #111113)" : "transparent",
                      color: activeFile === fp ? "var(--theme-text, #e4e4e7)" : "var(--theme-muted, #71717a)",
                      borderColor: "var(--theme-border, rgba(255,255,255,0.06))",
                    }}
                  >
                    {fp.replace(/^\//, "")}
                  </button>
                ))}
              </div>
              <div className="flex-1 min-h-0">
                <Editor
                  height="100%"
                  language={
                    activeFile.endsWith(".css")
                      ? "css"
                      : activeFile.endsWith(".html")
                        ? "html"
                        : activeFile.endsWith(".json")
                          ? "json"
                          : activeFile.endsWith(".tsx")
                            ? "typescript"
                            : activeFile.endsWith(".ts")
                              ? "typescript"
                              : "javascript"
                  }
                  value={files[activeFile]?.code || ""}
                  onChange={handleCodeChange}
                  theme="vs-dark"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    lineNumbers: "on",
                    scrollBeyondLastLine: false,
                    wordWrap: "on",
                    tabSize: 2,
                    padding: { top: 12 },
                    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                  }}
                />
              </div>
            </div>
          )}

          {tab === "files" && (
            <div className="mw-list" style={{ padding: 12 }}>
              {Object.keys(files)
                .sort()
                .map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => {
                      setActiveFile(p);
                      setTab("code");
                    }}
                    style={{
                      display: "block",
                      width: "100%",
                      textAlign: "left",
                      padding: "8px 10px",
                      marginBottom: 4,
                      background: "rgba(255,255,255,0.04)",
                      border: "1px solid rgba(255,255,255,0.08)",
                      borderRadius: 8,
                      color: "var(--theme-text, #e4e4e7)",
                      cursor: "pointer",
                    }}
                  >
                    {p.replace(/^\//, "")}
                  </button>
                ))}
            </div>
          )}

          {tab === "console" && (
            <div className="flex flex-col h-full min-h-0">
              <div
                className="shrink-0 flex flex-wrap items-center gap-1.5 px-3 py-2 border-b"
                style={{ borderColor: "var(--theme-border, rgba(255,255,255,0.07))" }}
              >
                {[
                  { id: "all", label: "All" },
                  { id: "error", label: "Errors" },
                  { id: "build", label: "Build" },
                  { id: "system", label: "System" },
                ].map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => setConsoleFilter(f.id)}
                    className="text-[10px] px-2 py-0.5 rounded-md font-medium transition"
                    style={{
                      background: consoleFilter === f.id ? "rgba(255,255,255,0.12)" : "transparent",
                      color: consoleFilter === f.id ? "var(--theme-text)" : "var(--theme-muted)",
                      border: `1px solid ${consoleFilter === f.id ? "var(--theme-border)" : "transparent"}`,
                    }}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
              <div className="flex-1 min-h-0">
                <ConsolePanel logs={filteredConsoleLogs} placeholder="Build logs appear here." />
              </div>
            </div>
          )}

          {tab === "dashboard" && (
            <div className="flex-1 overflow-y-auto p-4 space-y-3" style={{ color: "var(--theme-text)" }}>
              <div className="rounded-xl p-4 border" style={{ background: "var(--theme-surface2, #111)", borderColor: "var(--theme-border)" }}>
                <div className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--theme-muted)" }}>
                  Workspace
                </div>
                <div className="text-sm font-medium">{user?.email || "Guest"}</div>
                <div className="mt-3 pt-3 border-t flex gap-4 text-xs" style={{ borderColor: "var(--theme-border)" }}>
                  <div>
                    <span style={{ color: "var(--theme-muted)" }}>Files</span>
                    <span className="ml-2 font-medium">{Object.keys(files).length}</span>
                  </div>
                  <div>
                    <span style={{ color: "var(--theme-muted)" }}>Versions</span>
                    <span className="ml-2 font-medium">{versions.length}</span>
                  </div>
                  <div>
                    <span style={{ color: "var(--theme-muted)" }}>Events</span>
                    <span className="ml-2 font-medium">{buildTimelineEvents.length}</span>
                  </div>
                </div>
                {buildEventsErr && <div className="text-xs mt-2 text-amber-300">{buildEventsErr}</div>}
              </div>
              <div className="rounded-xl p-4 border" style={{ background: "var(--theme-surface2)", borderColor: "var(--theme-border)" }}>
                <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--theme-muted)" }}>
                  Publish &amp; Deploy
                </div>
                {projectLiveUrl && (
                  <a
                    href={projectLiveUrl.startsWith("http") ? projectLiveUrl : `https://${projectLiveUrl}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold mb-2 transition hover:bg-white/5 border"
                    style={{ borderColor: "rgba(74,222,128,0.35)", color: "#86efac" }}
                  >
                    <Globe className="w-3.5 h-3.5 shrink-0" /> Live site
                  </a>
                )}
                <button
                  type="button"
                  onClick={() => setShowDeployModal(true)}
                  disabled={Object.keys(files).length === 0}
                  className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs font-semibold transition disabled:opacity-40"
                  style={{ background: "var(--theme-accent, #6366f1)", color: "white" }}
                >
                  <Rocket className="w-3.5 h-3.5" /> Deploy App
                </button>
              </div>
            </div>
          )}

          {tab === "deploy" && (
            <div className="flex-1 overflow-y-auto p-4 space-y-3" style={{ color: "var(--theme-text)" }}>
              <p className="text-sm" style={{ color: "var(--theme-muted)" }}>
                Export from the editor or use your linked project for one-click deploy (Vercel / Netlify / Railway).
              </p>
              <button
                type="button"
                onClick={() => setShowDeployModal(true)}
                disabled={Object.keys(files).length === 0}
                className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs font-semibold transition disabled:opacity-40"
                style={{ background: "var(--theme-accent, #6366f1)", color: "white" }}
              >
                <Rocket className="w-3.5 h-3.5" /> Open deploy modal
              </button>
              <button
                type="button"
                onClick={handleExportDeploy}
                className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs font-medium transition hover:bg-white/5 border"
                style={{ borderColor: "var(--theme-border)", color: "var(--theme-text)" }}
              >
                <Download className="w-3.5 h-3.5" /> Deploy-ready ZIP (API)
              </button>
            </div>
          )}

          {tab === "graph" && (
            <div className="mw-list" style={{ padding: 12 }}>
              {steps.map((s) => (
                <div key={s.id} style={{ marginBottom: 8 }}>
                  {s.name} → {s.status}
                  {s.detail ? ` (${s.detail})` : ""}
                </div>
              ))}
            </div>
          )}

          {["database", "docs", "analytics", "agents", "passes", "sandbox"].includes(tab) && (
            <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
              {proPanel}
            </div>
          )}
        </div>
      </div>

      {showDeployModal && (
        <div className="fixed inset-0 z-[300] flex items-center justify-center" style={{ background: "rgba(0,0,0,0.75)" }} onClick={() => setShowDeployModal(false)}>
          <div
            className="rounded-2xl shadow-2xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto p-6 border"
            style={{ background: "var(--theme-surface, #1C1C1E)", borderColor: "var(--theme-border, rgba(255,255,255,0.1))" }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-white mb-1">Deploy your app</h3>
            <p className="text-sm mb-4" style={{ color: "var(--theme-muted, #71717a)" }}>
              Use your saved project for server packages and one-click deploy, or export from the editor.
            </p>
            {projectLiveUrl && (
              <a
                href={projectLiveUrl.startsWith("http") ? projectLiveUrl : `https://${projectLiveUrl}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-semibold mb-4 transition hover:opacity-90"
                style={{ background: "rgba(74,222,128,0.15)", color: "#86efac", border: "1px solid rgba(74,222,128,0.35)" }}
              >
                <Globe className="w-4 h-4" /> Open live site
              </a>
            )}
            {projectIdFromUrl && token && (
              <div className="mb-4 space-y-2">
                <div className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--theme-muted)" }}>
                  This project (API)
                </div>
                <button
                  type="button"
                  onClick={downloadServerDeployZip}
                  disabled={deployZipBusy}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition hover:bg-white/5 border disabled:opacity-50"
                  style={{ borderColor: "var(--theme-border, rgba(255,255,255,0.1))", color: "var(--theme-text, #e4e4e7)" }}
                >
                  {deployZipBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                  Download deploy ZIP (server build)
                </button>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => oneClickDeployPlatform("vercel")}
                    disabled={!!deployOneClickBusy}
                    className="flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-white hover:opacity-90 transition disabled:opacity-50"
                    style={{ background: "#000" }}
                  >
                    {deployOneClickBusy === "vercel" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                    Vercel
                  </button>
                  <button
                    type="button"
                    onClick={() => oneClickDeployPlatform("netlify")}
                    disabled={!!deployOneClickBusy}
                    className="flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-white hover:opacity-90 transition disabled:opacity-50"
                    style={{ background: "#00AD9F" }}
                  >
                    {deployOneClickBusy === "netlify" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                    Netlify
                  </button>
                </div>
                <div className="pt-2 border-t space-y-2" style={{ borderColor: "var(--theme-border, rgba(255,255,255,0.08))" }}>
                  <div className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--theme-muted)" }}>
                    Railway &amp; custom domain
                  </div>
                  <input
                    type="text"
                    value={publishCustomDomain}
                    onChange={(e) => setPublishCustomDomain(e.target.value)}
                    placeholder="app.example.com"
                    autoComplete="off"
                    className="w-full px-3 py-2 rounded-lg text-sm border bg-transparent"
                    style={{ borderColor: "var(--theme-border, rgba(255,255,255,0.12))", color: "var(--theme-text)" }}
                  />
                  <input
                    type="url"
                    value={publishRailwayUrl}
                    onChange={(e) => setPublishRailwayUrl(e.target.value)}
                    placeholder="https://railway.app/project/…"
                    autoComplete="off"
                    className="w-full px-3 py-2 rounded-lg text-sm border bg-transparent"
                    style={{ borderColor: "var(--theme-border, rgba(255,255,255,0.12))", color: "var(--theme-text)" }}
                  />
                  <button
                    type="button"
                    onClick={savePublishSettings}
                    disabled={publishSaveBusy}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition hover:bg-white/5 border disabled:opacity-50"
                    style={{ borderColor: "var(--theme-border)", color: "var(--theme-text)" }}
                  >
                    {publishSaveBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                    Save publish settings
                  </button>
                  <button
                    type="button"
                    onClick={prepareRailwayDeploy}
                    disabled={deployRailwayBusy}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-white transition disabled:opacity-50"
                    style={{ background: "#0B0D0E", border: "1px solid rgba(255,255,255,0.15)" }}
                  >
                    {deployRailwayBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Rocket className="w-3.5 h-3.5" />}
                    Validate for Railway (ZIP + CLI steps)
                  </button>
                  {deployRailwayErr && (
                    <div className="text-[11px] px-2 py-1.5 rounded-lg" style={{ background: "rgba(248,113,113,0.12)", color: "#fca5a5" }}>
                      {deployRailwayErr}
                    </div>
                  )}
                  {deployRailwaySteps && deployRailwaySteps.length > 0 && (
                    <div className="rounded-lg p-3 border text-[11px] space-y-2" style={{ borderColor: "var(--theme-border)", color: "var(--theme-muted)" }}>
                      <div className="font-semibold uppercase tracking-wider text-[10px]" style={{ color: "var(--theme-muted)" }}>
                        Next steps
                      </div>
                      <ol className="list-decimal pl-4 space-y-1">
                        {deployRailwaySteps.map((s, i) => (
                          <li key={i} style={{ color: "var(--theme-text)" }}>
                            {s}
                          </li>
                        ))}
                      </ol>
                      <button
                        type="button"
                        onClick={() => window.open(deployRailwayDashboard || "https://railway.app/new", "_blank", "noopener,noreferrer")}
                        className="w-full mt-1 py-2 rounded-lg text-xs font-semibold text-white"
                        style={{ background: "#0B0D0E", border: "1px solid rgba(255,255,255,0.15)" }}
                      >
                        Open Railway dashboard
                      </button>
                    </div>
                  )}
                </div>
                {(!deployTokensHint.has_vercel || !deployTokensHint.has_netlify) && (
                  <p className="text-[11px] leading-snug" style={{ color: "var(--theme-muted)" }}>
                    One-click needs tokens in{" "}
                    <Link to="/app/settings" className="underline font-medium" style={{ color: "var(--theme-accent)" }}>
                      Settings → Deploy integrations
                    </Link>
                    .
                  </p>
                )}
              </div>
            )}
            <div className="text-[10px] font-semibold uppercase tracking-wider mb-2 pt-1 border-t" style={{ color: "var(--theme-muted)", borderColor: "var(--theme-border, rgba(255,255,255,0.08))" }}>
              Editor export &amp; hosts
            </div>
            <div className="flex flex-col gap-2">
              <button type="button" onClick={downloadCode} className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition hover:bg-white/5 border" style={{ borderColor: "var(--theme-border, rgba(255,255,255,0.1))", color: "var(--theme-text, #e4e4e7)" }}>
                <Download className="w-4 h-4" /> Download ZIP (current editor)
              </button>
              <button type="button" onClick={handleExportDeploy} className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition hover:bg-white/5 border" style={{ borderColor: "var(--theme-border, rgba(255,255,255,0.1))", color: "var(--theme-text, #e4e4e7)" }}>
                <Rocket className="w-4 h-4" /> Deploy-ready ZIP (API from editor)
              </button>
              <a href="https://vercel.com/new" target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium text-white hover:opacity-90 transition" style={{ background: "#000" }}>
                Vercel (upload)
              </a>
              <a href="https://app.netlify.com/drop" target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium text-white hover:opacity-90 transition" style={{ background: "#00AD9F" }}>
                Netlify Drop
              </a>
              <a href="https://railway.app/new" target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium text-white hover:opacity-90 transition" style={{ background: "#0B0D0E", border: "1px solid rgba(255,255,255,0.15)" }}>
                Railway
              </a>
            </div>
            <button type="button" onClick={() => setShowDeployModal(false)} className="mt-4 w-full py-2 text-sm rounded-xl border transition hover:bg-white/5" style={{ color: "var(--theme-muted, #71717a)", borderColor: "var(--theme-border, rgba(255,255,255,0.1))" }}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
