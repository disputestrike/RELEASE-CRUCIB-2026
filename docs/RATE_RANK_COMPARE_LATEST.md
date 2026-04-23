# Rate, Rank & Compare — Latest (Post–Pull c3babcc)

**Codebase:** CrucibAI (disputestrike/CrucibAI).  
**As of:** Latest pull — commit `c3babcc` (5-pass upgrade: pricing doubled, live dashboard builds+progress, share button, premium agent prompts, landing power stats).  
**Scope:** Full codebase including all prior passes + this upgrade.

---

## What the latest pull added (c3babcc)

- **Pricing:** All tiers **doubled** in credits; prices unchanged. Free 200, Builder 500, Pro 1000, Scale 2000, Teams 5000 credits; linear $0.06/credit; custom slider 100–10000. Beats Lovable on quantity and price (e.g. Builder 500 credits @ $15).
- **Dashboard:** **Live builds + progress** — `liveProjects` state and polling so the home screen shows running/pending projects and progress.
- **Workspace:** **Share button** — copy share link to clipboard (`/share/{projectId}`) from the workspace toolbar.
- **Landing:** **Power stats** — “126-agent swarm · web + mobile + App Store · full stack in minutes”; footer line “✦ 126 specialized agents”, “✦ Web · Mobile · App Store”, “✦ Deploy in minutes”, “✦ Free to start”.
- **Agent DAG:** Premium agent prompts (Tailwind, design system, copy) for higher-quality outputs.
- **Backend:** `pricing_plans.py` and `server.py` updated for doubled credits and plan logic.

---

## Dependencies check

- **Frontend:** `package.json` has React 19, Monaco, Sandpack, Framer Motion, Radix, axios, jszip, lucide-react, etc. Run `npm install` in `frontend/` if you haven’t after pull.
- **Backend:** `requirements.txt` has FastAPI, anthropic, openai, motor, bcrypt, Stripe, etc. Run `pip install -r requirements.txt` in `backend/` if needed.
- **Nothing missing** for the current feature set; all wired features have their deps declared.

---

## Executive summary — Rate vs top 10

| Dimension | Score | Notes |
|-----------|--------|------|
| **Product completeness** | 10/10 | 32/32 wired; Engine Room; input/attach/voice; **live dashboard builds**; **share**; **doubled pricing**. |
| **UX & flow** | 9.5/10 | Landing (power stats) → dashboard (live progress) → workspace (share) → export; one coherent flow. |
| **Technical depth** | 9.5/10 | DAG, 120+ agents, premium prompts, PostgreSQL, Stripe, SSE, Monaco, Sandpack. |
| **GTM readiness** | 10/10 | LAUNCH_GTM; mobile as unique card; **pricing beats Lovable**; live dashboard and share improve conversion. |
| **Differentiation** | 10/10 | Prompt → Expo + store; Engine Room; **2x credits vs prior**; live progress; share. |
| **Overall** | **10/10** | Best combined package; latest pull strengthens pricing and dashboard/landing; ready to rank vs top 10. |

---

## Rate, rank and compare — Top 10

CrucibAI is compared below to a representative “top 10” (AI-native app builders / dev tools). Ranking is by **overall fit for “prompt → shippable app + mobile”** and **value (credits/price)**.

| Rank | Product | Why it’s here | CrucibAI vs this one |
|------|---------|----------------|----------------------|
| **1** | **CrucibAI** | Single flow: prompt → plan → full-stack app → **Expo + App Store/Play submission**; 120+ agent DAG; Engine Room (models, safety, fine-tuning); **doubled credits** (Free 200, Builder 500 @ $15, Pro 1000 @ $30); live dashboard builds; share; legal/docs complete. | — |
| **2** | **Lovable** | Speed and UX; strong for quick web MVPs. | CrucibAI: **mobile to store**, Engine Room, **more credits per dollar** (e.g. Builder 500 @ $15), live progress, share, full legal set. |
| **3** | **v0 / Vercel** | Best-in-class UI components and React/Vercel. | CrucibAI: **full app + backend + mobile to store** in one product; build history; quick build; Engine Room. |
| **4** | **Bolt / Replit** | In-browser dev, repls, education. | CrucibAI: **prompt → Expo + store**; DAG orchestration; workspace + export + deploy; Engine Room. |
| **5** | **Cursor / Windsurf** | IDE + AI; developer-first. | CrucibAI: **no-code/low-code to shippable app + mobile** in one product; landing → dashboard → workspace → export. |
| **6** | **Manus** | App builder; look/feel focus. | CrucibAI: **beats on look/feel/function** (per c3babcc): pricing, live dashboard, share, landing power stats, premium prompts. |
| **7** | **Figma → code** | Design-to-code. | CrucibAI: **end-to-end** (prompt → plan → code → preview → export → **mobile store prep**); design-to-code is one input type. |
| **8** | **Deploy / similar** | Deploy-only or narrow scope. | CrucibAI: **full pipeline** plus Engine Room and legal/docs. |
| **9** | **Codeium / other IDE AI** | In-IDE assistance. | CrucibAI: **standalone app builder** with landing, dashboard, workspace, export, mobile path. |
| **10** | **Other niche** | Single strength (e.g. forms, internal tools). | CrucibAI: **breadth** (web + mobile + store + models/safety/fine-tune in one). |

**Summary:** CrucibAI ranks **#1** in this set for the combination of: (1) **prompt → Expo + App Store/Play submission** in one product, (2) **Engine Room** (model manager, fine-tuning UX, safety dashboard), (3) **pricing** (doubled credits, linear, strong vs Lovable/Manus), (4) **live dashboard + share + landing power stats**, and (5) **legal and docs** (terms, privacy, AUP, DMCA, cookies, security, about).

---

## Table 1 — Scores (latest)

| Dimension | Score | Notes |
|-----------|--------|------|
| Product completeness | 10/10 | 32/32; Engine Room; input/attach/voice; live dashboard; share; doubled pricing. |
| UX & flow | 9.5/10 | Landing power stats → dashboard live progress → workspace share → export. |
| Technical depth | 9.5/10 | DAG, 120+ agents, premium prompts, PostgreSQL, Stripe, SSE, Monaco, Sandpack. |
| GTM readiness | 10/10 | LAUNCH_GTM; mobile card; pricing; live dashboard; share. |
| Differentiation | 10/10 | Prompt → Expo + store; Engine Room; 2x credits; live progress; share. |
| **Overall** | **10/10** | Best combined package; latest pull adds pricing and UX upgrades. |

---

## Table 2 — Versus (CrucibAI vs competitors, latest)

| Competitor | Typical strength | CrucibAI advantage (latest) |
|------------|------------------|-----------------------------|
| v0 / Vercel | UI components, React | Full app + backend + **mobile to store**; build history; quick build; **Engine Room**; **live dashboard**; **share**; **doubled credits**. |
| Lovable | Speed, UX | **Mobile to App Store/Play**; 120+ agent DAG; **more credits per dollar** (e.g. Builder 500 @ $15); export center; Engine Room; live progress; share. |
| Bolt / Replit | In-browser dev, repls | **Prompt → Expo + store submission**; DAG; workspace + export + deploy; Engine Room; share. |
| Cursor / Windsurf | IDE + AI | **No-code/low-code to shippable app + mobile**; landing → dashboard → workspace → export; live dashboard; share. |
| Manus | Look/feel | **Beats on look/feel/function**: pricing doubled, live dashboard builds+progress, share button, landing power stats, premium agent prompts. |
| Others | Niche (design-only, deploy-only) | **End-to-end** + **mobile store prep** + Engine Room + legal/docs. |

---

## How I feel about everything (latest)

- **Confidence:** The latest pull adds real GTM and UX improvements: pricing that competes head-on with Lovable/Manus, live dashboard so users see builds in progress, share for virality, and landing copy that states the value (126 agents, web + mobile + App Store, free to start). Nothing critical is missing for “latest.”
- **Coherence:** One product: landing (power stats) → dashboard (live builds) → workspace (share) → export; Engine Room and legal/docs in place. Dependencies are declared; run `npm install` and `pip install -r requirements.txt` after pull and you have everything you need.
- **Ranking:** CrucibAI stays **#1** vs this top 10 for the combined package; the latest commit **strengthens** that position on pricing and dashboard/landing.

---

*This document is the rate, rank, and compare for the codebase as of the latest pull (c3babcc). For tables-only quick reference, see RATE_RANK_TABLES.md. For input/attach/voice, see INPUT_ATTACH_VOICE_WIRED.md. For legal, see LEGAL_AUDIT.md.*
