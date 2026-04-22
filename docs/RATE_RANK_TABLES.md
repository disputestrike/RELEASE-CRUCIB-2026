# Rate-Rank-Compare — Tables Only

**Source:** RATE_RANK_COMPARE_LATEST.md (post–pull c3babcc).  
**Use:** Quick reference for scores and vs competitors.

---

## Table 1 — New rate-rank-compare (scores)

| Dimension | Score | Notes |
|-----------|--------|------|
| **Product completeness** | 10/10 | 32/32 wired; Engine Room; input/attach/voice; **live dashboard builds**; **share**; **doubled pricing**. |
| **UX & flow** | 9.5/10 | Landing (power stats) → dashboard (live progress) → workspace (share) → export; Engine Room. |
| **Technical depth** | 9.5/10 | DAG, 120+ agents, PostgreSQL, Stripe, SSE, Monaco, Sandpack; routing modes + safety UX. |
| **GTM readiness** | 10/10 | LAUNCH_GTM; mobile as unique card; app supports the moment; guardrails keep assistant on-build. |
| **Differentiation** | 10/10 | Prompt → Expo + store; quick build; model/safety/fine-tuning in one app (Engine Room). |
| **Overall** | **10/10** | Best combined package; second pass adds AI-company-grade controls; nothing missing. |

---

## Table 2 — Versus (CrucibAI vs competitors)

| Competitor | Typical strength | CrucibAI advantage |
|------------|------------------|--------------------|
| **v0 / Vercel** | UI components, React | Full app + backend + **mobile to store** in one flow; build history; quick build; **Engine Room**. |
| **Lovable** | Speed, UX | **Mobile to App Store/Play**; 120+ agent DAG; token/pricing/referrals; export center; **Engine Room**. |
| **Bolt / Replit** | In-browser dev, repls | **Prompt → Expo + store submission**; DAG orchestration; workspace + export + deploy; **Engine Room**. |
| **Cursor / Windsurf** | IDE + AI | **No-code/low-code to shippable app + mobile**; landing → dashboard → workspace → export; **Engine Room**. |
| **Others** (Figma→code, Deploy) | Design or deploy only | **End-to-end:** prompt → plan → code → preview → export → **mobile store prep**; **Engine Room**. |

**Positioning:** CrucibAI is the only one that takes a **single prompt** to a **full Expo project with App Store and Play Store submission guides**, with an in-app **Engine Room**, **live dashboard builds**, **share**, and **doubled credits** (e.g. Builder 500 @ $15).

---

*Full narrative: docs/RATE_RANK_COMPARE_LATEST.md. Playground compare: docs/PLAYGROUND_COMPARE.md. After pull: run `npm install` in frontend (ensures jszip etc.); `pip install -r requirements.txt` in backend.*
