# CrucibAI – List of All Features, Forms, and Functionality

**Purpose:** Single reference for every feature, form, and piece of functionality in the app, with connection status (frontend ↔ backend).

**Last updated:** February 2026

**Connection status:** All listed routes have a frontend caller or proof script; see COMPLIANCE_MATRIX.md for verification.

---

## 1. Frontend pages and routes

| Route | Page / component | Auth | Description |
|-------|-------------------|------|-------------|
| `/` | LandingPage | No | Landing, hero, live examples, try chat/voice |
| `/auth` | AuthPage | No | Login, register, MFA verify |
| `/builder` | Builder | No | Simple builder (chat → code) |
| `/workspace` | Workspace | Yes | Main workspace: prompt, build, tools, export, agents |
| `/share/:token` | ShareView | No | Public read-only view of shared project |
| `/privacy` | Privacy | No | Privacy policy |
| `/terms` | Terms | No | Terms of use |
| `/aup` | Aup | No | Acceptable use policy |
| `/dmca` | Dmca | No | DMCA policy |
| `/cookies` | Cookies | No | Cookie policy |
| `/about` | About | No | About page |
| `/pricing` | Pricing | No | Public pricing, bundles, Enterprise link |
| `/enterprise` | Enterprise | No | Enterprise contact form |
| `/features` | Features | No | Product features |
| `/templates` | TemplatesPublic | No | Public templates gallery |
| `/patterns` | PatternsPublic | No | Public patterns |
| `/learn` | LearnPublic | No | Public learn/docs |
| `/shortcuts` | ShortcutsPublic | No | Public shortcuts |
| `/prompts` | PromptsPublic | No | Public prompts |
| `/benchmarks` | Benchmarks | No | Benchmarks page |
| `/app` | Layout (shell) | Yes | App shell with sidebar |
| `/app` (index) | Dashboard | Yes | Dashboard: stats, project cards, Share/Duplicate/Template |
| `/app/builder` | Builder | Yes | Builder inside app |
| `/app/workspace` | Workspace | Yes | Workspace inside app |
| `/app/projects/new` | ProjectBuilder | Yes | Create new project (name, description, type, requirements) |
| `/app/projects/:id` | AgentMonitor | Yes | Project detail: status, phases, logs, retry phase |
| `/app/tokens` | TokenCenter | Yes | Bundles, history, usage, purchase |
| `/app/exports` | ExportCenter | Yes | List exports, create export |
| `/app/patterns` | PatternLibrary | Yes | Pattern library |
| `/app/templates` | TemplatesGallery | Yes | Templates gallery (from template) |
| `/app/prompts` | PromptLibrary | Yes | Templates, recent, saved, save new |
| `/app/learn` | LearnPanel | Yes | Learn content |
| `/app/env` | EnvPanel | Yes | Workspace env vars (GET/POST) |
| `/app/shortcuts` | ShortcutCheatsheet | Yes | Shortcuts reference |
| `/app/payments-wizard` | PaymentsWizard | Yes | Stripe checkout flow, inject Stripe |
| `/app/examples` | ExamplesGallery | Yes | Live examples, fork |
| `/app/generate` | GenerateContent | Yes | Generate docs/slides/sheets |
| `/app/settings` | Settings | Yes | API & Environment, MFA, deploy tokens |
| `/app/audit-log` | AuditLog | Yes | User audit logs, export |
| `/app/admin` | AdminDashboard | Yes (admin) | Admin overview |
| `/app/admin/users` | AdminUsers | Yes (admin) | User list |
| `/app/admin/users/:id` | AdminUserProfile | Yes (admin) | User profile, grant credits, suspend, downgrade |
| `/app/admin/billing` | AdminBilling | Yes (admin) | Billing transactions |
| `/app/admin/analytics` | AdminAnalytics | Yes (admin) | Analytics daily/weekly/report |
| `/app/admin/legal` | AdminLegal | Yes (admin) | Blocked requests, review |

---

## 2. Forms (user input → backend)

| Form | Location | Backend endpoint(s) | Purpose |
|------|----------|--------------------|---------|
| **Login** | AuthPage | POST `/auth/login` | Email + password; may return MFA required |
| **Register** | AuthPage | POST `/auth/register` | Email, password, name; optional referral |
| **MFA verify** | AuthPage | POST `/auth/verify-mfa` | Code + mfa_token |
| **MFA setup** | Settings | POST `/mfa/setup` | Init MFA; returns QR/secret |
| **MFA verify (setup)** | Settings | POST `/mfa/verify` | Token to enable MFA |
| **MFA disable** | Settings | POST `/mfa/disable` | Password to disable MFA |
| **Workspace env** | Settings (API tab), EnvPanel | GET/POST `/workspace/env` | API keys and env key/value |
| **Deploy tokens** | Settings | GET `/users/me/deploy-tokens`, PATCH `/users/me/deploy-tokens` | Vercel/Netlify tokens |
| **Create project** | ProjectBuilder | POST `/projects` | Name, description, project_type, requirements |
| **Build plan** | Workspace | POST `/build/plan` | Prompt, swarm flag |
| **Chat** | Workspace, LandingPage, Builder | POST `/ai/chat`, POST `/ai/chat/stream` | Message, model, mode |
| **Voice input** | Workspace, LandingPage | POST `/voice/transcribe` | Audio file (multipart) |
| **Image to code** | Workspace | POST `/ai/image-to-code` | Image file + optional prompt |
| **Enterprise contact** | Enterprise | POST `/enterprise/contact` | Company, email, team_size, use_case, budget, message |
| **Token purchase** | TokenCenter, PaymentsWizard | POST `/tokens/purchase` (bundle), POST `/stripe/create-checkout-session` | Bundle key; Stripe session |
| **Create export** | ExportCenter | POST `/exports` | Export config |
| **Save prompt** | PromptLibrary | POST `/prompts/save` | Save new prompt |
| **Share create** | Dashboard | POST `/share/create` | project_id, read_only |
| **Duplicate project** | Dashboard | POST `/projects/:id/duplicate` | — |
| **Save as template** | Dashboard | POST `/projects/:id/save-as-template` | name |
| **From template** | TemplatesGallery | POST `/projects/from-template` | template selection |
| **Retry phase** | AgentMonitor | POST `/projects/:id/retry-phase` | Retry failed phase |
| **Deploy Vercel/Netlify** | DeployButton / project | POST `/projects/:id/deploy/vercel`, POST `/projects/:id/deploy/netlify` | One-click deploy |
| **Admin: grant credits** | AdminUserProfile | POST `/admin/users/:id/grant-credits` | Credits amount |
| **Admin: suspend** | AdminUserProfile | POST `/admin/users/:id/suspend` | — |
| **Admin: downgrade** | AdminUserProfile | POST `/admin/users/:id/downgrade` | — |
| **Admin: legal review** | AdminLegal | POST `/admin/legal/review/:request_id` | action (approve/block) |

---

## 3. Backend API routes (full list) × caller

*All under `/api` prefix. Status: ✅ = has frontend or proof caller.*

| Method | Route | Caller | Status |
|--------|--------|--------|--------|
| GET | `/` | proof_full_routes, health | ✅ |
| GET | `/health` | Layout (frontend health check) | ✅ |
| POST | `/ai/chat` | Workspace, LandingPage, Builder | ✅ |
| GET | `/ai/chat/history/{session_id}` | Workspace | ✅ |
| POST | `/ai/chat/stream` | Workspace | ✅ |
| POST | `/ai/analyze` | Workspace (Tools → Analyze) | ✅ |
| POST | `/generate/doc` | GenerateContent (docs) | ✅ |
| POST | `/generate/slides` | GenerateContent (slides) | ✅ |
| POST | `/generate/sheets` | GenerateContent (sheets) | ✅ |
| POST | `/rag/query` | proof_full_routes | ✅ |
| POST | `/search` | proof_full_routes | ✅ |
| POST | `/voice/transcribe` | Workspace, LandingPage | ✅ |
| POST | `/files/analyze` | Workspace (Tools → Analyze files) | ✅ |
| POST | `/ai/image-to-code` | Workspace | ✅ |
| POST | `/ai/validate-and-fix` | Workspace (Tools) | ✅ |
| POST | `/export/zip` | Workspace (Export menu) | ✅ |
| POST | `/export/github` | Workspace (Export → GitHub) | ✅ |
| POST | `/export/deploy` | Workspace (Export → Deploy) | ✅ |
| POST | `/stripe/create-checkout-session` | TokenCenter, PaymentsWizard | ✅ |
| POST | `/stripe/webhook` | Stripe (server-to-server) | ✅ |
| POST | `/enterprise/contact` | Enterprise | ✅ |
| POST | `/auth/register` | AuthPage (via App) | ✅ |
| POST | `/auth/login` | AuthPage (via App) | ✅ |
| POST | `/auth/verify-mfa` | AuthPage (via App) | ✅ |
| GET | `/auth/me` | App.js (auth check, refresh) | ✅ |
| GET | `/auth/google` | OAuth redirect | ✅ |
| GET | `/auth/google/callback` | OAuth callback | ✅ |
| POST | `/mfa/setup` | Settings | ✅ |
| POST | `/mfa/verify` | Settings | ✅ |
| POST | `/mfa/disable` | Settings | ✅ |
| GET | `/mfa/status` | Settings | ✅ |
| POST | `/mfa/backup-code/use` | Auth flow | ✅ |
| GET | `/audit/logs` | AuditLog | ✅ |
| GET | `/audit/logs/export` | AuditLog | ✅ |
| GET | `/tokens/bundles` | TokenCenter, Pricing | ✅ |
| POST | `/tokens/purchase` | TokenCenter | ✅ |
| GET | `/tokens/history` | TokenCenter | ✅ |
| GET | `/tokens/usage` | TokenCenter | ✅ |
| GET | `/referrals/code` | (future UI) | ✅ proof |
| GET | `/referrals/stats` | (future UI) | ✅ proof |
| GET | `/agents` | proof_agents, AgentMonitor catalog | ✅ |
| GET | `/agents/status/{project_id}` | AgentMonitor | ✅ |
| GET | `/agents/activity` | Workspace (Agents panel) | ✅ |
| POST | `/agents/run/planner` … `generic` | Orchestration, proof_agents | ✅ |
| GET | `/agents/run/memory-list` | proof | ✅ |
| GET | `/agents/run/automation-list` | proof | ✅ |
| POST | `/projects` | ProjectBuilder | ✅ |
| GET | `/projects` | Dashboard, ExportCenter, AgentMonitor | ✅ |
| GET | `/projects/{project_id}` | AgentMonitor, BuildProgress | ✅ |
| GET | `/projects/{project_id}/deploy/zip` | DeployButton | ✅ |
| GET | `/projects/{project_id}/export/deploy` | DeployButton | ✅ |
| GET | `/users/me/deploy-tokens` | Settings | ✅ |
| PATCH | `/users/me/deploy-tokens` | Settings | ✅ |
| POST | `/projects/{project_id}/deploy/vercel` | DeployButton | ✅ |
| POST | `/projects/{project_id}/deploy/netlify` | DeployButton | ✅ |
| POST | `/projects/{project_id}/retry-phase` | AgentMonitor | ✅ |
| GET | `/projects/{project_id}/logs` | AgentMonitor | ✅ |
| GET | `/projects/{project_id}/phases` | AgentMonitor | ✅ |
| POST | `/projects/{project_id}/duplicate` | Dashboard | ✅ |
| POST | `/projects/{project_id}/save-as-template` | Dashboard | ✅ |
| GET | `/build/phases` | Workspace | ✅ |
| POST | `/build/plan` | Workspace | ✅ |
| POST | `/build/from-reference` | proof_full_routes | ✅ |
| GET | `/exports` | ExportCenter | ✅ |
| POST | `/exports` | ExportCenter | ✅ |
| GET | `/examples` | LandingPage (live examples) | ✅ |
| GET | `/examples/{name}` | ExamplesGallery | ✅ |
| POST | `/examples/{name}/fork` | ExamplesGallery | ✅ |
| GET | `/patterns` | PatternLibrary | ✅ |
| GET | `/dashboard/stats` | Dashboard | ✅ |
| GET | `/prompts/templates` | PromptLibrary | ✅ |
| GET | `/prompts/recent` | PromptLibrary | ✅ |
| GET | `/prompts/saved` | PromptLibrary | ✅ |
| POST | `/prompts/save` | PromptLibrary | ✅ |
| GET | `/workspace/env` | EnvPanel, Settings | ✅ |
| POST | `/workspace/env` | EnvPanel, Settings | ✅ |
| POST | `/share/create` | Dashboard | ✅ |
| GET | `/share/{token}` | ShareView | ✅ |
| GET | `/templates` | TemplatesGallery | ✅ |
| POST | `/projects/from-template` | TemplatesGallery | ✅ |
| POST | `/ai/explain-error` | Workspace (Tools) | ✅ |
| POST | `/ai/suggest-next` | Workspace (Tools) | ✅ |
| POST | `/ai/inject-stripe` | PaymentsWizard | ✅ |
| POST | `/ai/security-scan` | Workspace (Tools) | ✅ |
| POST | `/ai/optimize` | Workspace (Tools) | ✅ |
| POST | `/ai/accessibility-check` | Workspace (Tools) | ✅ |
| POST | `/ai/design-from-url` | Workspace (Tools) | ✅ |
| POST | `/ai/quality-gate` | Workspace (quality gate on code) | ✅ |
| POST | `/ai/generate-readme` | (proof / future UI) | ✅ proof |
| POST | `/ai/generate-docs` | (proof / future UI) | ✅ proof |
| POST | `/ai/generate-faq-schema` | (proof / future UI) | ✅ proof |
| GET | `/admin/dashboard` | AdminDashboard | ✅ |
| GET | `/admin/analytics/overview` | Admin | ✅ |
| GET | `/admin/analytics/daily` | AdminAnalytics | ✅ |
| GET | `/admin/analytics/weekly` | AdminAnalytics | ✅ |
| GET | `/admin/analytics/report` | AdminAnalytics | ✅ |
| GET | `/admin/users` | AdminUsers | ✅ |
| GET | `/admin/users/{user_id}` | AdminUserProfile | ✅ |
| POST | `/admin/users/{user_id}/grant-credits` | AdminUserProfile | ✅ |
| POST | `/admin/users/{user_id}/suspend` | AdminUserProfile | ✅ |
| POST | `/admin/users/{user_id}/downgrade` | AdminUserProfile | ✅ |
| GET | `/admin/users/{user_id}/export` | Admin | ✅ |
| GET | `/admin/billing/transactions` | AdminBilling | ✅ |
| GET | `/admin/fraud/flags` | Admin | ✅ |
| GET | `/admin/legal/blocked-requests` | AdminLegal | ✅ |
| POST | `/admin/legal/review/{request_id}` | AdminLegal | ✅ |
| GET | `/admin/referrals/links` | Admin | ✅ |
| GET | `/admin/referrals/leaderboard` | Admin | ✅ |
| GET | `/admin/segments` | Admin | ✅ |

---

## 4. Features and functionality (by area)

### Auth & account
- Register (email, password, name, optional referral)
- Login (email, password)
- MFA: setup (QR/secret), verify, disable, backup code
- Google OAuth (optional)
- Logout, refresh user, login with token (share links)

### Workspace & build
- Text prompt → plan → build (streaming or single response)
- Swarm mode (plan + suggestions in parallel)
- Model selector (auto, GPT-4o, Claude)
- Chat history per session
- Voice input (transcribe → text)
- Image attach → image-to-code
- Design from URL (screenshot → code)
- Quality gate (validate/lint) on code (POST `/ai/quality-gate`)
- Build phases visible; per-step tokens in AgentMonitor

### Tools (Workspace)
- Validate & fix code
- Security scan
- Accessibility check
- Optimize code
- Explain error
- Suggest next steps
- Analyze code
- Analyze files (upload)
- Design from URL

### Export & deploy
- Download ZIP
- Export to GitHub
- Export Deploy (ZIP)
- One-click deploy: Vercel, Netlify (via DeployButton; uses deploy tokens from Settings)
- Project deploy ZIP / export deploy (GET) for DeployButton

### Projects
- Create project (name, description, type, requirements)
- List projects (Dashboard, ExportCenter)
- Get project (AgentMonitor, BuildProgress)
- Duplicate project
- Save as template
- Create from template
- Project phases, logs, retry phase
- Share (create link, view read-only ShareView)

### Agents & orchestration
- 100 agents in DAG; run via build/plan and orchestration
- Build phases API; project phases API
- Agent status per project; agent activity (recent)
- AgentMonitor: status, phases, logs, retry phase, per-agent tokens

### Tokens & billing
- Token bundles (list)
- Token purchase (bundle key)
- Token history
- Token usage (current user)
- Stripe checkout session creation
- Stripe webhook (server)

### Settings & env
- Workspace env GET/POST (API keys, env vars)
- Deploy tokens (Vercel, Netlify) GET/PATCH
- MFA setup/verify/disable/status

### Prompt library
- Templates (GET)
- Recent (GET)
- Saved (GET)
- Save (POST)

### Patterns & templates
- Patterns list (PatternLibrary)
- Templates list (TemplatesGallery)
- From template (create project)
- Save as template (from project)

### Examples
- List examples (landing: live examples; app: ExamplesGallery)
- Get example by name
- Fork example

### Generate (docs/slides/sheets)
- Generate doc (POST generate/doc)
- Generate slides (POST generate/slides)
- Generate sheets (POST generate/sheets)
- GenerateContent page uses these

### Admin (admin_role only)
- Dashboard (overview)
- Analytics: overview, daily, weekly, report
- Users: list, get user, grant credits, suspend, downgrade, export
- Billing: transactions
- Fraud flags
- Legal: blocked requests, review (approve/block)
- Referrals: links, leaderboard
- Segments

### Legal & public
- Privacy, Terms, AUP, DMCA, Cookies, About
- Pricing (public), Enterprise (contact form)
- Features, Templates/Patterns/Learn/Shortcuts/Prompts/Benchmarks (public)
- Audit log (user’s own logs, export)

### Other
- Health check (backend; frontend Layout pings)
- Audit logs (user), audit logs export
- RAG query, search (backend; proof)
- AI generate-readme, generate-docs, generate-faq-schema (backend; proof or future UI)

---

## 5. Connection and verification

- **Backend ↔ frontend:** Every route in Section 3 has a caller (page or proof script). See COMPLIANCE_MATRIX.md for the same mapping and proof commands.
- **Run proof:**  
  `cd backend` → `python proof_full_routes.py` (server running)  
  `cd backend` → `python proof_agents.py`
- **Run tests:**  
  `.\run-all-tests.ps1` (root) or backend pytest + frontend Jest.

**Everything listed above is implemented and connected; proofs and tests confirm behavior.**
