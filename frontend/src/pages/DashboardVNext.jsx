import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { RefreshCw, Play, Activity, ShieldCheck, Workflow, Rocket } from 'lucide-react';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import './DashboardVNext.css';

function statusTone(status) {
  const s = String(status || '').toLowerCase();
  if (s === 'completed' || s === 'success') return 'good';
  if (s === 'failed' || s === 'error' || s === 'cancelled') return 'bad';
  if (s === 'running' || s === 'queued' || s === 'pending') return 'warn';
  return 'muted';
}

export default function DashboardVNext() {
  const navigate = useNavigate();
  const { token } = useAuth();
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

  const groupedWorkflows = useMemo(() => {
    const entries = Object.entries(workflows || {});
    return entries.flatMap(([category, items]) => {
      if (!Array.isArray(items)) return [];
      return items.map((item) => ({ ...item, category }));
    });
  }, [workflows]);

  const runningJobs = jobs.filter((j) => ['running', 'queued', 'pending', 'blocked'].includes(String(j.status || '').toLowerCase()));
  const failedJobs = jobs.filter((j) => ['failed', 'cancelled'].includes(String(j.status || '').toLowerCase()));

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
      <header className="dash-vnext-header">
        <div>
          <h1>Execution Control Tower</h1>
          <p>Backend truth only: projects, jobs, runtime events, trust proof.</p>
        </div>
        <button type="button" className="dash-vnext-btn" onClick={() => refresh(true)} disabled={refreshing || loading}>
          <RefreshCw size={14} />
          {refreshing ? 'Refreshing' : 'Refresh'}
        </button>
      </header>

      <section className="dash-vnext-kpis">
        <article>
          <span>Projects</span>
          <strong>{projects.length}</strong>
        </article>
        <article>
          <span>Running Jobs</span>
          <strong>{runningJobs.length}</strong>
        </article>
        <article>
          <span>Failed Jobs</span>
          <strong>{failedJobs.length}</strong>
        </article>
        <article>
          <span>Trust Pass Rate</span>
          <strong>{trustSummary?.pass_rate ? `${Math.round(Number(trustSummary.pass_rate) * 100)}%` : 'N/A'}</strong>
        </article>
      </section>

      <section className="dash-vnext-grid">
        <aside className="dash-vnext-col">
          <h2><Activity size={16} /> Live Projects</h2>
          <div className="dash-vnext-list">
            {projects.slice(0, 20).map((project) => (
              <button
                type="button"
                key={project.id}
                className="dash-vnext-row"
                onClick={() => navigate(`/app/workspace?projectId=${encodeURIComponent(project.id)}`)}
              >
                <div>
                  <strong>{project.name || project.id}</strong>
                  <span>{project.project_type || 'project'}</span>
                </div>
                <em className={`tone-${statusTone(project.status)}`}>{project.status || 'unknown'}</em>
              </button>
            ))}
            {!projects.length && !loading && <p className="dash-vnext-empty">No projects found.</p>}
          </div>
        </aside>

        <main className="dash-vnext-col dash-vnext-main">
          <h2><Workflow size={16} /> Command Center</h2>
          <div className="dash-vnext-card">
            <label htmlFor="wf">Workflow</label>
            <select id="wf" value={selectedWorkflow} onChange={(e) => setSelectedWorkflow(e.target.value)}>
              <option value="">Select a workflow</option>
              {groupedWorkflows.map((wf) => (
                <option key={wf.key} value={wf.key}>{wf.category} · {wf.name}</option>
              ))}
            </select>
            <label htmlFor="goal">Goal / Context</label>
            <textarea
              id="goal"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="Describe what this run should deliver..."
              rows={5}
            />
            <div className="dash-vnext-actions">
              <button type="button" className="dash-vnext-btn dash-vnext-btn-primary" onClick={runWorkflow} disabled={!selectedWorkflow || runBusy}>
                <Play size={14} />
                {runBusy ? 'Starting...' : 'Run Workflow'}
              </button>
              <button type="button" className="dash-vnext-btn" onClick={() => navigate('/app/workspace')}>
                <Rocket size={14} />
                Open Workspace
              </button>
            </div>
            {runError ? <p className="dash-vnext-error">{runError}</p> : null}
          </div>

          <div className="dash-vnext-card">
            <h3>Runtime Event Feed</h3>
            <ul className="dash-vnext-events">
              {runtimeEvents.slice(0, 12).map((event, idx) => (
                <li key={`${event.ts || idx}-${event.type || 'event'}`}>
                  <span>{event.type || 'event'}</span>
                  <em>{event.ts ? new Date(event.ts).toLocaleTimeString() : 'now'}</em>
                </li>
              ))}
              {!runtimeEvents.length && !loading && <li className="dash-vnext-empty">No recent runtime events.</li>}
            </ul>
          </div>
        </main>

        <aside className="dash-vnext-col">
          <h2><ShieldCheck size={16} /> Trust + Jobs</h2>
          <div className="dash-vnext-card">
            <h3>Trust Summary</h3>
            <p>Status: <strong>{trustSummary?.status || 'not_available'}</strong></p>
            <p>Prompts: <strong>{trustSummary?.prompt_count ?? 0}</strong></p>
            <p>Passed: <strong>{trustSummary?.passed_count ?? 0}</strong></p>
          </div>
          <div className="dash-vnext-card">
            <h3>Recent Jobs</h3>
            <div className="dash-vnext-list">
              {jobs.slice(0, 12).map((job) => (
                <button
                  type="button"
                  key={job.id}
                  className="dash-vnext-row"
                  onClick={() => navigate(`/app/workspace?jobId=${encodeURIComponent(job.id)}`)}
                >
                  <div>
                    <strong>{job.goal ? String(job.goal).slice(0, 48) : job.id}</strong>
                    <span>{job.id}</span>
                  </div>
                  <em className={`tone-${statusTone(job.status)}`}>{job.status || 'unknown'}</em>
                </button>
              ))}
              {!jobs.length && !loading && <p className="dash-vnext-empty">No jobs yet.</p>}
            </div>
          </div>
        </aside>
      </section>
    </div>
  );
}
