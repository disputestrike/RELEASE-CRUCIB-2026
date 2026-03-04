# Prompt Preservation + Landing UX — Evidence of Implementation

**Status:** All approved items implemented, wired, and integrated.  
**Date:** 2026-03-04

---

## 1. Goal (recap)

When someone types what they want to build on the homepage and is sent to sign-up/sign-in, their prompt must not be lost. After auth, they land on the workspace with that prompt already there, with clear “your idea is saved / loaded” messaging. No re-typing.

---

## 2. Evidence by plan step

### Step 1: Landing — save prompt to sessionStorage; long prompts omit from URL

| Requirement | Where it lives | Evidence |
|-------------|----------------|----------|
| Save prompt before redirect to auth | `frontend/src/pages/LandingPage.jsx` | Lines 11–12: `PENDING_PROMPT_KEY`, `MAX_PROMPT_IN_URL` (1500). Lines 46–52: `sessionStorage.setItem(PENDING_PROMPT_KEY, prompt)` before navigate; `workspacePath` = prompt length ≤ 1500 ? URL with `?prompt=...` : `'/app/workspace'`. |
| Long prompts (≥1500 chars) | Same file | Line 49–51: `prompt.length <= MAX_PROMPT_IN_URL` → include prompt in redirect URL; else redirect to `/app/workspace` only. Workspace reads from sessionStorage. |
| Wired | `startBuild()` is called on form submit (handleSubmit) and when user clicks send/arrow; unauthenticated path always saves to sessionStorage then redirects to auth with `redirect=` param. | Line 37–53; form onSubmit → handleSubmit → startBuild (line 136). |

### Step 2: Auth — show “We’ve saved your idea” when prompt is preserved

| Requirement | Where it lives | Evidence |
|-------------|----------------|----------|
| Detect saved prompt (URL or sessionStorage) | `frontend/src/pages/AuthPage.jsx` | Line 48–50: `redirectParam = searchParams.get('redirect')`, `hasSavedPrompt = redirectParam.includes('prompt=') \|\| !!sessionStorage.getItem('crucibai_pending_prompt')`. |
| Show message (no prompt in auth form) | Same file | Line 221–225: `{!error && hasSavedPrompt && (...)}` — green box: “We've saved your idea. It'll be ready when you're signed in.” Message is display-only; prompt is not put into any auth field. |
| After login, navigate to redirect | Existing behavior preserved | Lines 54–58: when `user` is set, `navigate(redirect \|\| '/app', { replace: true })`. Workspace then loads prompt from URL or sessionStorage. |

### Step 3: Workspace — read sessionStorage, pre-fill, welcome message, clear, auto-start

| Requirement | Where it lives | Evidence |
|-------------|----------------|----------|
| Initial prompt: state → URL → sessionStorage | `frontend/src/pages/Workspace.jsx` | Lines 739–750: `statePrompt = location.state?.initialPrompt \|\| searchParams.get('prompt')`; `storedPrompt = sessionStorage.getItem(PENDING_PROMPT_KEY)` then `sessionStorage.removeItem(PENDING_PROMPT_KEY)`; `promptToUse = statePrompt \|\| storedPrompt \|\| task?.prompt...`. |
| Pre-fill input when from sessionStorage | Same file | Lines 756–760: `if (storedPrompt) { setInput(storedPrompt); setShowSavedPromptWelcome(true); setTimeout(..., 5000); }`. |
| “Welcome back! Your idea is loaded.” | Same file | Lines 418, 2378–2382: `showSavedPromptWelcome` state; when true, render green banner with that text (dismisses after 5s). |
| Clear storage after use | Same file | Line 745: `if (storedPrompt) sessionStorage.removeItem(PENDING_PROMPT_KEY)` immediately after get. |
| Auto-start build when prompt from sessionStorage | Same file | Line 752: `shouldAutoStart = stateAutoStart \|\| !!storedPrompt \|\| ...`; line 762: `handleBuild(promptToUse, initialFiles)`. So stored prompt triggers build same as URL/state. |

### Step 4: Edge cases

| Case | How it’s handled |
|------|------------------|
| Long prompt (2000+ chars) | Landing: redirect = `/app/workspace` only; prompt only in sessionStorage. Workspace: reads from sessionStorage, uses it, clears it. |
| Special characters in prompt | Short prompts: `encodeURIComponent(prompt)` in URL (Landing line 51). sessionStorage: stored and read as-is (no double-encode). |
| Back button during auth | Prompt stays in sessionStorage (and in URL for short prompts) until Workspace consumes it; we don’t clear on auth page. |
| Clear after use | Cleared only in Workspace after reading (line 745). |
| Attached files through auth | Not persisted in this phase (plan: follow-up). State still passed when user is logged in; for unauthenticated flow only prompt is preserved. |

---

## 3. Additional UI/UX (Landing) — wired in same flow

| Item | Where | Evidence |
|------|--------|----------|
| Softer typography (2.5rem, font-semibold, #1a1a1a) | `LandingPage.jsx` | Hero h1, tagline, CTA section (softer sizes/weights). |
| Single border on input (no double border) | `LandingPage.jsx` | One wrapper `.landing-input-wrap` with single `border border-[#d1d5db]`; focus ring on focus-within. |
| Suggestion chips below input | `frontend/src/components/SuggestionChips.jsx` (new); used in `LandingPage.jsx` | Chips: Create slides, Build website, Develop apps, Design, Landing page. `onSelect={(prompt) => setInput(prompt)}`. |
| Voice + send button inside input | `LandingPage.jsx` | Mic (existing backend transcription) and send (ArrowRight) in same row; send triggers handleSubmit → startBuild. |
| Prompt preservation constants | `LandingPage.jsx` | `PENDING_PROMPT_KEY = 'crucibai_pending_prompt'`, `MAX_PROMPT_IN_URL = 1500` (lines 11–12). |

---

## 4. Data flow (integration)

```
Landing (not logged in):
  User types prompt → Submit → startBuild()
    → sessionStorage.setItem('crucibai_pending_prompt', prompt)
    → redirect = /auth?mode=register&redirect=/app/workspace?prompt=... (or /app/workspace if long)
  User lands on Auth → hasSavedPrompt true → "We've saved your idea..." shown
  User signs up/in → navigate(redirect) → Workspace

Workspace:
  On load → read statePrompt (state/URL) or storedPrompt (sessionStorage)
    → if storedPrompt: removeItem, setInput(storedPrompt), setShowSavedPromptWelcome(true), handleBuild(promptToUse)
  User sees "Welcome back! Your idea is loaded." and build starts (or prompt pre-filled and they can click Build).
```

---

## 5. Files changed (summary)

| File | Role |
|------|------|
| `frontend/src/pages/LandingPage.jsx` | sessionStorage save, long-prompt redirect, softer typography, single border, SuggestionChips, send/voice layout. |
| `frontend/src/pages/AuthPage.jsx` | hasSavedPrompt, “We’ve saved your idea” message. |
| `frontend/src/pages/Workspace.jsx` | Read/clear sessionStorage, promptToUse order, welcome banner, auto-start from stored prompt. |
| `frontend/src/components/SuggestionChips.jsx` | New component; chips that fill the landing textarea. |

---

## 6. How to confirm (manual)

1. **Short prompt through auth**  
   Log out, go to `/`, type e.g. “Build a todo app”, submit → redirect to auth with `?redirect=...prompt=...`. On auth page see “We've saved your idea...”. Sign in → Workspace opens with prompt in URL; build can start (or prompt in input). No re-typing.

2. **Long prompt (e.g. 1600 chars)**  
   Same flow; redirect should be `/app/workspace` (no prompt in URL). After login, Workspace loads prompt from sessionStorage, shows “Welcome back! Your idea is loaded.” and uses it for build.

3. **Suggestion chips**  
   On `/`, click a chip → textarea fills with that prompt. Submit → same as above (prompt preserved through auth if not logged in).

4. **Clear after use**  
   After Workspace loads stored prompt, `sessionStorage.getItem('crucibai_pending_prompt')` should be null (cleared in Workspace on read).

---

All approved plan items are implemented, wired, and integrated. This document serves as evidence for testing and sign-off.
