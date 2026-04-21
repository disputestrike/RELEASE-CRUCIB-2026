# CrucibAI — End-to-End Coherence Report
Generated: 2026-04-21T10:41:50Z
HEAD: feb3f82 mount(W3+W5): wire public_benchmarks, changelog, marketplace, api_keys routers

## 1. App is ONE system — connectivity verdict: PASS

| Layer | Count | Status |
|---|---:|---|
| Python backend LoC (non-test) | 71,661 | ✓ |
| JS/TS frontend LoC | 47,484 | ✓ |
| Routers loaded by server.py | 0/0 | ✓ |
| FastAPI routes mounted | 297 | ✓ |
| Frontend pages | 77 | ✓ |
| Frontend components | 162 | ✓ |
| React Router routes | 86 | ✓ |
| UI → backend endpoints referenced | 35 | ✓ |
| UI endpoints with orphaned backend | **0** | ✓ |
| Test collection | ========================= 527 tests collected in 3.02s ========================= | ✓ |

## 2. Live endpoint probes (via in-process TestClient)
- `/healthz` → **200**
- `/api/benchmarks/scorecards` → **200**
- `/api/benchmarks/competitors` → **200**
- `/public/benchmarks/scorecard` → **200**
- `/api/changelog` → **200**
- `/api/marketplace/listings` → **200**
- `/api/marketplace/featured` → **200**
- `/api/community/publications` → **200**
- `/api/mobile/presets` → **200**
- `/api/runs/preview-loop/capabilities` → **200**


## 3. Canonical page reachability
Every page the user can navigate to resolves against the router:

| Path | Page | Reachable |
|---|---|---|
| `/` | LandingPage | ✓ |
| `/auth` | AuthPage | ✓ |
| `/onboarding` | OnboardingPage | ✓ |
| `/app/workspace` | WorkspaceV3Shell (canonical) | ✓ |
| `/app/settings` | Settings (with 16-lang dropdown) | ✓ |
| `/app/admin` | AdminDashboard | ✓ |
| `/app/marketplace` | **Marketplace (W5 new)** | ✓ |
| `/app/developer` | **DeveloperPortal (W5 new)** | ✓ |
| `/app/templates-gallery` | **TemplateGallery (W5 new)** | ✓ |
| `/benchmarks/public` | **BenchmarksPublic (W3 new)** | ✓ |
| `/changelog/live` | **ChangelogLive (W3 new)** | ✓ |
