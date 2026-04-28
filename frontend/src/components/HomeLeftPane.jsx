import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import { FolderOpen, Activity, ShieldCheck, GitBranch, ArrowRight, Clock } from 'lucide-react';
import './HomeLeftPane.css';

// Home left-pane widgets: Recent projects, Today's activity, Trust score.
// Fails silently on error and hides sections with no data so first-run users
// see a clean, minimal page instead of loading spinners and empty tables.
export default function HomeLeftPane() {
  const { token } = useAuth();
  const [projects, setProjects] = useState(null);
  const [activity, setActivity] = useState(null);
  const [trust, setTrust] = useState(null);

  useEffect(() => {
    if (!token) return;
    const headers = { Authorization: `Bearer ${token}` };

    axios.get(`${API}/projects?limit=5`, { headers })
      .then((r) => setProjects(Array.isArray(r.data?.projects) ? r.data.projects.slice(0, 5) : []))
      .catch(() => setProjects([]));

    // Activity: if there's a runtime metrics endpoint, use it; else derive from projects.
    axios.get(`${API}/runtime/metrics`, { headers })
      .then((r) => setActivity(r.data || null))
      .catch(() => setActivity(null));

    // Trust summary: light-weight GET that returns an overall score (0-100).
    axios.get(`${API}/trust/summary`, { headers })
      .then((r) => setTrust(r.data || null))
      .catch(() => setTrust(null));
  }, [token]);

  const hasProjects = Array.isArray(projects) && projects.length > 0;
  const hasActivity = activity && typeof activity === 'object';
  const hasTrust = trust && (trust.overall != null || trust.score != null);

  return (
    <aside className="home-left-pane">
      {/* Recent projects */}
      <section className="hlp-card">
        <div className="hlp-card-head">
          <span className="hlp-card-title"><FolderOpen size={14} /> Recent projects</span>
          <Link to="/app/agents" className="hlp-card-link">All <ArrowRight size={11} /></Link>
        </div>
        {projects === null ? (
          <div className="hlp-skeleton">Loading…</div>
        ) : hasProjects ? (
          <ul className="hlp-projects">
            {projects.map((p) => (
              <li key={p.id || p.name}>
                <Link to={`/app/projects/${p.id}`} className="hlp-project-row">
                  <span className="hlp-project-name">{p.name || 'Untitled'}</span>
                  <span className="hlp-project-meta">
                    <span className={`hlp-status hlp-status-${(p.status || 'pending').toLowerCase()}`}>
                      {p.status || 'pending'}
                    </span>
                    {p.created_at && (
                      <span className="hlp-time"><Clock size={10} /> {formatRelative(p.created_at)}</span>
                    )}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <div className="hlp-empty">No projects yet — start one from the prompt above.</div>
        )}
      </section>

      {/* Today's activity */}
      <section className="hlp-card">
        <div className="hlp-card-head">
          <span className="hlp-card-title"><Activity size={14} /> Today</span>
        </div>
        {hasActivity ? (
          <div className="hlp-activity">
            <div className="hlp-stat">
              <strong>{formatNum(activity.runs_today ?? activity.runs ?? 0)}</strong>
              <span>runs</span>
            </div>
            <div className="hlp-stat">
              <strong>{formatNum(activity.tokens_today ?? activity.tokens ?? 0)}</strong>
              <span>tokens</span>
            </div>
            <div className="hlp-stat">
              <strong>{formatNum(activity.errors_today ?? activity.errors ?? 0)}</strong>
              <span>errors</span>
            </div>
          </div>
        ) : (
          <div className="hlp-empty">No activity yet today.</div>
        )}
      </section>

      {/* Trust / quality summary */}
      <section className="hlp-card">
        <div className="hlp-card-head">
          <span className="hlp-card-title"><ShieldCheck size={14} /> Trust score</span>
        </div>
        {hasTrust ? (
          <div className="hlp-trust">
            <div className="hlp-trust-score">
              <strong>{Math.round(trust.overall ?? trust.score ?? 0)}</strong>
              <span>/ 100</span>
            </div>
            <div className="hlp-trust-bar">
              <div
                className="hlp-trust-fill"
                style={{ width: `${Math.max(0, Math.min(100, trust.overall ?? trust.score ?? 0))}%` }}
              />
            </div>
            {(trust.security != null || trust.accessibility != null || trust.performance != null) && (
              <div className="hlp-trust-facets">
                {trust.security != null && <span>Sec {Math.round(trust.security)}</span>}
                {trust.accessibility != null && <span>A11y {Math.round(trust.accessibility)}</span>}
                {trust.performance != null && <span>Perf {Math.round(trust.performance)}</span>}
              </div>
            )}
          </div>
        ) : (
          <div className="hlp-empty">Build something to see a trust score.</div>
        )}
      </section>

      {/* What-If shortcut */}
      <section className="hlp-card hlp-whatif">
        <div className="hlp-card-head">
          <span className="hlp-card-title"><GitBranch size={14} /> What-If</span>
        </div>
        <p className="hlp-whatif-text">
          Simulate a decision across a population of agents — vendor swaps, pricing moves, architecture changes.
        </p>
        <Link to="/app/what-if" className="hlp-whatif-btn">
          Open What-If <ArrowRight size={12} />
        </Link>
      </section>
    </aside>
  );
}

function formatNum(n) {
  const x = Number(n) || 0;
  if (x >= 1_000_000) return `${(x / 1_000_000).toFixed(1)}M`;
  if (x >= 1_000) return `${(x / 1_000).toFixed(1)}k`;
  return String(x);
}

function formatRelative(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return '';
  const diff = Date.now() - d.getTime();
  const hr = diff / 3_600_000;
  if (hr < 1) return `${Math.max(1, Math.round(diff / 60_000))}m ago`;
  if (hr < 24) return `${Math.round(hr)}h ago`;
  const day = hr / 24;
  if (day < 7) return `${Math.round(day)}d ago`;
  return d.toLocaleDateString();
}
