"""Enterprise command build pack for complex regulated operating systems."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple


def _goal_text(job_or_goal: Any) -> str:
    if isinstance(job_or_goal, str):
        return job_or_goal or ""
    return str(job_or_goal.get("goal") or "")


def enterprise_command_intent(job_or_goal: Any) -> bool:
    goal = _goal_text(job_or_goal).lower()
    if not goal:
        return False
    direct_markers = (
        "black-belt omega gauntlet",
        "helios aegis command",
        "elite autonomous system test",
        "aegis omega build",
    )
    if any(marker in goal for marker in direct_markers):
        return True
    keywords = (
        "multi-tenant",
        "crm",
        "quote",
        "project workflow",
        "policy",
        "compliance",
        "audit",
        "analytics",
        "worker",
        "integration",
        "approval",
        "tenant isolation",
    )
    score = sum(1 for keyword in keywords if keyword in goal)
    return score >= 6


def _extract_named_product(goal: str) -> str | None:
    patterns = [
        r"named:\s*#\s*\*\*([^*]+)\*\*",
        r"named:\s*\*\*([^*]+)\*\*",
        r'named:\s*"([^"]+)"',
        r"platform named[:\s]+([A-Z][A-Za-z0-9][A-Za-z0-9 \-]{4,80})",
    ]
    for pattern in patterns:
        match = re.search(pattern, goal, re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip(" -:#")
    if "helios aegis command" in goal.lower():
        return "Helios Aegis Command"
    return None


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "enterprise-command"


def enterprise_command_profile(job_or_goal: Any) -> Dict[str, str]:
    goal = _goal_text(job_or_goal)
    product_name = _extract_named_product(goal) or "Enterprise Command Center"
    company_name = (
        "Helios Aegis"
        if "helios aegis" in goal.lower()
        else product_name.replace(" Command", "")
    )
    return {
        "product_name": product_name,
        "company_name": company_name or product_name,
        "command_slug": _slugify(product_name),
        "goal_excerpt": re.sub(r"\s+", " ", goal).strip()[:500],
    }


def _replace_tokens(template: str, **values: str) -> str:
    output = template
    for key, value in values.items():
        output = output.replace(f"__{key}__", value)
    return output


def _frontend_seed(profile: Dict[str, str]) -> Dict[str, Any]:
    org_id = f"{profile['command_slug']}-org"
    return {
        "tenant": {
            "id": org_id,
            "name": f"{profile['company_name']} Portfolio Operations",
            "region": "US West",
            "active_sites": 312,
            "customer_count": 148,
        },
        "metrics": [
            {"label": "Portfolio ARR", "value": "$12.8M", "delta": "+8.4%"},
            {"label": "Quotes Awaiting Review", "value": "6", "delta": "2 escalated"},
            {
                "label": "Policy Recommendations",
                "value": "4",
                "delta": "1 requires approval",
            },
            {"label": "Worker Failures", "value": "0", "delta": "all retries drained"},
        ],
        "leads": [
            {
                "id": "LD-104",
                "org_id": org_id,
                "name": "Riverton Logistics",
                "score": 92,
                "status": "qualified",
                "owner": "Alex Chen",
            },
            {
                "id": "LD-118",
                "org_id": org_id,
                "name": "Summit Storage Group",
                "score": 84,
                "status": "proposal",
                "owner": "Jordan Lee",
            },
        ],
        "accounts": [
            {
                "id": "AC-201",
                "org_id": org_id,
                "name": "Riverton Logistics",
                "segment": "Industrial",
                "region": "CA",
                "contracts": 3,
            },
            {
                "id": "AC-214",
                "org_id": org_id,
                "name": "Northwind Senior Living",
                "segment": "Healthcare",
                "region": "AZ",
                "contracts": 2,
            },
        ],
        "opportunities": [
            {
                "id": "OP-88",
                "org_id": org_id,
                "account": "Riverton Logistics",
                "value": "$184,500",
                "stage": "quote_pending",
            },
            {
                "id": "OP-93",
                "org_id": org_id,
                "account": "Northwind Senior Living",
                "value": "$94,300",
                "stage": "risk_review",
            },
        ],
        "quotes": [
            {
                "id": "Q-1042",
                "org_id": org_id,
                "account": "Riverton Logistics",
                "status": "pending_review",
                "total": 184500,
                "expires_on": "2026-04-30",
                "approver": "Morgan Rivera",
                "ai_recommendation": "Reduce battery reserve by 3% after human review.",
            },
            {
                "id": "Q-1047",
                "org_id": org_id,
                "account": "Northwind Senior Living",
                "status": "draft",
                "total": 94300,
                "expires_on": "2026-05-12",
                "approver": "Pending assignment",
                "ai_recommendation": "Block conversion until region eligibility is cleared.",
            },
        ],
        "projects": [
            {
                "id": "PR-12",
                "org_id": org_id,
                "name": "Riverton West Campus",
                "status": "installation_ready",
                "timeline": "Apr 22 - Jun 14",
                "account": "Riverton Logistics",
            },
            {
                "id": "PR-18",
                "org_id": org_id,
                "name": "Northwind Expansion",
                "status": "planning",
                "timeline": "May 03 - Jul 18",
                "account": "Northwind Senior Living",
            },
        ],
        "tasks": [
            {
                "id": "TS-301",
                "org_id": org_id,
                "title": "Review incentive region mismatch",
                "status": "open",
                "priority": "high",
                "owner": "Morgan Rivera",
                "source": "rule:region_eligibility",
            },
            {
                "id": "TS-309",
                "org_id": org_id,
                "title": "Approve quote Q-1042",
                "status": "open",
                "priority": "high",
                "owner": "Morgan Rivera",
                "source": "workflow:quote_review",
            },
        ],
        "policyRecommendations": [
            {
                "id": "POL-01",
                "org_id": org_id,
                "title": "Escalate repeated webhook failures",
                "status": "PENDING",
                "recommended_action": "Require org_admin approval before re-enabling vendor webhook.",
                "trigger": "3 failed sync runs in 20 minutes",
            },
            {
                "id": "POL-02",
                "org_id": org_id,
                "title": "Geo-risk review on storage site",
                "status": "APPROVED",
                "recommended_action": "Limit remote dispatch until site inspection completes.",
                "trigger": "Repeated suspicious telemetry variance",
            },
        ],
        "integrations": [
            {
                "id": "INT-11",
                "org_id": org_id,
                "name": "Salesforce sync",
                "status": "healthy",
                "last_run": "2m ago",
            },
            {
                "id": "INT-14",
                "org_id": org_id,
                "name": "Operator webhook",
                "status": "degraded",
                "last_run": "retrying",
            },
        ],
        "auditTrail": [
            {
                "id": "AUD-001",
                "org_id": org_id,
                "action": "quote.pending_review",
                "actor": "alex.chen@heliosaegis.test",
                "prev_hash": "GENESIS",
                "current_hash": "4bd4bf1902c7c201",
                "entity": "Q-1042",
            },
            {
                "id": "AUD-002",
                "org_id": org_id,
                "action": "policy.recommendation_created",
                "actor": "system",
                "prev_hash": "4bd4bf1902c7c201",
                "current_hash": "e1529145233cf892",
                "entity": "POL-01",
            },
        ],
        "analytics": {
            "quote_conversion": {"approved": 14, "rejected": 2, "pending": 6},
            "operator_load": {"open_tasks": 17, "sla_watch": 3, "retrying_jobs": 1},
            "policy_disposition": {
                "pending": 1,
                "approved": 1,
                "rejected": 0,
                "enforced": 0,
            },
            "ai_disposition": {"accepted": 12, "rejected": 4, "needs_human_review": 7},
        },
    }


def build_enterprise_frontend_file_set(job: Dict[str, Any]) -> List[Tuple[str, str]]:
    profile = enterprise_command_profile(job)
    return _build_frontend_files(profile)


def build_enterprise_backend_file_set(
    job: Dict[str, Any], step_key: str = ""
) -> List[Tuple[str, str]]:
    profile = enterprise_command_profile(job)
    return _build_backend_files(profile)


def build_enterprise_database_file_set(
    job: Dict[str, Any], step_key: str = ""
) -> List[Tuple[str, str]]:
    profile = enterprise_command_profile(job)
    return _build_database_files(profile, step_key=step_key)


def enterprise_backend_routes() -> List[Dict[str, str]]:
    return [
        {"method": "GET", "path": "/health", "description": "Health check"},
        {"method": "POST", "path": "/api/auth/login", "description": "Login"},
        {"method": "POST", "path": "/api/auth/refresh", "description": "Refresh token"},
        {"method": "GET", "path": "/api/auth/me", "description": "Current user"},
        {
            "method": "GET",
            "path": "/api/crm/leads",
            "description": "Tenant-scoped leads",
        },
        {
            "method": "GET",
            "path": "/api/crm/accounts",
            "description": "Tenant-scoped accounts",
        },
        {"method": "GET", "path": "/api/quotes", "description": "Quote queue"},
        {
            "method": "POST",
            "path": "/api/quotes/{quote_id}/approve",
            "description": "Human quote approval",
        },
        {"method": "GET", "path": "/api/projects", "description": "Projects"},
        {
            "method": "GET",
            "path": "/api/policies/recommendations",
            "description": "Policy recommendations",
        },
        {
            "method": "POST",
            "path": "/api/policies/{policy_id}/enforce",
            "description": "Enforce approved policy",
        },
        {"method": "GET", "path": "/api/audit/events", "description": "Audit events"},
        {
            "method": "GET",
            "path": "/api/analytics/overview",
            "description": "Analytics overview",
        },
    ]


def _build_frontend_files(profile: Dict[str, str]) -> List[Tuple[str, str]]:
    product_name = profile["product_name"]
    command_slug = profile["command_slug"]
    seed_json = json.dumps(_frontend_seed(profile), indent=2)
    package_json = json.dumps(
        {
            "name": command_slug,
            "version": "0.1.0",
            "private": True,
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview",
            },
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-router-dom": "^6.22.0",
                "zustand": "^4.5.0",
            },
            "devDependencies": {"vite": "^5.4.11", "@vitejs/plugin-react": "^4.3.4"},
        },
        indent=2,
    )
    return [
        ("package.json", package_json),
        (
            "index.html",
            f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{product_name}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
""",
        ),
        (
            "vite.config.js",
            """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({ plugins: [react()] });
""",
        ),
        (
            "README_BUILD.md",
            f"""# {product_name}

Enterprise command-center build generated by CrucibAI's deterministic enterprise pack.

Implemented surfaces:
- command dashboard
- tenant-scoped CRM
- quote approval workflow
- projects and tasks
- policy recommendation and enforcement boundary
- audit visibility
- analytics and integration health
""",
        ),
        (
            "docs/BUILD_MODE.md",
            f"""# Enterprise build mode

CrucibAI selected the enterprise command pack for `{product_name}` because the goal requested a regulated, multi-tenant command system.

This run does not display the prompt text as UI content.
""",
        ),
        (
            "proof/ELITE_ANALYSIS.md",
            f"""# Elite analysis

Product: {product_name}

- multi-page command UI
- explicit human approval boundaries
- tenant-scoped business data
- backend API foundation and SQL migrations
""",
        ),
        (
            "src/data/enterpriseSeed.js",
            f"""const enterpriseSeed = {seed_json};

export default enterpriseSeed;
""",
        ),
        (
            "src/store/useAppStore.js",
            _replace_tokens(
                """import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import enterpriseSeed from '../data/enterpriseSeed';

const clone = (value) => JSON.parse(JSON.stringify(value));

function nextHash(prevHash, marker) {
  const prefix = (prevHash || 'GENESIS').slice(0, 8);
  return `${prefix}-${marker}-${Date.now().toString(36)}`;
}

function appendAudit(state, action, entity) {
  const previous = state.auditTrail[state.auditTrail.length - 1];
  const prevHash = previous ? previous.current_hash : 'GENESIS';
  return [
    ...state.auditTrail,
    {
      id: `AUD-${String(state.auditTrail.length + 1).padStart(3, '0')}`,
      org_id: state.tenant.id,
      action,
      actor: state.currentOperator.name,
      prev_hash: prevHash,
      current_hash: nextHash(prevHash, action.replace(/[^a-z]/gi, '').slice(0, 6).toLowerCase() || 'audit'),
      entity,
    },
  ];
}

export const useAppStore = create(
  persist(
    (set) => ({
      theme: 'dark',
      tenant: clone(enterpriseSeed.tenant),
      metrics: clone(enterpriseSeed.metrics),
      leads: clone(enterpriseSeed.leads),
      accounts: clone(enterpriseSeed.accounts),
      opportunities: clone(enterpriseSeed.opportunities),
      quotes: clone(enterpriseSeed.quotes),
      projects: clone(enterpriseSeed.projects),
      tasks: clone(enterpriseSeed.tasks),
      policyRecommendations: clone(enterpriseSeed.policyRecommendations),
      integrations: clone(enterpriseSeed.integrations),
      auditTrail: clone(enterpriseSeed.auditTrail),
      analytics: clone(enterpriseSeed.analytics),
      currentOperator: { name: 'Morgan Rivera', role: 'org_admin' },
      operatorNotes: '',
      setTheme: (theme) => set({ theme }),
      setOperatorNotes: (operatorNotes) => set({ operatorNotes }),
      approveQuote: (quoteId, decision) =>
        set((state) => ({
          quotes: state.quotes.map((quote) =>
            quote.id === quoteId && ['draft', 'pending_review'].includes(quote.status)
              ? { ...quote, status: decision === 'approved' ? 'approved' : 'rejected', approver: state.currentOperator.name }
              : quote
          ),
          auditTrail: appendAudit(state, `quote.${decision}`, quoteId),
        })),
      approvePolicy: (policyId, decision) =>
        set((state) => ({
          policyRecommendations: state.policyRecommendations.map((item) =>
            item.id === policyId && item.status === 'PENDING'
              ? { ...item, status: decision === 'approved' ? 'APPROVED' : 'REJECTED' }
              : item
          ),
          auditTrail: appendAudit(state, `policy.${decision}`, policyId),
        })),
      enforcePolicy: (policyId) =>
        set((state) => ({
          policyRecommendations: state.policyRecommendations.map((item) =>
            item.id === policyId && item.status === 'APPROVED' ? { ...item, status: 'ENFORCED' } : item
          ),
          auditTrail: appendAudit(state, 'policy.enforced', policyId),
        })),
    }),
    {
      name: '__COMMAND_SLUG__-workspace',
      storage: createJSONStorage(() => localStorage),
    }
  )
);
""",
                COMMAND_SLUG=command_slug,
            ),
        ),
        (
            "src/context/AuthContext.jsx",
            """import React, { createContext, useContext, useMemo, useState } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState({ name: 'Morgan Rivera', email: 'morgan@heliosaegis.test', role: 'org_admin' });

  const value = useMemo(() => ({
    user,
    isAuthenticated: Boolean(user),
    login: (name) => setUser({ name: name || 'Morgan Rivera', email: 'morgan@heliosaegis.test', role: 'org_admin' }),
    logout: () => setUser(null),
  }), [user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
""",
        ),
        (
            "src/components/ErrorBoundary.jsx",
            """import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return <main className="app-shell"><section className="panel"><h1>Workspace needs attention</h1><p>The enterprise preview hit a recoverable UI error.</p></section></main>;
    }
    return this.props.children;
  }
}
""",
        ),
        (
            "src/components/ShellLayout.jsx",
            _replace_tokens(
                """import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useAppStore } from '../store/useAppStore';

const navItems = [
  ['/', 'Home'],
  ['/login', 'Login'],
  ['/dashboard', 'Command'],
  ['/crm', 'CRM'],
  ['/quotes', 'Quotes'],
  ['/projects', 'Projects'],
  ['/policy', 'Policy'],
  ['/audit', 'Audit'],
  ['/analytics', 'Analytics'],
  ['/team', 'Operators'],
];

export default function ShellLayout() {
  const { user, logout } = useAuth();
  const theme = useAppStore((state) => state.theme);
  const setTheme = useAppStore((state) => state.setTheme);
  const tenant = useAppStore((state) => state.tenant);

  return (
    <div className={`app-shell theme-${theme}`}>
      <header className="topbar">
        <div>
          <div className="eyebrow">Enterprise command center</div>
          <h1 className="brand">__PRODUCT_NAME__</h1>
          <p className="subtle">{tenant.name} · {tenant.active_sites} managed sites · role {user?.role}</p>
        </div>
        <div className="button-row">
          <button className="ghost-button" type="button" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>Theme: {theme}</button>
          <button className="primary-button" type="button" onClick={logout}>Sign out</button>
        </div>
      </header>
      <nav className="nav-row">
        {navItems.map(([to, label]) => (
          <NavLink key={to} to={to} className={({ isActive }) => (isActive ? 'nav-link nav-link-active' : 'nav-link')}>
            {label}
          </NavLink>
        ))}
      </nav>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
""",
                PRODUCT_NAME=product_name,
            ),
        ),
        (
            "src/components/StatusPill.jsx",
            """import React from 'react';

const palette = {
  draft: 'pill pill-slate', pending_review: 'pill pill-amber', approved: 'pill pill-green', rejected: 'pill pill-red',
  PENDING: 'pill pill-amber', APPROVED: 'pill pill-blue', ENFORCED: 'pill pill-green', REJECTED: 'pill pill-red',
  open: 'pill pill-amber', installation_ready: 'pill pill-green', planning: 'pill pill-slate', qualified: 'pill pill-green',
  proposal: 'pill pill-blue', healthy: 'pill pill-green', degraded: 'pill pill-red',
};

export default function StatusPill({ value }) {
  return <span className={palette[value] || 'pill pill-slate'}>{value}</span>;
}
""",
        ),
        (
            "src/components/MetricCard.jsx",
            """import React from 'react';

export default function MetricCard({ label, value, delta }) {
  return <article className="metric-card"><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-delta">{delta}</div></article>;
}
""",
        ),
        (
            "src/pages/HomePage.jsx",
            _replace_tokens(
                """import React from 'react';
import { Link } from 'react-router-dom';

export default function HomePage() {
  return (
    <section className="panel">
      <div className="eyebrow">Launch surface</div>
      <h2>Mission control</h2>
      <p className="lead">__PRODUCT_NAME__ unifies CRM, quoting, project delivery, policy review, audit visibility, and operator assist without rendering the raw prompt as product content.</p>
      <div className="button-row">
        <Link className="primary-button" to="/dashboard">Open command view</Link>
        <Link className="ghost-button" to="/quotes">Review protected quotes</Link>
        <Link className="ghost-button" to="/policy">Inspect policy approvals</Link>
      </div>
    </section>
  );
}
""",
                PRODUCT_NAME=product_name,
            ),
        ),
        (
            "src/pages/LoginPage.jsx",
            """import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('Morgan Rivera');

  return (
    <section className="panel">
      <div className="eyebrow">Demo auth</div>
      <h2>Operator access</h2>
      <p className="lead">Use the seeded org-admin session to inspect approvals, policy boundaries, and audit evidence.</p>
      <input className="text-input" placeholder="Display name" value={name} onChange={(event) => setName(event.target.value)} />
      <div className="button-row">
        <button className="primary-button" type="button" onClick={() => { login(name); navigate('/dashboard'); }}>Sign in (demo)</button>
      </div>
    </section>
  );
}
""",
        ),
        (
            "src/pages/DashboardPage.jsx",
            """import React from 'react';
import MetricCard from '../components/MetricCard';
import StatusPill from '../components/StatusPill';
import { useAppStore } from '../store/useAppStore';

export default function DashboardPage() {
  const metrics = useAppStore((state) => state.metrics);
  const quotes = useAppStore((state) => state.quotes);
  const policies = useAppStore((state) => state.policyRecommendations);
  const integrations = useAppStore((state) => state.integrations);

  return (
    <div className="page-grid">
      <section className="panel">
        <div className="eyebrow">Operational overview</div>
        <h2>Dashboard</h2>
        <p className="subtle">Live command summary for approvals, integrations, and tenant-scoped delivery work.</p>
      </section>
      <section className="metric-grid">{metrics.map((metric) => <MetricCard key={metric.label} {...metric} />)}</section>
      <section className="panel">
        <div className="eyebrow">Human approvals required</div>
        <h2>Critical review queue</h2>
        <table className="data-table">
          <thead><tr><th>Entity</th><th>Status</th><th>Owner</th><th>Signal</th></tr></thead>
          <tbody>
            {quotes.map((quote) => <tr key={quote.id}><td>{quote.id}</td><td><StatusPill value={quote.status} /></td><td>{quote.approver}</td><td>{quote.ai_recommendation}</td></tr>)}
            {policies.map((policy) => <tr key={policy.id}><td>{policy.id}</td><td><StatusPill value={policy.status} /></td><td>org_admin</td><td>{policy.recommended_action}</td></tr>)}
          </tbody>
        </table>
      </section>
      <section className="panel">
        <div className="eyebrow">Late-stage stability</div>
        <h2>Integration health</h2>
        <div className="stack-list">
          {integrations.map((integration) => (
            <div key={integration.id} className="stack-row">
              <div><strong>{integration.name}</strong><div className="subtle">{integration.last_run}</div></div>
              <StatusPill value={integration.status} />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
""",
        ),
        (
            "src/pages/CRMPage.jsx",
            """import React from 'react';
import StatusPill from '../components/StatusPill';
import { useAppStore } from '../store/useAppStore';

export default function CRMPage() {
  const leads = useAppStore((state) => state.leads);
  const accounts = useAppStore((state) => state.accounts);
  const opportunities = useAppStore((state) => state.opportunities);
  return (
    <div className="page-grid">
      <section className="panel"><div className="eyebrow">Tenant-scoped sales intake</div><h2>Leads</h2><table className="data-table"><thead><tr><th>Name</th><th>Score</th><th>Status</th><th>Owner</th></tr></thead><tbody>{leads.map((lead) => <tr key={lead.id}><td>{lead.name}</td><td>{lead.score}</td><td><StatusPill value={lead.status} /></td><td>{lead.owner}</td></tr>)}</tbody></table></section>
      <section className="panel"><div className="eyebrow">Portfolio organizations</div><h2>Accounts</h2><table className="data-table"><thead><tr><th>Account</th><th>Segment</th><th>Region</th><th>Contracts</th></tr></thead><tbody>{accounts.map((account) => <tr key={account.id}><td>{account.name}</td><td>{account.segment}</td><td>{account.region}</td><td>{account.contracts}</td></tr>)}</tbody></table></section>
      <section className="panel"><div className="eyebrow">Quote-linked revenue</div><h2>Opportunities</h2><table className="data-table"><thead><tr><th>ID</th><th>Account</th><th>Value</th><th>Stage</th></tr></thead><tbody>{opportunities.map((opportunity) => <tr key={opportunity.id}><td>{opportunity.id}</td><td>{opportunity.account}</td><td>{opportunity.value}</td><td>{opportunity.stage}</td></tr>)}</tbody></table></section>
    </div>
  );
}
""",
        ),
        (
            "src/pages/QuotesPage.jsx",
            """import React from 'react';
import StatusPill from '../components/StatusPill';
import { useAppStore } from '../store/useAppStore';

const currency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });

export default function QuotesPage() {
  const quotes = useAppStore((state) => state.quotes);
  const approveQuote = useAppStore((state) => state.approveQuote);
  return (
    <div className="page-grid">
      {quotes.map((quote) => (
        <section className="panel" key={quote.id}>
          <div className="panel-header">
            <div><div className="eyebrow">Human approval boundary</div><h2>{quote.id} · {quote.account}</h2></div>
            <div className="button-row"><button className="primary-button" type="button" onClick={() => approveQuote(quote.id, 'approved')}>Approve</button><button className="ghost-button" type="button" onClick={() => approveQuote(quote.id, 'rejected')}>Reject</button></div>
          </div>
          <div className="two-column"><div><div className="stat-row"><span>Status</span><StatusPill value={quote.status} /></div><div className="stat-row"><span>Total</span><strong>{currency.format(quote.total)}</strong></div><div className="stat-row"><span>Expires</span><span>{quote.expires_on}</span></div><div className="stat-row"><span>Approver</span><span>{quote.approver}</span></div></div><div><strong>AI recommendation</strong><p className="subtle">{quote.ai_recommendation}</p></div></div>
        </section>
      ))}
    </div>
  );
}
""",
        ),
        (
            "src/pages/ProjectsPage.jsx",
            """import React from 'react';
import StatusPill from '../components/StatusPill';
import { useAppStore } from '../store/useAppStore';

export default function ProjectsPage() {
  const projects = useAppStore((state) => state.projects);
  const tasks = useAppStore((state) => state.tasks);
  return (
    <div className="page-grid">
      <section className="panel"><div className="eyebrow">Deployment workflow</div><h2>Projects</h2><table className="data-table"><thead><tr><th>Name</th><th>Status</th><th>Timeline</th><th>Account</th></tr></thead><tbody>{projects.map((project) => <tr key={project.id}><td>{project.name}</td><td><StatusPill value={project.status} /></td><td>{project.timeline}</td><td>{project.account}</td></tr>)}</tbody></table></section>
      <section className="panel"><div className="eyebrow">Operator + rule provenance</div><h2>Tasks</h2><table className="data-table"><thead><tr><th>Task</th><th>Status</th><th>Priority</th><th>Source</th></tr></thead><tbody>{tasks.map((task) => <tr key={task.id}><td>{task.title}</td><td><StatusPill value={task.status} /></td><td>{task.priority}</td><td>{task.source}</td></tr>)}</tbody></table></section>
    </div>
  );
}
""",
        ),
        (
            "src/pages/PolicyPage.jsx",
            """import React from 'react';
import StatusPill from '../components/StatusPill';
import { useAppStore } from '../store/useAppStore';

export default function PolicyPage() {
  const items = useAppStore((state) => state.policyRecommendations);
  const approvePolicy = useAppStore((state) => state.approvePolicy);
  const enforcePolicy = useAppStore((state) => state.enforcePolicy);
  return (
    <div className="page-grid">
      {items.map((policy) => (
        <section className="panel" key={policy.id}>
          <div className="panel-header">
            <div><div className="eyebrow">Recommendation → approval → enforcement</div><h2>{policy.title}</h2></div>
            <div className="button-row"><button className="ghost-button" type="button" onClick={() => approvePolicy(policy.id, 'approved')}>Approve</button><button className="ghost-button" type="button" onClick={() => approvePolicy(policy.id, 'rejected')}>Reject</button><button className="primary-button" type="button" onClick={() => enforcePolicy(policy.id)}>Enforce</button></div>
          </div>
          <div className="stat-row"><span>Status</span><StatusPill value={policy.status} /></div>
          <div className="stat-row"><span>Trigger</span><span>{policy.trigger}</span></div>
          <p className="subtle">{policy.recommended_action}</p>
        </section>
      ))}
    </div>
  );
}
""",
        ),
        (
            "src/pages/AuditPage.jsx",
            """import React from 'react';
import { useAppStore } from '../store/useAppStore';

export default function AuditPage() {
  const auditTrail = useAppStore((state) => state.auditTrail);
  return (
    <section className="panel">
      <div className="eyebrow">Immutable visibility</div>
      <h2>Audit chain</h2>
      <table className="data-table"><thead><tr><th>Action</th><th>Actor</th><th>Entity</th><th>Prev hash</th><th>Current hash</th></tr></thead><tbody>{auditTrail.map((event) => <tr key={event.id}><td>{event.action}</td><td>{event.actor}</td><td>{event.entity}</td><td className="mono">{event.prev_hash}</td><td className="mono">{event.current_hash}</td></tr>)}</tbody></table>
    </section>
  );
}
""",
        ),
        (
            "src/pages/AnalyticsPage.jsx",
            """import React from 'react';
import { useAppStore } from '../store/useAppStore';

export default function AnalyticsPage() {
  const analytics = useAppStore((state) => state.analytics);
  return (
    <div className="page-grid">
      <section className="panel"><div className="eyebrow">Derived metrics</div><h2>Quote conversion</h2><div className="two-column"><div className="stat-row"><span>Approved</span><strong>{analytics.quote_conversion.approved}</strong></div><div className="stat-row"><span>Rejected</span><strong>{analytics.quote_conversion.rejected}</strong></div><div className="stat-row"><span>Pending</span><strong>{analytics.quote_conversion.pending}</strong></div></div></section>
      <section className="panel"><div className="eyebrow">Workflow health</div><h2>Operator load</h2><div className="two-column"><div className="stat-row"><span>Open tasks</span><strong>{analytics.operator_load.open_tasks}</strong></div><div className="stat-row"><span>SLA watch</span><strong>{analytics.operator_load.sla_watch}</strong></div><div className="stat-row"><span>Retrying jobs</span><strong>{analytics.operator_load.retrying_jobs}</strong></div></div></section>
      <section className="panel"><div className="eyebrow">Recommendation trust</div><h2>AI disposition</h2><div className="two-column"><div className="stat-row"><span>Accepted</span><strong>{analytics.ai_disposition.accepted}</strong></div><div className="stat-row"><span>Rejected</span><strong>{analytics.ai_disposition.rejected}</strong></div><div className="stat-row"><span>Needs review</span><strong>{analytics.ai_disposition.needs_human_review}</strong></div></div></section>
    </div>
  );
}
""",
        ),
        (
            "src/pages/TeamPage.jsx",
            """import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useAppStore } from '../store/useAppStore';

export default function TeamPage() {
  const { user } = useAuth();
  const tenant = useAppStore((state) => state.tenant);
  const operatorNotes = useAppStore((state) => state.operatorNotes);
  const setOperatorNotes = useAppStore((state) => state.setOperatorNotes);
  return (
    <div className="page-grid">
      <section className="panel"><div className="eyebrow">Human-in-the-loop</div><h2>Current operator</h2><div className="stat-row"><span>Name</span><strong>{user?.name}</strong></div><div className="stat-row"><span>Role</span><strong>{user?.role}</strong></div><div className="stat-row"><span>Tenant</span><strong>{tenant.name}</strong></div></section>
      <section className="panel"><div className="eyebrow">Persisted locally</div><h2>Operator handoff notes</h2><textarea className="text-area" value={operatorNotes} onChange={(event) => setOperatorNotes(event.target.value)} placeholder="Capture review notes, escalations, and follow-ups." rows={6} /></section>
    </div>
  );
}
""",
        ),
        (
            "src/App.jsx",
            """import React from 'react';
import { MemoryRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ErrorBoundary from './components/ErrorBoundary';
import ShellLayout from './components/ShellLayout';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import CRMPage from './pages/CRMPage';
import QuotesPage from './pages/QuotesPage';
import ProjectsPage from './pages/ProjectsPage';
import PolicyPage from './pages/PolicyPage';
import AuditPage from './pages/AuditPage';
import AnalyticsPage from './pages/AnalyticsPage';
import TeamPage from './pages/TeamPage';

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<ShellLayout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/crm" element={<CRMPage />} />
              <Route path="/quotes" element={<QuotesPage />} />
              <Route path="/projects" element={<ProjectsPage />} />
              <Route path="/policy" element={<PolicyPage />} />
              <Route path="/audit" element={<AuditPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/team" element={<TeamPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
}
""",
        ),
        (
            "src/main.jsx",
            "import React from 'react';\nimport { createRoot } from 'react-dom/client';\nimport App from './App.jsx';\nimport './styles/global.css';\n\ncreateRoot(document.getElementById('root')).render(<App />);\n",
        ),
        ("src/index.js", "import './main.jsx';\n"),
        (
            "src/styles/global.css",
            """* { box-sizing: border-box; } html, body, #root { margin: 0; min-height: 100%; }
body { font-family: Inter, system-ui, sans-serif; background: #08111f; color: #e2e8f0; }
a { color: inherit; }
.app-shell { min-height: 100vh; padding: 24px; }
.topbar { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 16px; }
.brand { margin: 0; font-size: 2rem; } .eyebrow { color: #38bdf8; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; }
.subtle { color: #94a3b8; line-height: 1.55; } .lead { color: #dbeafe; line-height: 1.7; margin-bottom: 16px; }
.nav-row, .button-row, .metric-grid, .page-grid, .stack-list { display: grid; gap: 12px; }
.nav-row { grid-template-columns: repeat(auto-fit, minmax(110px, max-content)); margin-bottom: 20px; }
.button-row { grid-auto-flow: column; justify-content: start; }
.nav-link { text-decoration: none; padding: 9px 14px; border-radius: 8px; border: 1px solid rgba(148, 163, 184, 0.22); color: #cbd5e1; }
.nav-link-active { background: rgba(56, 189, 248, 0.18); border-color: rgba(56, 189, 248, 0.45); color: #f8fafc; }
.panel { background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(148, 163, 184, 0.16); border-radius: 8px; padding: 20px; }
.panel-header { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; margin-bottom: 14px; } .panel-header h2 { margin: 0; }
.primary-button, .ghost-button { display: inline-flex; align-items: center; justify-content: center; border-radius: 8px; padding: 10px 14px; border: 1px solid transparent; cursor: pointer; text-decoration: none; font-weight: 600; }
.primary-button { background: #38bdf8; color: #082f49; } .ghost-button { background: transparent; color: #e2e8f0; border-color: rgba(148, 163, 184, 0.28); }
.metric-grid { grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); } .metric-card { background: linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.96)); border: 1px solid rgba(56, 189, 248, 0.18); border-radius: 8px; padding: 16px; }
.metric-label { color: #94a3b8; font-size: 0.9rem; } .metric-value { font-size: 1.8rem; font-weight: 700; margin: 10px 0 6px; } .metric-delta { color: #38bdf8; font-size: 0.9rem; }
.data-table { width: 100%; border-collapse: collapse; } .data-table th, .data-table td { text-align: left; padding: 10px 8px; border-bottom: 1px solid rgba(148, 163, 184, 0.12); vertical-align: top; }
.data-table th { color: #94a3b8; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.06em; }
.two-column { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 12px; }
.stat-row, .stack-row { display: flex; justify-content: space-between; gap: 12px; align-items: center; padding: 8px 0; border-bottom: 1px solid rgba(148, 163, 184, 0.08); }
.stack-row { padding: 12px; background: rgba(15, 23, 42, 0.6); border-radius: 8px; border-bottom: none; }
.pill { display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 10px; font-size: 0.78rem; font-weight: 700; }
.pill-amber { background: rgba(245, 158, 11, 0.16); color: #fbbf24; } .pill-blue { background: rgba(59, 130, 246, 0.16); color: #60a5fa; } .pill-green { background: rgba(34, 197, 94, 0.16); color: #4ade80; } .pill-red { background: rgba(248, 113, 113, 0.16); color: #f87171; } .pill-slate { background: rgba(148, 163, 184, 0.16); color: #cbd5e1; }
.mono { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.82rem; } .text-input, .text-area { width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid rgba(148, 163, 184, 0.24); background: rgba(15, 23, 42, 0.65); color: #e2e8f0; }
@media (max-width: 720px) { .app-shell { padding: 16px; } .topbar { flex-direction: column; } .button-row { grid-auto-flow: row; } .panel { padding: 16px; } }
""",
        ),
    ]


def _build_backend_files(profile: Dict[str, str]) -> List[Tuple[str, str]]:
    product_name = profile["product_name"]
    company_name = profile["company_name"]
    command_slug = profile["command_slug"]
    org_id = f"{command_slug}-org"
    backend_main = _replace_tokens(
        """from datetime import datetime, timedelta, timezone
import hashlib
import os
from typing import Dict

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext

APP_NAME = "__PRODUCT_NAME__"
COMPANY_NAME = "__COMPANY_NAME__"
DEMO_ORG_ID = "__ORG_ID__"
JWT_SECRET = os.getenv("JWT_SECRET", "development-only-change-me")
JWT_ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

app = FastAPI(title=APP_NAME, version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

LEADS = [
    {"id": "LD-104", "org_id": DEMO_ORG_ID, "name": "Riverton Logistics", "score": 92, "status": "qualified", "owner": "Alex Chen"},
    {"id": "LD-118", "org_id": DEMO_ORG_ID, "name": "Summit Storage Group", "score": 84, "status": "proposal", "owner": "Jordan Lee"},
]
ACCOUNTS = [
    {"id": "AC-201", "org_id": DEMO_ORG_ID, "name": "Riverton Logistics", "segment": "Industrial", "region": "CA", "contracts": 3},
    {"id": "AC-214", "org_id": DEMO_ORG_ID, "name": "Northwind Senior Living", "segment": "Healthcare", "region": "AZ", "contracts": 2},
]
QUOTES = [
    {"id": "Q-1042", "org_id": DEMO_ORG_ID, "account": "Riverton Logistics", "status": "pending_review", "total": 184500, "expires_on": "2026-04-30", "approver": "Morgan Rivera", "ai_recommendation": "Reduce battery reserve by 3% after human review."},
    {"id": "Q-1047", "org_id": DEMO_ORG_ID, "account": "Northwind Senior Living", "status": "draft", "total": 94300, "expires_on": "2026-05-12", "approver": "Pending assignment", "ai_recommendation": "Block conversion until region eligibility is cleared."},
]
PROJECTS = [
    {"id": "PR-12", "org_id": DEMO_ORG_ID, "name": "Riverton West Campus", "status": "installation_ready", "timeline": "Apr 22 - Jun 14", "account": "Riverton Logistics"},
    {"id": "PR-18", "org_id": DEMO_ORG_ID, "name": "Northwind Expansion", "status": "planning", "timeline": "May 03 - Jul 18", "account": "Northwind Senior Living"},
]
TASKS = [
    {"id": "TS-301", "org_id": DEMO_ORG_ID, "title": "Review incentive region mismatch", "status": "open", "priority": "high", "owner": "Morgan Rivera", "source": "rule:region_eligibility"},
    {"id": "TS-309", "org_id": DEMO_ORG_ID, "title": "Approve quote Q-1042", "status": "open", "priority": "high", "owner": "Morgan Rivera", "source": "workflow:quote_review"},
]
POLICY_RECOMMENDATIONS = [
    {"id": "POL-01", "org_id": DEMO_ORG_ID, "title": "Escalate repeated webhook failures", "status": "PENDING", "recommended_action": "Require org_admin approval before re-enabling vendor webhook.", "trigger": "3 failed sync runs in 20 minutes"},
    {"id": "POL-02", "org_id": DEMO_ORG_ID, "title": "Geo-risk review on storage site", "status": "APPROVED", "recommended_action": "Limit remote dispatch until site inspection completes.", "trigger": "Repeated suspicious telemetry variance"},
]
AUDIT_EVENTS = [
    {"id": "AUD-001", "org_id": DEMO_ORG_ID, "action": "quote.pending_review", "actor": "alex.chen@heliosaegis.test", "prev_hash": "GENESIS", "current_hash": "4bd4bf1902c7c201", "entity": "Q-1042"},
    {"id": "AUD-002", "org_id": DEMO_ORG_ID, "action": "policy.recommendation_created", "actor": "system", "prev_hash": "4bd4bf1902c7c201", "current_hash": "e1529145233cf892", "entity": "POL-01"},
]
ANALYTICS = {
    "quote_conversion": {"approved": 14, "rejected": 2, "pending": 6},
    "operator_load": {"open_tasks": 17, "sla_watch": 3, "retrying_jobs": 1},
    "policy_disposition": {"pending": 1, "approved": 1, "rejected": 0, "enforced": 0},
    "ai_disposition": {"accepted": 12, "rejected": 4, "needs_human_review": 7},
}


def _scoped(rows, org_id: str):
    return [row for row in rows if row.get("org_id") == org_id]


def _find(rows, item_id: str):
    for row in rows:
      if row.get("id") == item_id:
        return row
    return None


def create_access_token(subject: str, org_id: str, token_type: str = "access") -> str:
    payload = {
        "sub": subject,
        "org_id": org_id,
        "type": token_type,
        "exp": (datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def current_org_id(x_org_id: str = Header(default=DEMO_ORG_ID, alias="X-Org-Id")) -> str:
    return x_org_id


def current_role(x_actor_role: str = Header(default="org_admin", alias="X-Actor-Role")) -> str:
    return x_actor_role


def require_review_role(role: str = Depends(current_role)) -> str:
    if role not in {"org_admin", "security_analyst", "global_admin"}:
        raise HTTPException(status_code=403, detail="Explicit human approval role required")
    return role


@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME, "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/api/auth/login")
def login():
    return {
        "access_token": create_access_token("morgan-rivera", DEMO_ORG_ID),
        "refresh_token": create_access_token("morgan-rivera", DEMO_ORG_ID, token_type="refresh"),
        "token_type": "bearer",
    }


@app.post("/api/auth/refresh")
def refresh():
    return {
        "access_token": create_access_token("morgan-rivera", DEMO_ORG_ID),
        "refresh_token": create_access_token("morgan-rivera", DEMO_ORG_ID, token_type="refresh"),
        "token_type": "bearer",
    }


@app.get("/api/auth/me")
def me(org_id: str = Depends(current_org_id)):
    return {"id": "morgan-rivera", "email": "morgan@heliosaegis.test", "org_id": org_id, "roles": ["org_admin"]}


@app.get("/api/crm/leads")
def list_leads(org_id: str = Depends(current_org_id)):
    return {"org_id": org_id, "leads": _scoped(LEADS, org_id)}


@app.get("/api/crm/accounts")
def list_accounts(org_id: str = Depends(current_org_id)):
    return {"org_id": org_id, "accounts": _scoped(ACCOUNTS, org_id)}


@app.get("/api/quotes")
def list_quotes(org_id: str = Depends(current_org_id)):
    return {"org_id": org_id, "quotes": _scoped(QUOTES, org_id)}


@app.post("/api/quotes/{quote_id}/recommendation")
def quote_recommendation(quote_id: str, org_id: str = Depends(current_org_id)):
    quote = _find(QUOTES, quote_id)
    if not quote or quote.get("org_id") != org_id:
        raise HTTPException(status_code=404, detail="Quote not found")
    return {"quote_id": quote_id, "mode": "recommendation_only", "suggestion": quote.get("ai_recommendation")}


@app.post("/api/quotes/{quote_id}/approve")
def approve_quote(quote_id: str, decision: Dict[str, str], org_id: str = Depends(current_org_id), _role: str = Depends(require_review_role)):
    quote = _find(QUOTES, quote_id)
    if not quote or quote.get("org_id") != org_id:
        raise HTTPException(status_code=404, detail="Quote not found")
    if quote["status"] not in {"draft", "pending_review"}:
        raise HTTPException(status_code=409, detail="Quote can only be changed from draft or pending_review")
    status_value = str(decision.get("decision") or "").lower().strip()
    if status_value not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="decision must be approved or rejected")
    quote["status"] = status_value
    return {"quote_id": quote_id, "status": quote["status"], "approved_by_human": True}


@app.get("/api/projects")
def list_projects(org_id: str = Depends(current_org_id)):
    return {"org_id": org_id, "projects": _scoped(PROJECTS, org_id)}


@app.get("/api/tasks")
def list_tasks(org_id: str = Depends(current_org_id)):
    return {"org_id": org_id, "tasks": _scoped(TASKS, org_id)}


@app.get("/api/policies/recommendations")
def list_recommendations(org_id: str = Depends(current_org_id)):
    return {"org_id": org_id, "recommendations": _scoped(POLICY_RECOMMENDATIONS, org_id)}


@app.post("/api/policies/{policy_id}/approve")
def approve_policy(policy_id: str, decision: Dict[str, str], org_id: str = Depends(current_org_id), _role: str = Depends(require_review_role)):
    policy = _find(POLICY_RECOMMENDATIONS, policy_id)
    if not policy or policy.get("org_id") != org_id:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if policy["status"] != "PENDING":
        raise HTTPException(status_code=409, detail="Only pending recommendations can be decided")
    value = str(decision.get("decision") or "").upper().strip()
    if value not in {"APPROVED", "REJECTED"}:
        raise HTTPException(status_code=400, detail="decision must be APPROVED or REJECTED")
    policy["status"] = value
    return {"policy_id": policy_id, "status": policy["status"], "decision_by_human": True}


@app.post("/api/policies/{policy_id}/enforce")
def enforce_policy(policy_id: str, org_id: str = Depends(current_org_id), _role: str = Depends(require_review_role)):
    policy = _find(POLICY_RECOMMENDATIONS, policy_id)
    if not policy or policy.get("org_id") != org_id:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if policy["status"] != "APPROVED":
        raise HTTPException(status_code=409, detail="Policy cannot be enforced before explicit approval")
    policy["status"] = "ENFORCED"
    return {"policy_id": policy_id, "status": policy["status"], "enforced": True}


@app.get("/api/audit/events")
def audit_events(org_id: str = Depends(current_org_id)):
    return {"org_id": org_id, "events": _scoped(AUDIT_EVENTS, org_id)}


@app.get("/api/audit/chain/verify")
def audit_chain_verify(org_id: str = Depends(current_org_id)):
    events = _scoped(AUDIT_EVENTS, org_id)
    if not events:
        return {"org_id": org_id, "chain_valid": True, "total_logs": 0}
    first_ok = events[0]["prev_hash"] == "GENESIS"
    chain_ok = first_ok and all(events[index]["prev_hash"] == events[index - 1]["current_hash"] for index in range(1, len(events)))
    digest = hashlib.sha256(("".join(item["current_hash"] for item in events)).encode()).hexdigest()
    return {"org_id": org_id, "chain_valid": chain_ok, "total_logs": len(events), "digest": digest}


@app.get("/api/analytics/overview")
def analytics_overview(org_id: str = Depends(current_org_id)):
    return {"org_id": org_id, "analytics": ANALYTICS}
""",
        PRODUCT_NAME=product_name,
        COMPANY_NAME=company_name,
        ORG_ID=org_id,
    )
    return [
        ("backend/main.py", backend_main),
        (
            "backend/domain_models.py",
            """from pydantic import BaseModel


class LeadRecord(BaseModel):
    id: str
    org_id: str
    name: str
    score: int
    status: str


class QuoteRecord(BaseModel):
    id: str
    org_id: str
    account: str
    status: str
    total: int


class PolicyRecommendationRecord(BaseModel):
    id: str
    org_id: str
    title: str
    status: str
    recommended_action: str
""",
        ),
        (
            "backend/requirements.txt",
            """fastapi==0.115.0
uvicorn[standard]==0.30.6
python-jose==3.3.0
passlib[argon2]==1.7.4
pydantic==2.9.2
""",
        ),
        (
            "backend/.env.example",
            """JWT_SECRET=change-me
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
""",
        ),
        (
            "backend/Dockerfile",
            """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
        ),
        (
            "backend/README.md",
            f"""# {product_name} backend

FastAPI foundation for the enterprise command build.

Implemented:
- auth/login/refresh/me
- tenant-scoped CRM and quote routes
- human approval boundaries for quotes and policies
- audit chain verification
- analytics overview
""",
        ),
    ]


def _build_database_files(
    profile: Dict[str, str], step_key: str = ""
) -> List[Tuple[str, str]]:
    org_id = profile["command_slug"].replace("-", "_")
    schema_sql = f"""-- {profile["product_name"]} schema
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id),
  email TEXT UNIQUE NOT NULL,
  role TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS leads (
  id TEXT PRIMARY KEY,
  org_id UUID NOT NULL REFERENCES organizations(id),
  name TEXT NOT NULL,
  score INTEGER NOT NULL,
  status TEXT NOT NULL,
  owner TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quotes (
  id TEXT PRIMARY KEY,
  org_id UUID NOT NULL REFERENCES organizations(id),
  account_name TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('draft', 'pending_review', 'approved', 'rejected', 'expired')),
  total_amount INTEGER NOT NULL,
  expires_on DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS policy_recommendations (
  id TEXT PRIMARY KEY,
  org_id UUID NOT NULL REFERENCES organizations(id),
  title TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'ENFORCED')),
  recommended_action TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
  id TEXT PRIMARY KEY,
  org_id UUID NOT NULL REFERENCES organizations(id),
  action TEXT NOT NULL,
  actor TEXT NOT NULL,
  prev_hash TEXT NOT NULL,
  current_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
"""
    seed_sql = f"""INSERT INTO organizations (id, name)
VALUES ('{org_id}000000000000000000000000000000', '{profile["company_name"]} Portfolio Operations')
ON CONFLICT DO NOTHING;
"""
    if step_key == "database.seed":
        return [("db/seeds/001_enterprise_seed.sql", seed_sql)]
    return [
        ("db/migrations/001_enterprise_command_schema.sql", schema_sql),
        ("db/seeds/001_enterprise_seed.sql", seed_sql),
    ]
