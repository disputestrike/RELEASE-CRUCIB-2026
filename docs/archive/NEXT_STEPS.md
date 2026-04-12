# What’s Next for CrucibAI

You’re at **10/10** on the roadmap with audit proof, build-anything positioning, and trading/game/mobile/SaaS/bot/agent support. Here’s a clear order of operations.

---

## Best next step: **Go live (soft launch)**

**Recommendation:** Ship to real users soon with a **minimal go-live checklist**, then improve from feedback. Avoid piling on features or heavy load tests before a first launch.

| Priority | Action | Why |
|----------|--------|-----|
| **1** | **Go live (soft launch)** | Validates the product, gets feedback, and creates momentum. You can limit signups or invite-only at first. |
| **2** | **Smoke / health in CI** | One quick run before deploy: health + auth + one build flow. Catches regressions without full stress tests. |
| **3** | **Stress / load tests** | Add when you expect a traffic spike or need to set SLAs. Not required for day-one soft launch. |
| **4** | **More features** | Add after launch based on what users ask for. Avoid feature creep before first release. |

---

## Go-live checklist (minimal)

- [ ] **Backend** on a host (e.g. Railway, Render, Fly.io) with `MONGO_URL` (e.g. Atlas) and `JWT_SECRET` set.
- [ ] **Frontend** built and served (e.g. Vercel, Netlify) with `REACT_APP_BACKEND_URL` pointing at your backend URL.
- [ ] **CORS** on backend: set `CORS_ORIGINS` to your frontend origin(s) (e.g. `https://yourapp.vercel.app`).
- [ ] **Auth** works: register, login, token persisted; optional Google OAuth if you use it.
- [ ] **One happy path** works: sign up → New Project → describe an app → build runs → project completes (with OpenAI/Anthropic keys in Settings or server).
- [ ] **Privacy + Terms** linked from footer (you already have the pages).
- [ ] **Optional:** Stripe live keys + webhook for paid tokens; or keep “buy tokens” for later and launch with free/welcome tokens only.

---

## If you do stress/load testing

- **When:** Before a planned launch event or once you have a target (e.g. “50 concurrent users” or “100 builds/day”).
- **What:** Health and a few key routes (e.g. `/api/health`, `/api/auth/login`, `/api/build/plan`) under load (e.g. k6 or Locust). Find breaking concurrency or timeout; fix and re-run.
- **Where:** In CI as a separate job or a one-off run before release. No need for 24/7 load unless you’re selling SLAs.

---

## If you add features before launch

Keep it to **launch-blockers only**, e.g.:

- One-click deploy (e.g. “Deploy to Vercel”) and show live app URL in the app.
- Clear “Add API key in Settings” when a build fails for missing key.

Everything else (more agents, more project types, advanced dashboards) is better **after** you have real usage and feedback.

---

## Summary

| Question | Answer |
|----------|--------|
| **Best next step?** | **Go live (soft launch)** with the minimal checklist above. |
| **Stress/load test now?** | Optional. Add when you have a traffic target or launch event; start with smoke/health in CI. |
| **More features now?** | Only launch-blockers. Defer the rest until after launch. |
| **After launch?** | Iterate from feedback; then add stress/load and more features as needed. |

Ship first, then harden and expand.
