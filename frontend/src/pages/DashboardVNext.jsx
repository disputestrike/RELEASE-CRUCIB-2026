import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Activity,
  ArrowRight,
  BadgeCheck,
  Database,
  RefreshCw,
  Rocket,
  ShieldCheck,
  Sparkles,
  Play,
  Workflow,
  FolderOpen,
  Clock3,
  Bot,
} from 'lucide-react';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import './DashboardVNext.css';

function statusTone(status) {
  const value = String(status || '').toLowerCase();
  if (value === 'completed' || value === 'success' || value === 'deployed') return 'good';
  if (value === 'failed' || value === 'error' || value === 'cancelled') return 'bad';
  if (value === 'running' || value === 'queued' || value === 'pending' || value === 'blocked') return 'warn';
  return 'muted';
}

function formatRelative(value) {
  if (!value) return 'No timestamp';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'No timestamp';
  const minutes = Math.round((Date.now() - date.getTime()) / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

export default function DashboardVNext() {
  const navigate = useNavigate();
  const { token, user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [projects, setProjects] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [workflows, setWorkflows] = useState({});
  const [runtimeEvents, setRuntimeEvents] = useState([]);
  const [trustSummary, setTrustSummary] = useState(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState('');
  const [goal, setGoal] = useState('');
  const [runBusy, setRunBusy] = useState(false);
  const [runError, setRunError] = useState('');

  const headers = useMemo(() => (token ? { Authorization: `Bearer ${token}` } : {}), [token]);

  const refresh = async (isManual = false) => {
    if (!token) return;
    if (isManual) setRefreshing(true);
    try {
      const [projectsRes, jobsRes, workflowsRes, eventsRes, trustRes] = await Promise.allSettled([
        axios.get(`${API}/projects`, { headers, timeout: 12000 }),
        axios.get(`${API}/jobs`, { headers, timeout: 12000 }),
        axios.get(`${API}/workflows`, { headers, timeout: 12000 }),
        axios.get(`${API}/runtime/events/recent`, { headers, timeout: 12000 }),
        axios.get(`${API}/trust/benchmark-summary`, { timeout: 12000 }),
      ]);

      if (projectsRes.status === 'fulfilled') {
        const rows = projectsRes.value.data?.projects || projectsRes.value.data || [];
        setProjects(Array.isArray(rows) ? rows : []);
      }
      if (jobsRes.status === 'fulfilled') {
        const rows = jobsRes.value.data?.jobs || [];
        setJobs(Array.isArray(rows) ? rows : []);
      }
      if (workflowsRes.status === 'fulfilled') {
        setWorkflows(workflowsRes.value.data?.workflows || {});
      }
      if (eventsRes.status === 'fulfilled') {
        setRuntimeEvents(eventsRes.value.data?.events || []);
      }
      if (trustRes.status === 'fulfilled') {
        setTrustSummary(trustRes.value.data || null);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (!token) return;
    refresh(false);
    const id = setInterval(() => {
      refresh(false).catch(() => {});
    }, 15000);
    return () => clearInterval(id);
  }, [token]);

  const workflowOptions = useMemo(() => {
    return Object.entries(workflows || {}).flatMap(([group, items]) => {
      if (!Array.isArray(items)) return [];
      return items.map((item) => ({ ...item, group }));
    });
  }, [workflows]);

  const runningJobs = jobs.filter((job) => ['running', 'queued', 'pending', 'blocked'].includes(String(job.status || '').toLowerCase()));
  const completedJobs = jobs.filter((job) => ['completed', 'success'].includes(String(job.status || '').toLowerCase()));
  const failedJobs = jobs.filter((job) => ['failed', 'cancelled'].includes(String(job.status || '').toLowerCase()));
  const latestProject = projects[0];
  const latestRuntimeEvent = runtimeEvents[0];

  const summaryCards = [
    {
      label: 'Projects',
      value: projects.length,
      detail: latestProject ? `Latest: ${latestProject.name || latestProject.id}` : 'No projects yet',
      icon: FolderOpen,
    },
    {
      label: 'Active runs',
      value: runningJobs.length,
      detail: runningJobs[0] ? String(runningJobs[0].goal || runningJobs[0].id).slice(0, 56) : 'No live orchestration right now',
      icon: Activity,
    },
    {
      label: 'Completed jobs',
      value: completedJobs.length,
      detail: completedJobs[0] ? `Last finish ${formatRelative(completedJobs[0].updated_at || completedJobs[0].completed_at)}` : 'No completions recorded',
      icon: BadgeCheck,
    },
    {
      label: 'Trust pass rate',
      value: trustSummary?.pass_rate ? `${Math.round(Number(trustSummary.pass_rate) * 100)}%` : 'N/A',
      detail: trustSummary ? `${trustSummary.passed_count ?? 0}/${trustSummary.prompt_count ?? 0} proof checks passing` : 'Trust benchmark unavailable',
      icon: ShieldCheck,
    },
  ];

  const runWorkflow = async () => {
    if (!selectedWorkflow || !token) return;
    setRunBusy(true);
    setRunError('');
    try {
      const res = await axios.post(
        `${API}/workflows/run`,
        {
          workflow_key: selectedWorkflow,
          context: goal || undefined,
        },
        { headers, timeout: 20000 },
      );
      const jobId = res.data?.job_id;
      if (jobId) {
        navigate(`/app/workspace?jobId=${encodeURIComponent(jobId)}`);
        return;
      }
      navigate('/app/workspace', { state: { initialPrompt: goal || 'Run selected workflow' } });
    } catch (e) {
      setRunError(e?.response?.data?.detail || e?.message || 'Workflow run failed');
    } finally {
      setRunBusy(false);
    }
  };

  return (
    <div className="dash-vnext">
      <section className="dash-vnext-hero">
        <div>
          <div className="dash-vnext-eyebrow">
            <Sparkles size={14} />
            Operating center
          </div>
          <h1>Run CrucibAI like a product studio, not a pile of tabs.</h1>
          <p>
            Projects, orchestration, trust signals, and live activity are all in one calmer surface.
            The structure follows the workspace style you shared while staying wired to your real backend.
          </p>
        </div>
        <div className="dash-vnext-hero-actions">
          <button type="button" className="dash-vnext-btn" onClick={() => refresh(true)} disabled={refreshing || loading}>
            <RefreshCw size={14} />
            {refreshing ? 'Refreshing' : 'Refresh'}
          </button>
          <button type="button" className="dash-vnext-btn dash-vnext-btn-primary" onClick={() => navigate('/app/workspace')}>
            <Rocket size={14} />
            Open workspace
          </button>
        </div>
      </section>

      <section className="dash-vnext-summary">
        {summaryCards.map((card) => {
          const Icon = card.icon;
          return (
            <article key={card.label} className="dash-vnext-summary-card">
              <div className="dash-vnext-summary-head">
                <span>{card.label}</span>
                <Icon size={16} />
              </div>
              <strong>{card.value}</strong>
              <p>{card.detail}</p>
            </article>
          );
        })}
      </section>

      <section className="dash-vnext-grid">
        <aside className="dash-vnext-panel dash-vnext-panel-left">
          <div className="dash-vnext-panel-title">
            <h2>Recent projects</h2>
            <button type="button" className="dash-vnext-link-btn" onClick={() => navigate('/app/workspace')}>
              New build
              <ArrowRight size={14} />
            </button>
          </div>
          <div className="dash-vnext-list">
            {projects.slice(0, 8).map((project) => (
              <button
                type="button"
                key={project.id}
                className="dash-vnext-row"
                onClick={() => navigate(`/app/workspace?projectId=${encodeURIComponent(project.id)}`)}
              >
                <div className="dash-vnext-row-copy">
                  <strong>{project.name || project.id}</strong>
                  <span>{project.project_type || 'project'} · {formatRelative(project.updated_at || project.created_at)}</span>
                </div>
                <em className={`tone-${statusTone(project.status)}`}>{project.status || 'unknown'}</em>
              </button>
            ))}
            {!projects.length && !loading && <p className="dash-vnext-empty">No projects found yet.</p>}
          </div>

          <div className="dash-vnext-subpanel">
            <div className="dash-vnext-subpanel-head">
              <h3>System pulse</h3>
              <Clock3 size={14} />
            </div>
            <div className="dash-vnext-pulse">
              <div>
                <span>Latest event</span>
                <strong>{latestRuntimeEvent?.type || 'No recent events'}</strong>
              </div>
              <p>{latestRuntimeEvent?.ts ? formatRelative(latestRuntimeEvent.ts) : 'Waiting for runtime activity'}</p>
            </div>
          </div>
        </aside>

        <main className="dash-vnext-panel dash-vnext-panel-main">
          <div className="dash-vnext-panel-title">
            <h2>Command composer</h2>
            <span className="dash-vnext-caption">Start a workflow or jump into the full workspace.</span>
          </div>
          <div className="dash-vnext-composer">
            <label htmlFor="dashboard-workflow">Workflow</label>
            <select id="dashboard-workflow" value={selectedWorkflow} onChange={(e) => setSelectedWorkflow(e.target.value)}>
              <option value="">Select a workflow</option>
              {workflowOptions.map((workflow) => (
                <option key={workflow.key} value={workflow.key}>
                  {workflow.group} · {workflow.name}
                </option>
              ))}
            </select>

            <label htmlFor="dashboard-goal">Goal / context</label>
            <textarea
              id="dashboard-goal"
              rows={6}
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="Describe what this run should deliver, what should be changed, or what should be verified."
            />

            <div className="dash-vnext-actions">
              <button type="button" className="dash-vnext-btn dash-vnext-btn-primary" onClick={runWorkflow} disabled={!selectedWorkflow || runBusy}>
                <Play size={14} />
                {runBusy ? 'Starting...' : 'Run workflow'}
              </button>
              <button type="button" className="dash-vnext-btn" onClick={() => navigate('/app/workspace', { state: { initialPrompt: goal || undefined } })}>
                <Workflow size={14} />
                Continue in workspace
              </button>
            </div>
            {runError ? <p className="dash-vnext-error">{runError}</p> : null}
          </div>

          <div className="dash-vnext-subgrid">
            <section className="dash-vnext-subpanel">
              <div className="dash-vnext-subpanel-head">
                <h3>Live activity</h3>
                <Activity size={14} />
              </div>
              <ul className="dash-vnext-events">
                {runtimeEvents.slice(0, 8).map((event, index) => (
                  <li key={`${event.ts || index}-${event.type || 'event'}`}>
                    <div>
                      <strong>{event.type || 'event'}</strong>
                      <span>{event.payload?.path || event.payload?.command || event.payload?.headline || 'Runtime update'}</span>
                    </div>
                    <em>{event.ts ? formatRelative(event.ts) : 'now'}</em>
                  </li>
                ))}
                {!runtimeEvents.length && !loading && <li className="dash-vnext-empty">No recent runtime events.</li>}
              </ul>
            </section>

            <section className="dash-vnext-subpanel">
              <div className="dash-vnext-subpanel-head">
                <h3>Capabilities online</h3>
                <Database size={14} />
              </div>
              <div className="dash-vnext-tags">
                {['Backend server', 'Database', 'Auth', 'Workflows', 'Trust proof'].map((item) => (
                  <span key={item}>{item}</span>
                ))}
              </div>
              <p className="dash-vnext-note">
                Signed in as {user?.name || user?.email || 'guest'}.
                Use the workspace for build execution and this dashboard for orchestration, monitoring, and navigation.
              </p>
            </section>
          </div>
        </main>

        <aside className="dash-vnext-panel dash-vnext-panel-right">
          <div className="dash-vnext-panel-title">
            <h2>Jobs and trust</h2>
            <span className="dash-vnext-caption">The right rail stays focused on health and outcomes.</span>
          </div>

          <div className="dash-vnext-subpanel">
            <div className="dash-vnext-subpanel-head">
              <h3>Recent jobs</h3>
              <Bot size={14} />
            </div>
            <div className="dash-vnext-list">
              {jobs.slice(0, 7).map((job) => (
                <button
                  type="button"
                  key={job.id}
                  className="dash-vnext-row"
                  onClick={() => navigate(`/app/workspace?jobId=${encodeURIComponent(job.id)}`)}
                >
                  <div className="dash-vnext-row-copy">
                    <strong>{job.goal ? String(job.goal).slice(0, 54) : job.id}</strong>
                    <span>{formatRelative(job.updated_at || job.created_at)}</span>
                  </div>
                  <em className={`tone-${statusTone(job.status)}`}>{job.status || 'unknown'}</em>
                </button>
              ))}
              {!jobs.length && !loading && <p className="dash-vnext-empty">No jobs yet.</p>}
            </div>
          </div>

          <div className="dash-vnext-subpanel">
            <div className="dash-vnext-subpanel-head">
              <h3>Trust benchmark</h3>
              <ShieldCheck size={14} />
            </div>
            <div className="dash-vnext-trust">
              <div>
                <span>Status</span>
                <strong>{trustSummary?.status || 'not_available'}</strong>
              </div>
              <div>
                <span>Prompt count</span>
                <strong>{trustSummary?.prompt_count ?? 0}</strong>
              </div>
              <div>
                <span>Passed</span>
                <strong>{trustSummary?.passed_count ?? 0}</strong>
              </div>
              <div>
                <span>Failures</span>
                <strong>{failedJobs.length}</strong>
              </div>
            </div>
          </div>
        </aside>
      </section>
    </div>
  );
}
