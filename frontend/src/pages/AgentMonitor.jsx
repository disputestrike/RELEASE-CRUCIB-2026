import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Bot, CheckCircle, Clock, AlertCircle, Play, Pause,
  Zap, ArrowLeft, ExternalLink, Download, RefreshCw, ChevronDown, ChevronRight, Database, Code, List, Eye, ShieldCheck
} from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';
import BuildProgress from '../components/BuildProgress';
import QualityScore from '../components/QualityScore';

const AgentMonitor = () => {
  const { id } = useParams();
  const { token } = useAuth();
  
  const [project, setProject] = useState(null);
  const [agents, setAgents] = useState([]);
  const [phases, setPhases] = useState([]);
  const [logs, setLogs] = useState([]);
  const [projectState, setProjectState] = useState(null);
  const [statePanelOpen, setStatePanelOpen] = useState(false);
  const [buildEvents, setBuildEvents] = useState([]);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [workspaceFiles, setWorkspaceFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(true);
  const [retrying, setRetrying] = useState(false);
  const [dependencyAudit, setDependencyAudit] = useState(null);
  const [dependencyAuditLoading, setDependencyAuditLoading] = useState(false);

  const agentLayers = {
    planning: ['Planner', 'Requirements Clarifier', 'Stack Selector'],
    execution: ['Frontend Generation', 'Backend Generation', 'Database Agent', 'API Integration', 'Test Generation'],
    validation: ['Security Checker', 'Test Executor', 'UX Auditor', 'Performance Analyzer'],
    deployment: ['Deployment Agent', 'Error Recovery', 'Memory Agent']
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [projectRes, agentsRes, logsRes, phasesRes] = await Promise.all([
          axios.get(`${API}/projects/${id}`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/agents/status/${id}`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/projects/${id}/logs`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/projects/${id}/phases`, { headers: { Authorization: `Bearer ${token}` } }).catch(() => ({ data: { phases: [] } }))
        ]);
        setProject(projectRes.data.project);
        setAgents(agentsRes.data.statuses);
        setLogs(logsRes.data.logs);
        setPhases(phasesRes.data?.phases || []);
        try {
          const stateRes = await axios.get(`${API}/projects/${id}/state`, { headers: { Authorization: `Bearer ${token}` } });
          setProjectState(stateRes.data?.state || null);
        } catch (_) {
          setProjectState(null);
        }
        try {
          const eventsRes = await axios.get(`${API}/projects/${id}/events/snapshot`, { headers: { Authorization: `Bearer ${token}` } });
          setBuildEvents(eventsRes.data?.events || []);
        } catch (_) {
          setBuildEvents([]);
        }
        try {
          const filesRes = await axios.get(`${API}/projects/${id}/workspace/files`, { headers: { Authorization: `Bearer ${token}` } });
          setWorkspaceFiles(filesRes.data?.files || []);
        } catch (_) {
          setWorkspaceFiles([]);
        }
        if (projectRes.data.project.status === 'completed' || projectRes.data.project.status === 'failed') {
          setPolling(false);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    
    let interval;
    if (polling) {
      interval = setInterval(fetchData, 2000);
    }
    
    return () => clearInterval(interval);
  }, [id, token, polling]);

  useEffect(() => {
    if (!project?.id || !token) return;
    axios.get(`${API}/projects/${id}/preview-token`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => setPreviewUrl(r.data?.url || null))
      .catch(() => setPreviewUrl(null));
  }, [id, project?.id, token]);

  const getAgentStatus = (agentName) => {
    return agents.find(a => a.agent_name === agentName) || { status: 'idle', progress: 0, tokens_used: 0 };
  };

  const handleRetryPhase = async () => {
    if (retrying || !project?.suggest_retry_phase) return;
    setRetrying(true);
    try {
      await axios.post(`${API}/projects/${id}/retry-phase`, {}, { headers: { Authorization: `Bearer ${token}` } });
      setPolling(true);
      const projectRes = await axios.get(`${API}/projects/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      setProject(projectRes.data.project);
    } catch (e) {
      console.error(e);
    } finally {
      setRetrying(false);
    }
  };

  const getLayerColor = (layer) => {
    switch (layer) {
      case 'planning': return 'blue';
      case 'execution': return 'green';
      case 'validation': return 'purple';
      case 'deployment': return 'orange';
      default: return 'gray';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-gray-400">Loading project...</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="text-center py-20">
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">Project not found</h2>
        <Link to="/app" className="text-blue-400 hover:text-blue-300">Back to dashboard</Link>
      </div>
    );
  }

  const completedAgents = agents.filter(a => a.status === 'completed').length;
  const totalAgents = 20;
  const progress = Math.round((completedAgents / totalAgents) * 100);

  return (
    <div className="space-y-6" data-testid="agent-monitor">
      {project.status === 'running' && (
        <BuildProgress projectId={id} apiBaseUrl={(API || '').replace(/\/api\/?$/, '')} />
      )}
      {/* Generated images + videos when build completed */}
      {project.status === 'completed' && (project.images || project.videos) && (
        <div className="p-4 rounded-xl border border-white/10 bg-[#0a0a0a]">
          <h3 className="text-sm font-medium text-gray-400 mb-3">Generated media</h3>
          {project.images && Object.keys(project.images).length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
              {project.images.hero && (
                <div>
                  <p className="text-xs text-gray-500 mb-2">Hero image</p>
                  <img src={project.images.hero} alt="Hero" className="w-full h-32 object-cover rounded-lg border border-white/10" />
                </div>
              )}
              {project.images.feature_1 && (
                <div>
                  <p className="text-xs text-gray-500 mb-2">Feature 1</p>
                  <img src={project.images.feature_1} alt="Feature 1" className="w-full h-32 object-cover rounded-lg border border-white/10" />
                </div>
              )}
              {project.images.feature_2 && (
                <div>
                  <p className="text-xs text-gray-500 mb-2">Feature 2</p>
                  <img src={project.images.feature_2} alt="Feature 2" className="w-full h-32 object-cover rounded-lg border border-white/10" />
                </div>
              )}
            </div>
          )}
          {project.videos && project.videos.hero && (
            <div>
              <p className="text-xs text-gray-500 mb-2">Hero video</p>
              <video src={project.videos.hero} autoPlay muted loop playsInline className="w-full h-48 object-cover rounded-lg border border-white/10" />
            </div>
          )}
          {project.videos && project.videos.feature && (
            <div className="mt-3">
              <p className="text-xs text-gray-500 mb-2">Feature video</p>
              <video src={project.videos.feature} autoPlay muted loop playsInline className="w-full h-48 object-cover rounded-lg border border-white/10" />
            </div>
          )}
        </div>
      )}
      {/* Quality score (0–100 + breakdown) when build completed */}
      {project.status === 'completed' && project.quality_score && (
        <div className="p-4 rounded-xl border border-white/10 bg-[#0a0a0a]">
          <h3 className="text-sm font-medium text-gray-400 mb-2">Code quality</h3>
          <QualityScore score={project.quality_score} />
        </div>
      )}
      {/* Security scan summary (from last run in Workspace) */}
      {project.last_security_scan && (project.last_security_scan.passed != null || project.last_security_scan.failed != null) && (
        <div className="p-4 rounded-xl border border-white/10 bg-[#0a0a0a]">
          <h3 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4" /> Security scan
          </h3>
          <p className="text-sm text-gray-300">
            {project.last_security_scan.passed ?? 0} PASS, {project.last_security_scan.failed ?? 0} FAIL
            {project.last_security_scan.at && (
              <span className="text-gray-500 ml-2">(last run from Workspace)</span>
            )}
          </p>
          <Link to={`/app/workspace?projectId=${id}`} className="text-sm text-blue-400 hover:text-blue-300 mt-1 inline-block">Run again in Workspace →</Link>
        </div>
      )}
      {/* Optional: dependency audit (npm / pip) */}
      {(project.status === 'completed' || workspaceFiles.length > 0) && (
        <div className="p-4 rounded-xl border border-white/10 bg-[#0a0a0a]">
          <h3 className="text-sm font-medium text-gray-400 mb-2">Dependency audit</h3>
          {dependencyAuditLoading && <p className="text-sm text-gray-500">Running npm/pip audit…</p>}
          {!dependencyAuditLoading && !dependencyAudit && (
            <button
              type="button"
              onClick={async () => {
                setDependencyAuditLoading(true);
                try {
                  const { data } = await axios.get(`${API}/projects/${id}/dependency-audit`, { headers: { Authorization: `Bearer ${token}` } });
                  setDependencyAudit(data);
                } catch (_) {
                  setDependencyAudit({ npm: { error: 'Request failed' }, pip: null });
                } finally {
                  setDependencyAuditLoading(false);
                }
              }}
              className="text-sm text-blue-400 hover:text-blue-300"
            >
              Run dependency audit (npm / pip)
            </button>
          )}
          {!dependencyAuditLoading && dependencyAudit && (
            <div className="text-sm text-gray-300 space-y-1">
              {dependencyAudit.npm && (
                <p>
                  npm: {dependencyAudit.npm.error ? dependencyAudit.npm.error : `${dependencyAudit.npm.critical ?? 0} critical, ${dependencyAudit.npm.high ?? 0} high`}
                  {dependencyAudit.npm.ok && !dependencyAudit.npm.error && ' — OK'}
                </p>
              )}
              {dependencyAudit.pip && (
                <p>
                  pip: {dependencyAudit.pip.error ? dependencyAudit.pip.error : `${dependencyAudit.pip.critical ?? 0} critical, ${dependencyAudit.pip.high ?? 0} high`}
                  {dependencyAudit.pip.ok && !dependencyAudit.pip.error && ' — OK'}
                </p>
              )}
              {(!dependencyAudit.npm && !dependencyAudit.pip) && dependencyAudit.message && <p>{dependencyAudit.message}</p>}
            </div>
          )}
        </div>
      )}
      {/* 10/10: Phase retry suggestion when Quality phase had many failures */}
      {project.status === 'completed' && (project.suggest_retry_phase != null || project.suggest_retry_reason) && (
        <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 flex flex-wrap items-center justify-between gap-3">
          <p className="text-amber-200 text-sm">
            {project.suggest_retry_reason || 'Quality checks had issues. Retry code generation?'}
          </p>
          <button
            onClick={handleRetryPhase}
            disabled={retrying}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500 text-black font-medium hover:bg-amber-400 transition disabled:opacity-50"
          >
            {retrying ? <RefreshCw className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            {retrying ? 'Starting…' : 'Retry code generation'}
          </button>
        </div>
      )}
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link to="/app" className="p-2 hover:bg-white/10 rounded-lg transition">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold">{project.name}</h1>
            <p className="text-gray-400">{project.project_type}{project.build_kind === 'mobile' ? ' · Mobile (Expo)' : ''}</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {project.build_kind === 'mobile' && (
            <span className="px-3 py-1.5 rounded-full text-sm font-medium bg-violet-500/20 text-violet-300" data-testid="mobile-badge">
              Mobile project — includes App Store &amp; Play Store guide
            </span>
          )}
          <span className={`px-3 py-1.5 rounded-full text-sm font-medium ${
            project.status === 'completed' ? 'bg-green-500/20 text-green-400' :
            project.status === 'running' ? 'bg-blue-500/20 text-blue-400' :
            project.status === 'failed' ? 'bg-red-500/20 text-red-400' :
            'bg-gray-500/20 text-gray-400'
          }`} data-testid="project-status">
            {project.status === 'running' && <span className="inline-block w-2 h-2 bg-blue-400 rounded-full mr-2 animate-pulse"></span>}
            {project.status}
          </span>
          {project.status === 'running' && (
            <BuildProgress projectId={id} apiBaseUrl={(API || '').replace(/\/api\/?$/, '')} />
          )}
          {project.live_url && (
            <a
              href={project.live_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 rounded-lg font-medium transition"
              data-testid="live-url-btn"
            >
              <ExternalLink className="w-4 h-4" />
              View Live
            </a>
          )}
          <Link
            to={`/app/workspace?projectId=${id}`}
            className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg font-medium transition border border-white/20"
          >
            <Code className="w-4 h-4" />
            Open in Workspace
          </Link>
        </div>
      </div>

      {/* Live preview (workspace files served with preview token) */}
      {previewUrl && (
        <div className="p-4 rounded-xl border border-white/10 bg-[#0a0a0a]">
          <h3 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
            <Eye className="w-4 h-4" /> Live preview (workspace)
          </h3>
          <div className="rounded-lg overflow-hidden border border-white/10 bg-black" style={{ minHeight: 280 }}>
            <iframe
              title="Preview"
              src={previewUrl}
              className="w-full h-[280px] border-0"
              sandbox="allow-scripts"
            />
          </div>
        </div>
      )}

      {/* Event timeline (SSE-style: agent_started, agent_completed) */}
      {buildEvents.length > 0 && (
        <div className="p-4 rounded-xl border border-white/10 bg-[#0a0a0a]">
          <h3 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
            <List className="w-4 h-4" /> Event timeline
          </h3>
          <div className="max-h-48 overflow-y-auto space-y-1 text-xs font-mono">
            {buildEvents.slice(-80).map((ev, i) => (
              <div key={ev.id ?? i} className="flex gap-2 text-gray-300">
                <span className="text-gray-500 shrink-0">{ev.ts ? new Date(ev.ts).toLocaleTimeString() : ''}</span>
                <span className={ev.type === 'agent_completed' ? 'text-green-400' : ev.type === 'agent_started' ? 'text-blue-400' : 'text-amber-400'}>
                  {ev.type === 'agent_started' && `${ev.agent || 'agent'} started`}
                  {ev.type === 'agent_completed' && `${ev.agent || 'agent'} completed`}
                  {ev.type === 'phase_started' && (ev.message || 'phase')}
                  {ev.type === 'build_started' && 'Build started'}
                  {ev.type === 'build_completed' && `Build ${ev.status || 'done'}`}
                  {!['agent_started','agent_completed','phase_started','build_started','build_completed'].includes(ev.type) && (ev.message || ev.type)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Progress */}
      <div className="p-6 bg-[#0a0a0a] rounded-xl border border-white/10">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold">Generation Progress</h3>
            <p className="text-sm text-gray-500">{completedAgents} of {totalAgents} agents completed</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm text-gray-500">Total tokens this run</p>
              <p className="font-bold text-lg flex items-center gap-1">
                <Zap className="w-4 h-4 text-yellow-500" />
                {(agents.reduce((sum, a) => sum + (a.tokens_used || 0), 0) || project.tokens_used || 0).toLocaleString()}
              </p>
            </div>
          </div>
        </div>
        
        <div className="relative h-3 bg-white/10 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            className={`absolute inset-y-0 left-0 rounded-full ${
              project.status === 'completed' ? 'bg-green-500' :
              project.status === 'failed' ? 'bg-red-500' :
              'bg-blue-500'
            }`}
          />
        </div>
        <p className="text-right text-sm text-gray-500 mt-2">{progress}%</p>

        {phases.length > 0 && (
          <div className="mt-4 pt-4 border-t border-white/10">
            <h4 className="text-sm font-medium text-gray-400 mb-2">Build phases</h4>
            <div className="flex flex-wrap gap-2">
              {phases.map((p, i) => (
                <span key={i} className="px-2 py-1 rounded bg-white/10 text-gray-300 text-xs">{typeof p === 'string' ? p : p?.name || p?.title || JSON.stringify(p)}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Agent Grid */}
      <div className="grid lg:grid-cols-2 gap-6">
        {Object.entries(agentLayers).map(([layer, layerAgents]) => {
          const color = getLayerColor(layer);
          return (
            <div key={layer} className="p-6 bg-[#0a0a0a] rounded-xl border border-white/10">
              <h3 className={`text-lg font-semibold mb-4 capitalize flex items-center gap-2 text-${color}-400`}>
                <div className={`w-3 h-3 rounded-full bg-${color}-400`}></div>
                {layer} Layer
              </h3>
              <div className="space-y-3">
                {layerAgents.map(agentName => {
                  const agent = getAgentStatus(agentName);
                  return (
                    <motion.div
                      key={agentName}
                      layout
                      className={`p-4 rounded-lg border transition-all ${
                        agent.status === 'completed' ? 'bg-green-500/10 border-green-500/30' :
                        agent.status === 'running' ? `bg-${color}-500/10 border-${color}-500/30` :
                        agent.status === 'failed' ? 'bg-red-500/10 border-red-500/30' :
                        'bg-white/5 border-white/10'
                      }`}
                      data-testid={`agent-${agentName.toLowerCase().replace(/ /g, '-')}`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                            agent.status === 'completed' ? 'bg-green-500/20' :
                            agent.status === 'running' ? `bg-${color}-500/20` :
                            'bg-white/10'
                          }`}>
                            {agent.status === 'completed' ? <CheckCircle className="w-4 h-4 text-green-400" /> :
                             agent.status === 'running' ? <Bot className={`w-4 h-4 text-${color}-400 animate-pulse`} /> :
                             agent.status === 'failed' ? <AlertCircle className="w-4 h-4 text-red-400" /> :
                             <Clock className="w-4 h-4 text-gray-500" />}
                          </div>
                          <span className="font-medium">{agentName}</span>
                        </div>
                        <span className="text-sm text-gray-500">
                          {agent.tokens_used?.toLocaleString() || 0} tokens
                        </span>
                      </div>
                      {agent.status === 'running' && (
                        <div className="relative h-1.5 bg-white/10 rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${agent.progress}%` }}
                            className={`absolute inset-y-0 left-0 bg-${color}-500 rounded-full`}
                          />
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Build state (plan, requirements, stack, tool_log) — demo of real agent outputs */}
      <div className="p-6 bg-[#0a0a0a] rounded-xl border border-white/10">
        <button
          type="button"
          onClick={() => setStatePanelOpen((o) => !o)}
          className="flex items-center gap-2 w-full text-left font-semibold text-lg mb-2 hover:text-gray-300 transition"
        >
          {statePanelOpen ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          <Database className="w-5 h-5 text-blue-400" />
          Build state (plan, requirements, stack, reports)
        </button>
        {statePanelOpen && (
          <div className="mt-4 space-y-4 text-sm border-t border-white/10 pt-4">
            {!projectState ? (
              <p className="text-gray-500">No state yet. State is written as agents run (plan, requirements, stack, tool results).</p>
            ) : (
              <>
                {Array.isArray(projectState.plan) && projectState.plan.length > 0 && (
                  <div>
                    <h4 className="text-gray-400 font-medium mb-1">Plan</h4>
                    <ul className="list-disc list-inside text-gray-300 space-y-0.5">
                      {projectState.plan.slice(0, 15).map((item, i) => (
                        <li key={i}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {projectState.requirements && Object.keys(projectState.requirements).length > 0 && (
                  <div>
                    <h4 className="text-gray-400 font-medium mb-1">Requirements</h4>
                    <pre className="bg-black/30 p-3 rounded overflow-x-auto text-gray-300 whitespace-pre-wrap max-h-32 overflow-y-auto">
                      {JSON.stringify(projectState.requirements, null, 2)}
                    </pre>
                  </div>
                )}
                {projectState.stack && Object.keys(projectState.stack).length > 0 && (
                  <div>
                    <h4 className="text-gray-400 font-medium mb-1">Stack</h4>
                    <pre className="bg-black/30 p-3 rounded overflow-x-auto text-gray-300 whitespace-pre-wrap max-h-24 overflow-y-auto">
                      {JSON.stringify(projectState.stack, null, 2)}
                    </pre>
                  </div>
                )}
                {(projectState.memory_summary || '').toString().trim() && (
                  <div>
                    <h4 className="text-gray-400 font-medium mb-1">Memory summary</h4>
                    <p className="text-gray-300">{String(projectState.memory_summary).slice(0, 500)}</p>
                  </div>
                )}
                {Array.isArray(projectState.tool_log) && projectState.tool_log.length > 0 && (
                  <div>
                    <h4 className="text-gray-400 font-medium mb-1">Tool runs (last {Math.min(10, projectState.tool_log.length)})</h4>
                    <ul className="space-y-1 text-gray-300">
                      {projectState.tool_log.slice(-10).reverse().map((entry, i) => (
                        <li key={i} className="flex gap-2">
                          <span className="text-blue-400 font-mono text-xs">{entry.agent || 'agent'}</span>
                          <span className="truncate">{typeof entry.output_preview === 'string' ? entry.output_preview.slice(0, 80) : ''}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {(projectState.security_report || projectState.ux_report || projectState.performance_report || '').toString().trim() && (
                  <div>
                    <h4 className="text-gray-400 font-medium mb-1">Reports</h4>
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {projectState.security_report && (
                        <p className="text-gray-300 text-xs"><strong className="text-amber-400">Security:</strong> {String(projectState.security_report).slice(0, 200)}…</p>
                      )}
                      {projectState.ux_report && (
                        <p className="text-gray-300 text-xs"><strong className="text-purple-400">UX:</strong> {String(projectState.ux_report).slice(0, 200)}…</p>
                      )}
                      {projectState.performance_report && (
                        <p className="text-gray-300 text-xs"><strong className="text-green-400">Perf:</strong> {String(projectState.performance_report).slice(0, 200)}…</p>
                      )}
                    </div>
                  </div>
                )}
                {workspaceFiles.length > 0 && (
                  <div>
                    <h4 className="text-gray-400 font-medium mb-1">Files in workspace</h4>
                    <ul className="text-gray-300 text-xs font-mono space-y-0.5 max-h-32 overflow-y-auto">
                      {workspaceFiles.slice(0, 50).map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                      {workspaceFiles.length > 50 && <li className="text-gray-500">… +{workspaceFiles.length - 50} more</li>}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Logs */}
      <div className="p-6 bg-[#0a0a0a] rounded-xl border border-white/10">
        <h3 className="text-lg font-semibold mb-4">Activity Log</h3>
        <div className="h-64 overflow-y-auto space-y-2 mono text-sm" data-testid="activity-log">
          <AnimatePresence>
            {logs.map((log, i) => (
              <motion.div
                key={log.id || i}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-start gap-3 p-2 hover:bg-white/5 rounded"
              >
                <span className={`w-2 h-2 mt-1.5 rounded-full flex-shrink-0 ${
                  log.level === 'success' ? 'bg-green-400' :
                  log.level === 'error' ? 'bg-red-400' :
                  log.level === 'warning' ? 'bg-yellow-400' :
                  'bg-blue-400'
                }`}></span>
                <span className="text-gray-500 flex-shrink-0">
                  {new Date(log.created_at).toLocaleTimeString()}
                </span>
                <span className="text-gray-300">{log.message}</span>
              </motion.div>
            ))}
          </AnimatePresence>
          {logs.length === 0 && (
            <p className="text-gray-500 text-center py-8">Waiting for activity...</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AgentMonitor;