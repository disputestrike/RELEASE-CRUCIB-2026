# CrucibAI – Integration Audit & QC Report

**Date:** February 9, 2026  
**Scope:** Approved items integrated into existing codebase (model fallbacks, phases API, validate-and-fix, Stripe for us + in-app, real-time phase UI, command palette, paywall).  
**Status:** Implemented; ready for run-local and manual QA.

---

## 1. What Was Integrated

### Backend (`backend/server.py`)

| Feature | Implementation | Proof |
|--------|----------------|-------|
| **Model fallback on failure** | `MODEL_FALLBACK_CHAINS`, `MODEL_CHAINS`, `_get_model_chain()`, `_call_llm_with_fallback()`. `/api/ai/chat` and `/api/ai/chat/stream` use fallback: try primary model, on exception try next in chain. | Lines ~118–140 (chains), ~248–268 (helper), ~271–308 (chat), ~328–370 (stream). |
| **Project / build phases API** | `BUILD_PHASES` (Planning, Generating, Validating, Deployment). `GET /api/build/phases` returns phase list. `GET /api/projects/{id}/phases` returns current phase + per-phase status from `agent_status`. | Lines ~844–888. |
| **Validate-and-fix** | `POST /api/ai/validate-and-fix` (body: `code`, optional `language`). Step 1: LLM validates; if “no issues” return as-is. Step 2: else LLM fixes, returns `fixed_code`, `issues_found`, `valid`. Uses same fallback chain. | Lines ~597–635. |
| **Stripe (pay us)** | `POST /api/stripe/create-checkout-session` (body: `bundle`). Creates Stripe Checkout Session, returns `url`. `POST /api/stripe/webhook` verifies signature, on `checkout.session.completed` adds tokens to user and writes to `token_ledger`. Env: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `FRONTEND_URL`. | Lines ~719–795. |
| **Stripe in generated apps** | Not a backend endpoint: frontend detects “payment|stripe|subscription|checkout” in user prompt and appends instruction to include Stripe Checkout in generated code. | See Workspace.jsx `messageContent` + `wantsPayments`. |

### Frontend

| Feature | Implementation | Proof |
|--------|----------------|-------|
| **Real-time phase UI** | Workspace fetches `GET /api/build/phases` on mount. During build, `currentPhase` is set (Planning → Generating → Validating → Deployment). Progress bar shows phase label above it. | Workspace.jsx: `buildPhases`, `currentPhase`, agent loop sets phase, UI shows phase label. |
| **Command palette** | Ctrl+K / Cmd+K toggles palette. Commands: Deploy, Export, Push to GitHub, Auto-fix (if `lastError`), Token Center, Settings. Escape closes. | Workspace.jsx: `commandPaletteOpen`, `useEffect` keydown, modal with `runCommand()`. |
| **Paywall banner** | When `user.token_balance === 0` or `< 10000`, banner at top: “Out of tokens” / “Running low” + “Buy tokens” → `/app/tokens`. | Workspace.jsx: conditional banner above header. |
| **Stripe checkout in Token Center** | Each bundle has “Add tokens” (existing) and “Pay with Stripe”. “Pay with Stripe” calls `POST /api/stripe/create-checkout-session` and redirects to `session.url`. | TokenCenter.jsx: `handleStripeCheckout`, second button per bundle. |

---

## 2. Files Touched

- `backend/server.py` – Model chains, fallback helper, chat/stream use fallback; BUILD_PHASES, GET build/phases, GET projects/:id/phases; validate-and-fix; Stripe create-checkout + webhook; Request import.
- `frontend/src/pages/Workspace.jsx` – Phases state and fetch; currentPhase during build; Stripe-in-app prompt; command palette (state, keydown, modal, runCommand); paywall banner; Settings icon import.
- `frontend/src/pages/TokenCenter.jsx` – handleStripeCheckout; “Pay with Stripe” button per bundle.
- `backend/tests/test_crucibai_api.py` – TestBuildPhasesAndValidate (build/phases, validate-and-fix), TestStripeEndpoints (auth required, invalid bundle).

---

## 3. QC Checklist (Manual)

Run backend and frontend locally, then:

- [ ] **Health:** `GET /api/health` → 200, `status: healthy`.
- [ ] **Build phases:** `GET /api/build/phases` → 200, `phases` array with `id`, `name`, `agents`.
- [ ] **AI chat fallback:** Turn off primary provider or force error; confirm second model is tried (check logs).
- [ ] **Validate-and-fix:** `POST /api/ai/validate-and-fix` with `{"code": "const x = }"}` → 200, `fixed_code` and `valid: false` (or valid after fix).
- [ ] **Stripe (no keys):** `POST /api/stripe/create-checkout-session` without auth → 401; with auth and no `STRIPE_SECRET_KEY` → 503.
- [ ] **Workspace:** Open `/workspace`, start a build → phase label appears (Planning, then Generating, etc.).
- [ ] **Command palette:** Ctrl+K (or Cmd+K) → palette opens; click Deploy → deploy ZIP downloads; Escape closes.
- [ ] **Paywall:** As logged-in user with balance 0 or &lt; 10k, open Workspace → banner “Out of tokens” / “Running low” with “Buy tokens”.
- [ ] **Token Center:** “Add tokens” and “Pay with Stripe” both present; “Pay with Stripe” with Stripe configured redirects to Stripe Checkout.
- [ ] **Stripe in app:** In Workspace, prompt “Build a subscription SaaS with Stripe” → build; generated code should mention Stripe/checkout.

---

## 4. Environment

**Backend (optional for full behavior):**

- `MONGO_URL`, `DB_NAME` – required for app.
- `OPENAI_API_KEY` or `LLM_API_KEY` – for AI and validate-and-fix.
- `STRIPE_SECRET_KEY` – for Stripe Checkout; if missing, create-checkout returns 503.
- `STRIPE_WEBHOOK_SECRET` – for webhook signature verification.
- `FRONTEND_URL` – success/cancel redirect (e.g. `http://localhost:3000`).

**Frontend:**

- `REACT_APP_BACKEND_URL` – API base.

---

## 5. Test Run (Proof)

To run automated tests (against a running backend):

```bash
cd backend
export REACT_APP_BACKEND_URL=http://localhost:8000  # or your backend URL
pytest tests/test_crucibai_api.py -v --tb=short
```

New tests:

- `TestBuildPhasesAndValidate::test_build_phases`
- `TestBuildPhasesAndValidate::test_validate_and_fix`
- `TestStripeEndpoints::test_stripe_checkout_requires_auth`
- `TestStripeEndpoints::test_stripe_checkout_invalid_bundle`

Existing tests (health, chat, auth, tokens, projects, etc.) remain unchanged; chat now uses fallback internally.

---

## 6. Summary

- **Model selection & fallbacks:** Implemented; chat and stream try primary then fallback chain on failure.
- **Project/build phases API:** Implemented; `GET /api/build/phases` and `GET /api/projects/{id}/phases`.
- **Validate-and-fix:** Implemented; `POST /api/ai/validate-and-fix`.
- **Stripe (pay us):** Implemented; create-checkout-session + webhook; Token Center “Pay with Stripe.”
- **Stripe in generated apps:** Implemented via prompt when user asks for payment/subscription/Stripe.
- **Real-time phase UI:** Implemented in Workspace with phase label during build.
- **Command palette:** Implemented; Ctrl+K, Deploy/Export/GitHub/Auto-fix/Tokens/Settings.
- **Paywall:** Implemented; low/zero balance banner in Workspace with link to Token Center.

**Next:** Run backend and frontend locally, run pytest, then complete the QC checklist above for sign-off.
