# Architecture Notes — design-only items from EXTERNAL_AUDIT.md

These are audit items we've pulled *intentionally* at the design level, but
have *not* shipped as code. They're documented here so the next pass knows the
intended shape instead of re-deriving from zero.

## 1. "goosed" — external-backend pattern (paid-product adapted)

Goose runs a long-lived backend daemon (`goosed`) that the desktop/CLI talk to
over a local socket, with a JSON-RPC-ish contract. The clean parts for
CrucibAI's paid positioning:

- Single FastAPI process that owns all long-lived state (runs, cost, mesh,
  permissions), already implemented in `backend/server.py`.
- Frontend is the client — in our case React over HTTPS + WebSocket, same as
  today.
- The "paid" differentiator vs Goose's open-source daemon is **account-scoped
  runs with cost tracking and admin controls baked in**:
    - `/api/cost/*` (CF27) — billable surface.
    - `/api/doctor` (CF27) — tier-aware diagnostic.
    - `/api/runtime/compact` (CF27) — context-window budget enforcement per
      tier.

We are *not* shipping a separate daemon. The architectural lesson we take is
that **one backend owns all long-lived state**; we do not fork to child
processes per capability. Every audit-sourced capability lands as an in-process
FastAPI router under `backend/routes/`.

## 2. Peer-to-peer mesh (Cursor Tab / Claude Code session sharing)

The audit lists cross-device session mesh as a Cursor/Claude Code moat. Design
shape for CrucibAI:

- Session ID is the mesh key. Every client (web, desktop later, CLI) attaches
  to a session over WebSocket.
- Backend is the rendezvous — peers do **not** talk directly. Claude Code's
  actual implementation uses MCP + optional tailnet; we do the same *through
  our backend* so paid tenants get audit logging and rate limits for free.
- Session state lives in the DB (runs, journal events, permission-mode
  transitions) — already implemented under `backend/services/`.

Not shipped yet:

- Cross-device "resume this session on my phone" — needs (a) mobile client
  onboarding code path for an unauth'd device (QR pairing), and (b) server
  ACLs that scope a session token to a specific `workspace_id + user_id`.
- Live cursor sharing — explicitly deferred; it's a UX-heavy feature that
  doesn't pay off before we have a multi-seat tenant customer asking for it.

When we do ship this, the permission-mode state machine added in CF27
(`backend/services/permissions/mode_transitions.py`) is the gate: a session
joined from a second device starts in `DEFAULT`, even if the originating
device is in `BYPASS`.

## 3. Ollama / local-model probe — **explicitly skipped**

Audit item #7. Skipped on product grounds: CrucibAI is a paid product, not a
"bring your own local model" tool. If a tenant asks for self-hosted Claude
later, the integration point is adding an entry to the cost-tracker `PRICING`
table and a new provider adapter under `backend/services/llm/`, not a local
Ollama shim.

## 4. Unification principle

Everything CF27/CF28 landed as a router + page/component that lives under the
existing `/app/*` shell:

- `/app/cost` (Cost Center page) — CF28
- `/app/doctor` (Doctor diagnostic page) — CF28
- Voice input and `/compact` surface inside the ThreePaneWorkspace composer —
  CF28
- `Cmd/Ctrl+K` quick launcher is globally mounted inside `<BrowserRouter>` —
  CF28

So the audit items are not bolted on as separate tools; they're surfaces of
the same product.
