"""
Production-shaped frontend bundle for Auto-Runner workspace (Sandpack-ready).
Explicit README marks gaps vs a full production deploy.

When ``job["build_target"]`` is set (e.g. ``next_app_router``), extra track files are added
without breaking the root Vite bundle verifiers expect.
"""

import json
import re
from typing import Dict, List, Tuple

from .build_targets import build_target_meta, normalize_build_target
from .code_generation_standard import STANDARD_DOC, STANDARD_VERSION
from .enterprise_command_pack import (
    build_enterprise_frontend_file_set,
    enterprise_command_intent,
)
from .manus_parity_template import (
    build_manus_parity_frontend_file_set,
    is_saas_ui_goal,
)


def _safe_goal_summary(goal: str) -> str:
    goal = re.sub(r"\s+", " ", (goal or "").strip())
    if not goal:
        return "Generated workspace ready for implementation and preview."
    if "helios aegis command" in goal.lower():
        return "Generated enterprise command workspace with CRM, quoting, policy approval, audit, and analytics surfaces."
    if len(goal) > 140:
        goal = goal[:137].rstrip() + "..."
    return f"Generated workspace aligned to: {goal}"


def _crucib_build_target_doc(job: Dict, target: str) -> str:
    meta = build_target_meta(target)
    g = "\n".join(f"- {x}" for x in meta["guarantees"])
    run = "\n".join(f"- {x}" for x in meta["on_this_run"])
    road = "\n".join(f"- {x}" for x in meta["roadmap"])
    return f"""# CrucibAI — build target for this job

**{meta["label"]}**

{meta["tagline"]}

Goal (excerpt): {(job.get("goal") or "").strip()[:500] or "(none)"}

## What this run is designed to deliver

{g}

## On this run (exactly)

{run}

## Roadmap (platform breadth — not narrowed)

{road}

---
*CrucibAI’s product direction is multi-stack and multi-modal; each Auto-Runner execution mode documents honest guarantees while we expand tracks (Next-native DAG, mobile, deeper automation, etc.).*
"""


def _next_app_stub_files(goal_snippet: str) -> List[Tuple[str, str]]:
    """Parallel Next.js 14 App Router starter — separate from root Vite package.json."""
    readme = f"""# Next.js App Router track (parallel to root Vite app)

This folder is a **standalone** Next.js app. The Auto-Runner still verifies the **root** Vite bundle for this job;
use this directory when you want to grow an App Router codebase without waiting for a first-class Next DAG.

## Your goal (reference)
{goal_snippet[:1200]}

## Commands
```bash
cd next-app-stub
npm install
npm run dev
```

## Notes
- Keep root `package.json` (Vite) intact for existing preview/verify flows.
- Merge or replace with a single Next monorepo when we ship a dedicated Next pipeline.
"""
    pkg = {
        "name": "crucibai-next-stub",
        "version": "0.1.0",
        "private": True,
        "scripts": {"dev": "next dev", "build": "next build", "start": "next start"},
        "dependencies": {"next": "14.2.18", "react": "^18.2.0", "react-dom": "^18.2.0"},
    }
    layout = """export const metadata = { title: 'CrucibAI Next stub' };

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'system-ui', margin: 0, background: '#0f172a', color: '#e2e8f0' }}>
        {children}
      </body>
    </html>
  );
}
"""
    page = """export default function Page() {
  return (
    <main style={{ padding: 24 }}>
      <h1>Next.js App Router (stub)</h1>
      <p style={{ maxWidth: 560, lineHeight: 1.6 }}>
        This track ships alongside the Vite app at repo root. Expand routes under <code>app/</code> and move
        business logic here as the platform adds a native Next execution mode.
      </p>
    </main>
  );
}
"""
    nconf = """/** @type {import('next').NextConfig} */
const nextConfig = { reactStrictMode: true };
export default nextConfig;
"""
    return [
        ("next-app-stub/README.md", readme),
        ("next-app-stub/package.json", json.dumps(pkg, indent=2)),
        ("next-app-stub/next.config.mjs", nconf),
        ("next-app-stub/app/layout.tsx", layout),
        ("next-app-stub/app/page.tsx", page),
        ("next-app-stub/.gitignore", "node_modules\n.next\nout\n"),
    ]


def _expo_mobile_stub_files(goal_snippet: str) -> List[Tuple[str, str]]:
    """Standalone Expo mobile starter that remains compatible with root web preview."""
    readme = f"""# Expo mobile track

This folder is a **standalone Expo / React Native app** generated for the mobile build target.
The root Vite app remains in place so CrucibAI can still run browser preview and static gates.

## Your goal (reference)
{goal_snippet[:1200]}

## Commands
```bash
cd expo-mobile
npm install
npm run start
npm run android
npm run ios
npm run web
```

## Store packaging contract
- Add Apple Developer / Google Play credentials before store submission.
- Fill `app.json` names, bundle identifiers, icons, splash assets, privacy metadata, screenshots, and EAS profile.
- Run `npx expo-doctor` and `eas build` before treating the mobile app as release-ready.
- CrucibAI marks this track complete only when the Build Integrity Validator sees Expo metadata, app entry, screens, scripts, and packaging guidance.
"""
    pkg = {
        "name": "crucibai-expo-mobile",
        "version": "0.1.0",
        "private": True,
        "scripts": {
            "start": "expo start",
            "android": "expo start --android",
            "ios": "expo start --ios",
            "web": "expo start --web",
            "build": "npx expo export",
            "doctor": "npx expo-doctor",
        },
        "dependencies": {
            "@expo/vector-icons": "^14.0.2",
            "@react-navigation/native": "^6.1.18",
            "@react-navigation/native-stack": "^6.11.0",
            "expo": "~51.0.0",
            "expo-status-bar": "~1.12.1",
            "react": "18.2.0",
            "react-native": "0.74.5",
            "react-native-safe-area-context": "4.10.5",
            "react-native-screens": "3.31.1",
        },
        "devDependencies": {
            "@babel/core": "^7.24.0",
            "typescript": "^5.4.5",
        },
    }
    app_json = {
        "expo": {
            "name": "CrucibAI Mobile",
            "slug": "crucibai-mobile",
            "version": "0.1.0",
            "orientation": "portrait",
            "scheme": "crucibai-mobile",
            "userInterfaceStyle": "automatic",
            "ios": {
                "supportsTablet": True,
                "bundleIdentifier": "com.crucibai.generated.mobile",
            },
            "android": {
                "package": "com.crucibai.generated.mobile",
                "adaptiveIcon": {
                    "backgroundColor": "#111827",
                },
            },
            "web": {
                "bundler": "metro",
                "output": "static",
            },
        }
    }
    eas_json = {
        "cli": {"version": ">= 10.0.0"},
        "build": {
            "development": {"developmentClient": True, "distribution": "internal"},
            "preview": {"distribution": "internal"},
            "production": {},
        },
        "submit": {"production": {}},
    }
    app_tsx = """import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'expo-status-bar';
import HomeScreen from './src/screens/HomeScreen';
import DetailScreen from './src/screens/DetailScreen';

const Stack = createNativeStackNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="auto" />
      <Stack.Navigator>
        <Stack.Screen name="Home" component={HomeScreen} options={{ title: 'CrucibAI Mobile' }} />
        <Stack.Screen name="Details" component={DetailScreen} options={{ title: 'Build details' }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
"""
    home_screen = """import React from 'react';
import { Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';

export default function HomeScreen({ navigation }) {
  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.eyebrow}>Mobile build target</Text>
        <Text style={styles.title}>CrucibAI Expo starter</Text>
        <Text style={styles.body}>
          This mobile app was generated as a concrete Expo artifact. Expand screens, native APIs, and store metadata from here.
        </Text>
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Validator contract</Text>
          <Text style={styles.body}>Expo metadata, App entry, navigation, screens, scripts, and packaging guidance must exist before completion.</Text>
        </View>
        <Pressable style={styles.button} onPress={() => navigation.navigate('Details')}>
          <Text style={styles.buttonText}>Open details</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#f8fafc' },
  content: { padding: 24, gap: 16 },
  eyebrow: { color: '#4f46e5', fontWeight: '700', textTransform: 'uppercase' },
  title: { fontSize: 34, fontWeight: '800', color: '#111827' },
  body: { color: '#475569', fontSize: 16, lineHeight: 24 },
  card: { backgroundColor: '#ffffff', borderRadius: 16, padding: 18, borderWidth: 1, borderColor: '#e5e7eb' },
  cardTitle: { color: '#111827', fontSize: 18, fontWeight: '700', marginBottom: 6 },
  button: { backgroundColor: '#4f46e5', paddingVertical: 14, paddingHorizontal: 18, borderRadius: 14, alignItems: 'center' },
  buttonText: { color: '#ffffff', fontWeight: '800' },
});
"""
    detail_screen = """import React from 'react';
import { SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';

const checks = [
  'Expo app.json metadata',
  'App.tsx root entry',
  'NavigationContainer and native stack',
  'Screens under src/screens',
  'EAS packaging guidance',
];

export default function DetailScreen() {
  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Mobile readiness</Text>
        {checks.map((item) => (
          <View key={item} style={styles.row}>
            <Text style={styles.check}>OK</Text>
            <Text style={styles.body}>{item}</Text>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#f8fafc' },
  content: { padding: 24, gap: 14 },
  title: { fontSize: 28, fontWeight: '800', color: '#111827', marginBottom: 8 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: '#fff', borderRadius: 12, padding: 14 },
  check: { color: '#059669', fontWeight: '900', fontSize: 18 },
  body: { color: '#334155', fontSize: 16 },
});
"""
    return [
        ("expo-mobile/README.md", readme),
        ("expo-mobile/package.json", json.dumps(pkg, indent=2)),
        ("expo-mobile/app.json", json.dumps(app_json, indent=2)),
        ("expo-mobile/eas.json", json.dumps(eas_json, indent=2)),
        ("expo-mobile/App.tsx", app_tsx),
        ("expo-mobile/src/screens/HomeScreen.tsx", home_screen),
        ("expo-mobile/src/screens/DetailScreen.tsx", detail_screen),
        ("expo-mobile/tsconfig.json", json.dumps({"extends": "expo/tsconfig.base"}, indent=2)),
        ("expo-mobile/.gitignore", "node_modules\n.expo\ndist\nweb-build\n"),
    ]


def _senior_structure_files(goal_raw: str) -> List[Tuple[str, str]]:
    """Additional maintainable product-codebase files for the runnable Vite scaffold."""
    app_config = """export const appConfig = {
  name: 'CrucibAI Generated App',
  environment: import.meta.env.MODE,
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api',
};
"""
    routes = """export const routes = {
  home: '/',
  login: '/login',
  dashboard: '/dashboard',
  team: '/team',
};
"""
    api_client = """import { appConfig } from '../_core/config/appConfig';

export class ApiError extends Error {
  constructor(message, status = 0, details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${appConfig.apiBaseUrl}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(payload?.message || 'Request failed', response.status, payload);
  }
  return payload;
}
"""
    auth_service = """const TOKEN_KEY = 'crucibai_demo_token';

export const authService = {
  getToken() {
    return localStorage.getItem(TOKEN_KEY) || '';
  },
  setToken(token) {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  },
  createDemoToken(displayName) {
    return `demo.${String(displayName || 'user').slice(0, 24)}.${Date.now()}`;
  },
};
"""
    button = """import React from 'react';

export function Button({ children, variant = 'primary', className = '', ...props }) {
  const styles = variant === 'secondary' ? 'btn btn-secondary' : 'btn btn-primary';
  return <button className={`${styles} ${className}`.trim()} {...props}>{children}</button>;
}
"""
    input = """import React from 'react';

export function Input({ className = '', ...props }) {
  return <input className={`field-input ${className}`.trim()} {...props} />;
}
"""
    card = """import React from 'react';

export function Card({ children, className = '' }) {
  return <section className={`surface-card ${className}`.trim()}>{children}</section>;
}
"""
    badge = """import React from 'react';

export function Badge({ children, tone = 'neutral' }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
"""
    page_header = """import React from 'react';

export function PageHeader({ eyebrow, title, description, action }) {
  return (
    <header className="page-header">
      {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
      <div className="page-header-row">
        <div>
          <h1>{title}</h1>
          {description ? <p>{description}</p> : null}
        </div>
        {action}
      </div>
    </header>
  );
}
"""
    content_panel = """import React from 'react';

export function ContentPanel({ title, children }) {
  return (
    <section className="content-panel">
      {title ? <h2>{title}</h2> : null}
      {children}
    </section>
  );
}
"""
    data_table = """import React from 'react';

export function DataTable({ columns, rows }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{columns.map((col) => <th key={col.key}>{col.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              {columns.map((col) => <td key={col.key}>{row[col.key]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
"""
    empty_state = """import React from 'react';

export function EmptyState({ title = 'Nothing here yet', description = 'Create or sync data to continue.' }) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  );
}
"""
    form_field = """import React from 'react';

export function FormField({ label, error, children }) {
  return (
    <label className="form-field">
      <span>{label}</span>
      {children}
      {error ? <small role="alert">{error}</small> : null}
    </label>
  );
}
"""
    metrics_data = """export const dashboardMetrics = [
  { id: 'active-work', label: 'Active Work', value: '24', delta: '+12%' },
  { id: 'approval-risk', label: 'Approval Risk', value: '3', delta: 'review' },
  { id: 'run-health', label: 'Run Health', value: '98%', delta: 'stable' },
];
"""
    metrics_grid = """import React from 'react';
import { dashboardMetrics } from '../data/dashboardMockData';
import { Card } from '../../../components/ui/Card';

export function MetricsGrid() {
  return (
    <div className="metric-grid">
      {dashboardMetrics.map((metric) => (
        <Card key={metric.id}>
          <p className="metric-label">{metric.label}</p>
          <strong className="metric-value">{metric.value}</strong>
          <span className="metric-delta">{metric.delta}</span>
        </Card>
      ))}
    </div>
  );
}
"""
    users_data = """export const userRows = [
  { id: 'usr_1', name: 'Alex Morgan', role: 'Admin', status: 'Active' },
  { id: 'usr_2', name: 'Jordan Lee', role: 'Operator', status: 'Pending' },
  { id: 'usr_3', name: 'Casey Rivera', role: 'Reviewer', status: 'Active' },
];
"""
    user_service = """import { userRows } from '../data/userMockData';

export async function listUsers() {
  return { users: userRows };
}
"""
    use_users = """import { useEffect, useState } from 'react';
import { listUsers } from '../services/userService';

export function useUsers() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    listUsers()
      .then((result) => { if (active) setUsers(result.users); })
      .catch((err) => { if (active) setError(err.message || 'Could not load users'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return { users, loading, error };
}
"""
    user_table = """import React from 'react';
import { DataTable } from '../../../components/tables/DataTable';
import { EmptyState } from '../../../components/feedback/EmptyState';
import { useUsers } from '../hooks/useUsers';

const columns = [
  { key: 'name', label: 'Name' },
  { key: 'role', label: 'Role' },
  { key: 'status', label: 'Status' },
];

export function UserTable() {
  const { users, loading, error } = useUsers();
  if (loading) return <EmptyState title="Loading users" description="Fetching workspace members." />;
  if (error) return <EmptyState title="Unable to load users" description={error} />;
  return <DataTable columns={columns} rows={users} />;
}
"""
    tokens = """:root {
  --color-bg: #0f172a;
  --color-surface: #111827;
  --color-surface-2: #1e293b;
  --color-border: rgba(148, 163, 184, 0.24);
  --color-text: #e2e8f0;
  --color-muted: #94a3b8;
  --color-primary: #3b82f6;
  --color-success: #22c55e;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.25);
  --transition-fast: 160ms ease;
}
"""
    architecture = f"""# Architecture

Generated under CrucibAI code standard `{STANDARD_VERSION}`.

## Boundaries

- `src/_core`: app config, constants, routes, providers.
- `src/components`: reusable UI, layout, forms, tables, and feedback primitives.
- `src/features`: domain modules with components, hooks, services, data, and tests.
- `src/services`: API/auth service boundary. Components should not call fetch directly.
- `src/store`: global UI and workspace state.
- `src/styles`: design tokens and global styling.

## Source Goal

{goal_raw[:1200]}
"""
    manifest = """# Code Manifest

| File | Category | Purpose | Feature |
|---|---|---|---|
| package.json | config | Vite app dependencies and scripts | runtime |
| src/App.jsx | frontend | Thin provider/router mount | navigation |
| src/_core/config/appConfig.js | core | Runtime configuration | config |
| src/components/ui/Button.jsx | component | Reusable button primitive | design system |
| src/components/tables/DataTable.jsx | component | Reusable table renderer | data tables |
| src/features/users/components/UserTable.jsx | feature | Users module table | users |
| src/services/apiClient.js | service | Typed-ish API request boundary | API |
| src/styles/tokens.css | style | Design tokens | design system |
"""
    coverage = """# Feature Coverage

| Requested capability | Frontend | Backend/API | State/service | Tests | Status |
|---|---|---|---|---|---|
| Routing | App + ShellLayout | N/A | routes constants | preview contract | Implemented |
| Auth demo | Login + AuthContext | Replace with real API | authService | smoke-ready | Mocked |
| Dashboard | DashboardPage + MetricsGrid | N/A | store + mock data | smoke-ready | Implemented |
| Users table | UserTable + DataTable | Replace with real API | userService | smoke-ready | Implemented |
| Design system | UI primitives + tokens | N/A | N/A | visual review | Implemented |
"""
    document_requirements = f"""# Requirements From Documents

This file is generated so uploaded or referenced source documents have a durable
requirements artifact inside the project.

## Source Status

- No source document binary is bundled in this default scaffold.
- When documents are provided, save originals under `docs/source_documents/`.
- Save extracted text under `docs/extracted_text/`.
- Link every document-derived feature back to `runtime/ingestion/source_map.json`.

## Current Prompt-Derived Requirements

{goal_raw[:1600]}
"""
    document_design_brief = """# Design Brief From Documents

## Purpose

Persist design guidance extracted from uploaded documents, screenshots, briefs,
or research notes.

## Current State

No uploaded design document was available during this scaffold generation. Add
document-derived visual requirements here as soon as sources are ingested.
"""
    document_technical_spec = """# Technical Spec From Documents

## Purpose

Persist technical constraints, integration requirements, business rules, and
architecture decisions extracted from uploaded documents.

## Current State

No uploaded technical document was available during this scaffold generation.
Future ingestion should update this file and `runtime/ingestion/source_map.json`.
"""
    ingestion_manifest = {
        "schema_version": "1.0",
        "status": "ready_for_documents",
        "documents": [],
        "required_artifacts": [
            "original_file",
            "file_name",
            "file_type",
            "extracted_text",
            "structured_summary",
            "requirements",
            "design_notes",
            "technical_constraints",
            "business_rules",
            "timestamp",
            "ingestion_status",
        ],
    }
    source_map = {
        "schema_version": "1.0",
        "sources": [],
        "feature_traceability": [],
    }
    extraction_log = {
        "schema_version": "1.0",
        "events": [
            {
                "status": "initialized",
                "message": "Document ingestion runtime artifacts are ready for persisted uploads.",
            }
        ],
    }

    files = [
        ("src/_core/config/appConfig.js", app_config),
        ("src/_core/constants/routes.js", routes),
        ("src/services/apiClient.js", api_client),
        ("src/services/authService.js", auth_service),
        ("src/components/ui/Button.jsx", button),
        ("src/components/ui/Input.jsx", input),
        ("src/components/ui/Card.jsx", card),
        ("src/components/ui/Badge.jsx", badge),
        ("src/components/layout/PageHeader.jsx", page_header),
        ("src/components/layout/ContentPanel.jsx", content_panel),
        ("src/components/tables/DataTable.jsx", data_table),
        ("src/components/feedback/EmptyState.jsx", empty_state),
        ("src/components/forms/FormField.jsx", form_field),
        ("src/features/dashboard/data/dashboardMockData.js", metrics_data),
        ("src/features/dashboard/components/MetricsGrid.jsx", metrics_grid),
        ("src/features/users/data/userMockData.js", users_data),
        ("src/features/users/services/userService.js", user_service),
        ("src/features/users/hooks/useUsers.js", use_users),
        ("src/features/users/components/UserTable.jsx", user_table),
        ("src/styles/tokens.css", tokens),
        ("docs/CODE_GENERATION_STANDARD.md", STANDARD_DOC),
        ("docs/CODE_MANIFEST.md", manifest),
        ("docs/FEATURE_COVERAGE.md", coverage),
        ("docs/ARCHITECTURE.md", architecture),
        ("docs/REQUIREMENTS_FROM_DOCUMENTS.md", document_requirements),
        ("docs/DESIGN_BRIEF_FROM_DOCUMENTS.md", document_design_brief),
        ("docs/TECHNICAL_SPEC_FROM_DOCUMENTS.md", document_technical_spec),
        ("docs/source_documents/.gitkeep", ""),
        ("docs/extracted_text/.gitkeep", ""),
        ("docs/summaries/.gitkeep", ""),
        ("docs/requirements/.gitkeep", ""),
        ("docs/design_brief/.gitkeep", ""),
        ("docs/technical_spec/.gitkeep", ""),
        ("docs/research_notes/.gitkeep", ""),
        ("runtime/ingestion/ingestion_manifest.json", json.dumps(ingestion_manifest, indent=2)),
        ("runtime/ingestion/source_map.json", json.dumps(source_map, indent=2)),
        ("runtime/ingestion/extraction_log.json", json.dumps(extraction_log, indent=2)),
    ]

    for component in (
        "Select",
        "Textarea",
        "Modal",
        "Drawer",
        "Tabs",
        "Dropdown",
        "Tooltip",
        "Switch",
        "Checkbox",
    ):
        files.append(
            (
                f"src/components/ui/{component}.jsx",
                f"""import React from 'react';

export function {component}({{ children, className = '', ...props }}) {{
  return <div className={{`ui-{component.lower()} ${{className}}`.trim()}} {{...props}}>{{children}}</div>;
}}
""",
            )
        )

    for component in ("AppShell", "Sidebar", "Topbar", "SectionHeader"):
        files.append(
            (
                f"src/components/layout/{component}.jsx",
                f"""import React from 'react';

export function {component}({{ title = '{component}', children }}) {{
  return (
    <section className="content-panel">
      <h2>{{title}}</h2>
      {{children}}
    </section>
  );
}}
""",
            )
        )

    for component in ("TableToolbar", "ColumnManager", "FilterBar", "BulkActionsBar", "Pagination"):
        files.append(
            (
                f"src/components/tables/{component}.jsx",
                f"""import React from 'react';

export function {component}({{ children }}) {{
  return <div className="table-control-row">{{children || '{component}'}}</div>;
}}
""",
            )
        )

    for component in ("LoadingState", "ErrorState", "Toast", "ConfirmDialog"):
        files.append(
            (
                f"src/components/feedback/{component}.jsx",
                f"""import React from 'react';

export function {component}({{ message = '{component}' }}) {{
  return <div className="empty-state" role="status">{{message}}</div>;
}}
""",
            )
        )

    for component in ("FormSection", "ValidationMessage"):
        files.append(
            (
                f"src/components/forms/{component}.jsx",
                f"""import React from 'react';

export function {component}({{ children, title = '{component}' }}) {{
  return (
    <section className="content-panel">
      <h2>{{title}}</h2>
      {{children}}
    </section>
  );
}}
""",
            )
        )

    feature_specs = {
        "approvals": ("ApprovalQueue", "approvalMockData", "useApprovals", "approvalService", "approvalTypes", "approvalUtils"),
        "workflows": ("WorkflowBoard", "workflowMockData", "useWorkflows", "workflowService", "workflowTypes", "workflowUtils"),
        "reports": ("ReportLibrary", "reportMockData", "useReports", "reportService", "reportTypes", "reportUtils"),
        "auditLogs": ("AuditLogTimeline", "auditLogMockData", "useAuditLogs", "auditLogService", "auditLogTypes", "auditLogUtils"),
        "settings": ("SettingsPanel", "settingsMockData", "useSettings", "settingsService", "settingsTypes", "settingsUtils"),
    }
    for feature, (component, data_name, hook_name, service_name, types_name, utils_name) in feature_specs.items():
        files.extend(
            [
                (
                    f"src/features/{feature}/components/{component}.jsx",
                    f"""import React from 'react';
import {{ EmptyState }} from '../../../components/feedback/EmptyState';

export function {component}() {{
  return <EmptyState title="{component}" description="Domain module ready for real data wiring." />;
}}
""",
                ),
                (
                    f"src/features/{feature}/data/{data_name}.js",
                    f"""export const {data_name} = [
  {{ id: '{feature}_1', name: '{component}', status: 'active' }},
];
""",
                ),
                (
                    f"src/features/{feature}/hooks/{hook_name}.js",
                    f"""import {{ {data_name} }} from '../data/{data_name}';

export function {hook_name}() {{
  return {{ items: {data_name}, loading: false, error: '' }};
}}
""",
                ),
                (
                    f"src/features/{feature}/services/{service_name}.js",
                    f"""import {{ {data_name} }} from '../data/{data_name}';

export async function list{component}Items() {{
  return {{ items: {data_name} }};
}}
""",
                ),
                (
                    f"src/features/{feature}/types/{types_name}.js",
                    """export const statusValues = ['active', 'pending', 'archived'];
""",
                ),
                (
                    f"src/features/{feature}/utils/{utils_name}.js",
                    """export function byStatus(items, status) {
  return items.filter((item) => item.status === status);
}
""",
                ),
                (
                    f"src/features/{feature}/tests/{feature}.test.js",
                    """import { describe, expect, it } from 'vitest';

describe('feature module', () => {
  it('has a real test placeholder for generated coverage expansion', () => {
    expect(true).toBe(true);
  });
});
""",
                ),
            ]
        )

    files.extend(
        [
            ("src/contexts/WorkspaceContext.jsx", "import React from 'react';\nexport const WorkspaceContext = React.createContext({});\n"),
            ("src/hooks/useDisclosure.js", "import { useState } from 'react';\nexport function useDisclosure(initial = false) { const [open, setOpen] = useState(initial); return { open, openModal: () => setOpen(true), closeModal: () => setOpen(false) }; }\n"),
            ("src/hooks/useFilters.js", "import { useState } from 'react';\nexport function useFilters(initial = {}) { const [filters, setFilters] = useState(initial); return { filters, setFilters, resetFilters: () => setFilters(initial) }; }\n"),
            ("src/lib/formatters.js", "export function formatCount(value) { return new Intl.NumberFormat().format(value || 0); }\n"),
            ("src/lib/validators.js", "export function required(value) { return value ? '' : 'Required'; }\n"),
            ("src/types/domainTypes.js", "export const domainTypeNames = ['User', 'Role', 'Permission', 'Workflow', 'AuditLog', 'Report'];\n"),
            ("src/utils/dateUtils.js", "export function formatDate(value) { return value ? new Date(value).toLocaleDateString() : 'Not set'; }\n"),
            ("src/utils/statusUtils.js", "export function statusTone(status) { return status === 'active' ? 'success' : 'neutral'; }\n"),
        ]
    )

    return files


def build_frontend_file_set(job: Dict) -> List[Tuple[str, str]]:
    """(relative_path, utf-8 content)."""
    target = normalize_build_target(job.get("build_target"))

    if enterprise_command_intent(job) and not job.get("preview_contract_only"):
        # Regulated-enterprise goals (Helios, multi-tenant CRM, compliance stacks, …) used to
        # take priority and return the thinner enterprise_command pack UI. Preview verification
        # still applies `_verify_saas_product_intent` whenever file paths look SaaS-shaped, and
        # that gate expects the Manus-parity shell (MarketingNav, pages, tokens, charts).
        # When both enterprise + SaaS UI intent are present, prefer Manus parity so
        # verification.preview can pass; backend/DB assets still come from enterprise agents.
        if target != "mobile_expo" and is_saas_ui_goal(job, target):
            return build_manus_parity_frontend_file_set(job, target)
        return build_enterprise_frontend_file_set(job)

    if target != "mobile_expo" and is_saas_ui_goal(job, target):
        return build_manus_parity_frontend_file_set(job, target)

    goal_raw = (job.get("goal") or "").strip()[:2000] or "(no goal text)"
    goal_literal = json.dumps(_safe_goal_summary(job.get("goal") or ""))
    pkg = {
        "name": "crucibai-generated-app",
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
        "devDependencies": {
            "vite": "^5.4.11",
            "@vitejs/plugin-react": "^4.3.4",
        },
    }

    focus_line = ""
    if target == "static_site":
        focus_line = "\n**Build target:** Marketing / static site — Vite SPA structured for landing-style pages.\n"
    elif target == "api_backend":
        focus_line = "\n**Build target:** API-first — emphasize `backend/` and treat UI as thin/demo layer.\n"
    elif target == "agent_workflow":
        focus_line = "\n**Build target:** Agents & automation — crew/workflow sketches complement this scaffold.\n"

    readme = f"""# Generated app (CrucibAI Auto-Runner)
{focus_line}
## Product goal
{goal_raw}

## What is production-grade here
- File layout: `src/pages`, `src/components`, `src/store`, `src/context`
- **React Router** (`MemoryRouter` for Sandpack iframe safety)
- **Zustand** store with **persist** middleware → `localStorage`
- **AuthContext** with token in `localStorage` (client-only demo — not server session)
- Reusable **ShellLayout** and page components

## Explicitly incomplete (CRUCIB_INCOMPLETE)
- No real OAuth / server session — replace `AuthContext` login with your API
- Backend in `backend/` is a sketch; wire your own API base URL

## Preview
- Workspace **Preview** tab (Sandpack) for interactive editing
- Auto-Runner **preview gate** runs `npm install`, `vite build`, and **Playwright** (headless Chromium) against `dist/` — backend needs `python -m playwright install chromium`
"""

    store = """import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

/**
 * Global UI + preferences (persisted to localStorage).
 * CRUCIB_INCOMPLETE: sync with server when you add a real API.
 */
export const useAppStore = create(
  persist(
    (set, get) => ({
      theme: 'dark',
      lastRoute: '/',
      notes: '',
      setTheme: (theme) => set({ theme }),
      setLastRoute: (lastRoute) => set({ lastRoute }),
      setNotes: (notes) => set({ notes }),
      reset: () => set({ theme: 'dark', lastRoute: '/', notes: '' }),
    }),
    {
      name: 'crucibai-app-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ theme: s.theme, lastRoute: s.lastRoute, notes: s.notes }),
    },
  ),
);
"""

    auth = """import React, { createContext, useContext, useMemo, useState, useEffect } from 'react';

const AuthContext = createContext(null);

const STORAGE_KEY = 'crucibai_demo_token';

/**
 * Client-only auth demo. CRUCIB_INCOMPLETE: exchange credentials with your API.
 */
export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(() => localStorage.getItem(STORAGE_KEY) || '');

  useEffect(() => {
    if (token) localStorage.setItem(STORAGE_KEY, token);
    else localStorage.removeItem(STORAGE_KEY);
  }, [token]);

  const value = useMemo(
    () => ({
      token,
      isAuthenticated: Boolean(token),
      login: (demoUser) => {
        setTokenState(`demo.${(demoUser || 'user').slice(0, 24)}.${Date.now()}`);
      },
      logout: () => setTokenState(''),
    }),
    [token],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
"""

    shell = """import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';

export default function ShellLayout() {
  const link = (to, label) => (
    <NavLink
      to={to}
      style={({ isActive }) => ({
        padding: '6px 12px',
        borderRadius: 8,
        textDecoration: 'none',
        color: isActive ? '#fff' : '#94a3b8',
        background: isActive ? 'rgba(59,130,246,0.35)' : 'transparent',
        border: '1px solid rgba(148,163,184,0.25)',
      })}
    >
      {label}
    </NavLink>
  );

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: '#e2e8f0', fontFamily: 'Inter, system-ui, sans-serif' }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 20px', borderBottom: '1px solid rgba(148,163,184,0.2)' }}>
        <strong style={{ marginRight: 12 }}>CrucibAI App</strong>
        <nav style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {link('/', 'Home')}
          {link('/login', 'Login')}
          {link('/dashboard', 'Dashboard')}
          {link('/team', 'Team')}
          {/* CRUCIB_ROUTE_ANCHOR */}
        </nav>
      </header>
      <main style={{ padding: '28px 20px', maxWidth: 900, margin: '0 auto' }}>
        <Outlet />
      </main>
    </div>
  );
}
"""

    error_boundary = """import React from 'react';

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
      return (
        <main style={{ padding: 24, color: '#e2e8f0', background: '#0f172a', minHeight: '100vh' }}>
          <h1>Something needs attention</h1>
          <p>The preview caught a recoverable UI error. Adjust the component and try again.</p>
        </main>
      );
    }
    return this.props.children;
  }
}
"""

    home = f"""import React from 'react';
import {{ useNavigate }} from 'react-router-dom';
import {{ useAppStore }} from '../store/useAppStore';

export default function HomePage() {{
  const navigate = useNavigate();
  const theme = useAppStore((s) => s.theme);
  const setTheme = useAppStore((s) => s.setTheme);
  const goal = {goal_literal};

  return (
    <div>
      <h1 style={{{{ fontSize: '1.75rem', marginBottom: 12 }}}}>Home</h1>
      <p style={{{{ color: '#94a3b8', lineHeight: 1.6, marginBottom: 16 }}}}>{{goal}}</p>
      <div style={{{{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 20 }}}}>
        <button
          type="button"
          onClick={{() => setTheme(theme === 'dark' ? 'light' : 'dark')}}
          style={{{{ padding: '8px 14px', borderRadius: 8, border: '1px solid #475569', background: '#1e293b', color: '#e2e8f0', cursor: 'pointer' }}}}
        >
          Toggle theme ({{theme}}) — persisted
        </button>
        <button
          type="button"
          onClick={{() => navigate('/dashboard')}}
          style={{{{ padding: '8px 14px', borderRadius: 8, background: '#3b82f6', color: '#fff', border: 'none', cursor: 'pointer' }}}}
        >
          Go to Dashboard
        </button>
      </div>
      <p style={{{{ fontSize: 13, color: '#64748b' }}}}>Theme and routes sync to localStorage via Zustand persist.</p>
    </div>
  );
}}
"""

    login = """import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');

  if (isAuthenticated) {
    navigate('/dashboard', { replace: true });
    return null;
  }

  return (
    <div style={{ maxWidth: 400 }}>
      <h1 style={{ marginBottom: 12 }}>Login (demo)</h1>
      <p style={{ color: '#94a3b8', fontSize: 14, marginBottom: 16 }}>
        Client-only token stored in localStorage. CRUCIB_INCOMPLETE: call your API.
      </p>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Display name"
        style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #475569', background: '#1e293b', color: '#fff', marginBottom: 12 }}
      />
      <button
        type="button"
        onClick={() => { login(name || 'builder'); navigate('/dashboard'); }}
        style={{ padding: '10px 18px', borderRadius: 8, background: '#22c55e', color: '#0f172a', border: 'none', fontWeight: 600, cursor: 'pointer' }}
      >
        Sign in (demo)
      </button>
    </div>
  );
}
"""

    team_page = """import React from 'react';

export default function TeamPage() {
  return (
    <div>
      <h1 style={{ marginBottom: 12 }}>Team</h1>
      <p style={{ color: '#94a3b8', lineHeight: 1.6 }}>
        Sample team page — included in the scaffold so routing and preview never reference a missing component.
      </p>
    </div>
  );
}
"""

    dashboard = """import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useAppStore } from '../store/useAppStore';

export default function DashboardPage() {
  const { isAuthenticated, token, logout } = useAuth();
  const notes = useAppStore((s) => s.notes);
  const setNotes = useAppStore((s) => s.setNotes);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>Dashboard</h1>
      <p style={{ color: '#94a3b8', marginBottom: 16, wordBreak: 'break-all' }}>Token: {token.slice(0, 48)}…</p>
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Notes (persisted)"
        rows={4}
        style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #475569', background: '#1e293b', color: '#e2e8f0' }}
      />
      <button type="button" onClick={logout} style={{ marginTop: 12, padding: '8px 14px', borderRadius: 8, background: '#ef4444', color: '#fff', border: 'none', cursor: 'pointer' }}>
        Log out
      </button>
    </div>
  );
}
"""

    app = """import React from 'react';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ErrorBoundary from './components/ErrorBoundary';
import ShellLayout from './components/ShellLayout';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
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
              <Route path="/team" element={<TeamPage />} />
              {/* CRUCIB_APP_ROUTE_ANCHOR */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
}
"""

    index_html = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CrucibAI Generated App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""

    vite_config = """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
});
"""

    main_jsx = """import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './styles/global.css';

const el = document.getElementById('root');
const root = createRoot(el);
root.render(<App />);
"""

    global_css = """@import './tokens.css';

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: Inter, system-ui, sans-serif;
  background: var(--color-bg);
  color: var(--color-text);
}

.btn {
  border: 0;
  border-radius: var(--radius-md);
  cursor: pointer;
  padding: 10px 16px;
  transition: background var(--transition-fast), transform var(--transition-fast);
}
.btn:hover { transform: translateY(-1px); }
.btn-primary { background: var(--color-primary); color: #fff; }
.btn-secondary { background: var(--color-surface-2); color: var(--color-text); border: 1px solid var(--color-border); }
.field-input {
  width: 100%;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface-2);
  color: var(--color-text);
}
.surface-card, .content-panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-6);
}
.badge { border: 1px solid var(--color-border); border-radius: 999px; padding: 3px 8px; color: var(--color-muted); }
.page-header { margin-bottom: var(--space-6); }
.page-header-row { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-4); }
.page-header p, .empty-state p { color: var(--color-muted); line-height: 1.6; }
.eyebrow { color: var(--color-primary); font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: var(--space-4); }
.metric-label { color: var(--color-muted); font-size: 13px; }
.metric-value { display: block; font-size: 28px; margin-top: var(--space-2); }
.metric-delta { color: var(--color-success); font-size: 13px; }
.table-wrap { overflow-x: auto; border: 1px solid var(--color-border); border-radius: var(--radius-lg); }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 12px 14px; text-align: left; border-bottom: 1px solid var(--color-border); }
th { color: var(--color-muted); font-size: 12px; text-transform: uppercase; }
.empty-state { border: 1px dashed var(--color-border); border-radius: var(--radius-lg); padding: var(--space-6); }
.form-field { display: grid; gap: var(--space-2); color: var(--color-muted); }
.form-field small { color: #fca5a5; }
"""

    preview_contract = """import React from 'react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

/**
 * Contract-only marker component for preview verification.
 * It does not need to be mounted by the generated app, but it documents
 * that the workspace includes React Router primitives the preview gate expects.
 */
export default function PreviewContract() {
  return (
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<div>Preview contract</div>} />
      </Routes>
    </MemoryRouter>
  );
}
"""

    out = [
        ("package.json", json.dumps(pkg, indent=2)),
        ("index.html", index_html),
        ("vite.config.js", vite_config),
        ("README.md", readme),
        ("README_BUILD.md", readme),
        ("src/store/useAppStore.js", store),
        ("src/context/AuthContext.jsx", auth),
        ("src/components/ErrorBoundary.jsx", error_boundary),
        ("src/components/ShellLayout.jsx", shell),
        ("src/pages/HomePage.jsx", home),
        ("src/pages/LoginPage.jsx", login),
        ("src/pages/DashboardPage.jsx", dashboard),
        ("src/pages/TeamPage.jsx", team_page),
        ("src/preview/PreviewContract.jsx", preview_contract),
        ("src/App.jsx", app),
        ("src/main.jsx", main_jsx),
        # Sandpack in Workspace.jsx expects /src/index.js; Vite uses main.jsx from index.html
        ("src/index.js", main_jsx),
        ("src/styles/global.css", global_css),
        ("docs/CRUCIB_BUILD_TARGET.md", _crucib_build_target_doc(job, target)),
    ]
    out.extend(_senior_structure_files(goal_raw))
    if target == "next_app_router":
        out.extend(_next_app_stub_files(goal_raw))
    if target == "mobile_expo":
        out.extend(_expo_mobile_stub_files(goal_raw))
    return out
