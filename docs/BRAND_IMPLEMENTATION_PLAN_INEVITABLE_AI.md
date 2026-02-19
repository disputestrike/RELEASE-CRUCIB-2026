# CrucibAI — Full End-to-End Brand Implementation Plan: Inevitable AI

**Purpose:** Integrate the Inevitable AI brand strategy into the existing website and product with your agreed corrections. No implementation in this doc — plan only. Preserve what works; add outcome-first messaging; avoid feature-dump; reduce overstimulation; align visual identity.

**Basis:** Complete Brand Strategy (Inevitable AI), RATE_RANK_CODE_REVIEW, and current codebase (LandingPage, Features, index.css, tailwind, public pages).

**Status:** Final for approval. Once approved, implementation can follow this plan.

**Compliance:** Use **BRAND_IMPLEMENTATION_COMPLIANCE_CROSSWALK.md** during and after implementation to verify every item is wired and that auth, routes, and webhooks remain intact.

---

## 0. BRAND RULE: DON’T EXPOSE SECRET SAUCE (Public-facing)

**Rule:** On the **website and all public branding** (landing, pricing, Features, FAQ, marketing, press), do **not** name:
- **Models:** OpenAI, Claude, Gemini, or any LLM provider.
- **Image providers:** Together AI, Nano Banana, or any image API.

**Why:** Manus (and others) don’t tell you on their website which models they use. We do the same: sell outcomes and proof (120-agent swarm, 99.2%, full transparency), not provider names. Keeps positioning clean and avoids giving away the stack.

**Public copy:** Say “AI image generation,” “AI-generated visuals,” “powered by our 120-agent swarm” — never “Together AI” or “Nano Banana” on the front.

**In-app (Workspace, AgentMonitor):** When the user is inside the product (e.g. image generation running), use **generic** status only: e.g. “Generating image…” or “Image generation…” with **no** provider name in the main UI. Optionally, provider can appear in Settings (e.g. “Image provider: default”) or in debug/admin only, not in the main generation status. So we do **not** copy Manus’s “Nano Banana generating image” in the IDE unless we explicitly decide we want that for power users later; default is generic.

**Tier naming:** We use Free, Starter, Builder, Pro, Agency (and add-ons Light, Dev). Manus uses Light / Light Pro / Pro Max. Our structure is already clear; no need to rename. Do **not** tie model names to tiers on the site (e.g. no “Gemini for free tier” or “Claude for Pro”).

---

## 0.1 AGENT COUNT, SWARM, AND IMAGE GENERATION (Brand Consistency)

### Agent count: 120 (not 115 or 100)

**Current inconsistency:** Backend DAG and `verify_120_agents.py` use **120** agents. Some marketing and IDE extensions say **115**. Landing and Workspace say **100** in several places.

**Recommendation:** Use **120** everywhere as the single source of truth. The DAG is built for 120; it’s your differentiator. Update:
- **Landing:** All “100 agents” → “120 agents”; “100-agent orchestration” → “120-agent swarm.”
- **Features, FAQ, comparison table:** 100 → 120.
- **IDE extensions (package.json, extension.js, plugin.xml):** 115 → 120.
- **Proof strip and hero:** “120 specialized agents” or “120-agent swarm.”
- **Docs and rate/rank:** Where they say 115, align to 120 unless you intentionally trim the DAG later.

### Use “swarm” in messaging

**Recommendation:** Use **“agent swarm”** or **“120-agent swarm”** in proof and positioning. You already have Swarm (Beta) as a mode (plan + suggestions in parallel). The word “swarm” differentiates you from “one LLM” and matches the product.

- **Proof strip:** “120-agent swarm” (not just “120 specialized agents”).
- **Hero / NEW badge:** “120-agent swarm, 99.2% success, full transparency” or “Inevitable AI — 120-agent swarm.”
- **Features / How it works:** “120-agent swarm working in parallel” and “Swarm mode runs agents in parallel for speed.”
- **Keep:** “Swarm (Beta)” as the mode name in Workspace; no change there.

### Image generation (backend: two options; front: no provider names)

**Current:** Backend uses **Together AI** (e.g. FLUX) for the Image Generation agent. **Nano Banana** is to be added as a second option so we have two image providers in the product.

**Public branding (website, landing, Features, FAQ):**
- Do **not** name Together AI or Nano Banana. Use only: “AI image generation,” “AI-generated visuals,” “hero and feature images.”
- Same rule as §0: don’t expose secret sauce on the front.

**Backend / product:**
- **Primary in production:** Together AI (keep as is).
- **Add Nano Banana** as an option (e.g. user or project setting, or fallback) so we offer two image providers in the product. No need to advertise the names publicly.
- **In-app UI (Workspace, AgentMonitor):** When image generation is running, show **generic** status only: “Generating image…” or “Image generation…” — **no** provider name (e.g. no “Nano Banana generating image” in the main UI). Optionally, provider can be visible in Settings or debug only. Default = generic.

**Implementation:** Backend/image_generator: keep Together AI; add Nano Banana integration as alternate path or selectable provider. Frontend: no copy that names either provider; in-app status text = generic.

### Pricing strategy (free tier, Gemini, tiers) — preserve and reflect in brand

**Current (from code):**
- **Free tier:** 50 credits, `landing_only: True` in plan config (~1 landing page); 3 projects max on free.
- **Paid tiers:** Starter $12.99 (100 credits), Builder $29.99 (500), Pro $79.99 (2000), Agency $199.99 (10000). Add-ons: Light 50 credits/$7, Dev 250/$30.
- **Annual:** 17% off (2 months free): Starter $129, Builder $299, Pro $799, Agency $1999.
- **Credits/LLM:** MIN_CREDITS_FOR_LLM = 5; prepay; insufficient credits → 402 with “Buy more in Credit Center.”
- **Models:** `auto` (prefer best available), `gpt-4o`, `claude`, `gemini`. Gemini is in the chain (e.g. `gemini-2.5-flash`) when keys are set; used for chat/stream/plan when selected or as fallback.
- **Referral:** 100 credits each (referee + referrer if referrer on free plan); 10/month cap per referrer.

**Recommendation:** Keep all of the above. In the brand plan and on the Pricing page:
- Do **not** show model names (Manus-style): no OpenAI, Claude, Gemini on the site. Lead with outcomes and credits only.
- One outcome line on Pricing: “Predictable pricing for inevitable outcomes” or “Plans that match how you build.”
- Free tier: “50 credits to start — one landing or small app. No credit card required.”
- Keep Pricing page structure (bundles, add-ons, outcome calculator, Enterprise CTA). No structural change; only ensure copy aligns with Inevitable AI. Tier structure (Free / Starter / Builder / Pro / Agency) is already clear; no need to copy Manus’s Light / Light Pro / Pro Max naming.

### Office-style outputs: PDF and Excel (we have them)

**Current:** We have **PDF Export** and **Excel Export** agents (reportlab, openpyxl); **Invoice Agent** (PDF). Users get formatted PDF reports, spreadsheets, and invoice-style outputs as part of the app/output pipeline — not a general “edit any Word/PPT” like Kimi’s Office agent.

**Recommendation:**
- **Useful and on-brand:** Yes. Export to PDF and Excel (reports, tracking, invoices) is useful for apps and fits “full-stack outcome.” Call it out in Features and “What is CrucibAI”: “Export to PDF and Excel (reports, spreadsheets, invoices).”
- **Don’t claim:** “Office agent that edits Word/PPT in one shot” like Kimi. We’re app/output focused: we **generate** PDFs and Excel as outputs of the build, not a standalone doc editor.
- **PowerPoint:** Not in the current DAG. Add to roadmap if you want “presentation export”; otherwise keep messaging to PDF + Excel.

### Real websites vs wrappers — can we build better websites than Manus?

**Direct answer: Yes. We build real websites (and full-stack apps), not just wrappers.**

**Evidence in code:**
- **Design Agent:** Outputs placement spec (hero, feature_1, feature_2) with position, aspect, role — tells you where things go.
- **Layout Agent:** Takes frontend code + design spec and injects image placeholders into React/JSX in the right places.
- **Image Generation:** Fills hero and feature images (backend: two provider options; no provider names in public messaging).
- **Frontend Generation:** React/Next.js UI components. **Backend Generation:** APIs, auth, business logic. **Database Agent:** schema, migrations. **API Integration, Test Generation, SEO Agent,** etc.

So we produce **multi-section, structured, deployable apps** with real placement, real backend, real DB — not single-page wrappers or generic templates. We can build **better websites than Manus** in the sense: same “premium, clean” outcome **plus** full stack (backend, DB, API), Design Agent + Layout Agent (controlled placement), quality score, mobile + store pack, and full transparency (AgentMonitor). Manus does websites; we do websites **and** mobile and full-stack apps with visible orchestration.

**Messaging:** “Real websites and full-stack apps — not wrappers. Design Agent places hero and features; Layout Agent wires them in; 120-agent swarm builds the rest. Premium outcomes, full visibility.”

---

## I. EXECUTIVE SUMMARY

**Goal:** The site should feel like “Inevitable AI” (certainty, outcome guarantee, proof) without ripping out the good structure you have. Features stay, but they support the story — they don’t lead it.

**Approach:**
- **Primary message everywhere:** “Inevitable AI” / “Intelligence that makes outcomes inevitable.” Not “transparent AI” as the main tagline; “transparent” is a proof point (full transparency, see every decision).
- **Landing:** One clear hero (Inevitable AI + outcome), one proof block (120-agent swarm, 99.2%, time-to-reality, full transparency), then your existing input + sections. Reduce density so the hero and proof breathe; keep “What is CrucibAI,” “Key Features,” “For Every Need,” “How it works,” Examples, Compare, FAQ, footer — but shorten some blocks and use outcome language in headings/subtext.
- **Features page:** Reframe as “Why it’s inevitable” — outcome first, then 3–4 proof pillars (e.g. 120-agent swarm, full transparency, quality score, deploy) with features under each. Not 13 feature cards in a row.
- **Visual:** Align colors to brand (accent #6366F1, primary dark #0A0E27 optional); keep **Outfit + Inter** (better than Segoe UI for a dev/AI brand); optionally soften grid pattern or section count to reduce overstimulation.
- **Corrections baked in:** 72-hour → “typically under 72 hours” or “48–72 hours” until you have a solid metric; “zero supervision” → “minimal supervision” / “declare intent, come back to reality”; “physics” → “measured” or “proven.”

**What we preserve:** Nav structure, auth flow, workspace, app shell, dashboard, **pricing strategy** (free 50 credits, landing_only, Starter/Builder/Pro/Agency, add-ons, annual, Gemini in model chain, referral), templates, benchmarks, learn, shortcuts, FAQ content (with light copy edits), comparison table, footer links, all existing functionality.

---

## II. BRAND CORRECTIONS (Baked Into Plan)

| Brand doc phrase | Correction | Where it appears in plan |
|------------------|------------|---------------------------|
| “72-hour average manifestation” | Use “typically under 72 hours” or “48–72 hours from idea to deployed app” until you have a defensible average from real data. | Hero subtext, Proof section, any GTM/press |
| “Zero supervision required” | “Minimal supervision” or “Declare intent. Walk away. Come back to reality.” (Autonomous execution, low touch — not literally zero.) | Proof section, value props, FAQ if mentioned |
| “Not promises. Physics.” | “Not promises. Measured.” or “Not promises. Proven.” (Same punch, more defensible.) | Proof section, CTAs, footer |
| “Transparent AI” as tagline | Do **not** lead with “Transparent AI.” Lead with “Inevitable AI.” Use “full transparency” as a proof point (see every decision, every phase, no black boxes). | All hero/headlines: Inevitable AI; tactical line can be “The AI that makes your ideas inevitable — with full transparency.” |

---

## III. MESSAGING HIERARCHY: INEVITABLE VS TRANSPARENT

**Decision:** Stay with **Inevitable AI** as the primary brand. “Transparent” supports; it doesn’t replace.

- **Strategic (hero, nav, press, ProductHunt):** “Inevitable AI” / “Intelligence that doesn’t just act — it guarantees.” / “Describe your vision. Watch it become inevitable.”
- **Tactical (subhead, Features, for-users):** “The AI that makes your ideas inevitable.” Optional add: “Full transparency: see every phase, every agent, no black boxes.”
- **Proof (everywhere):** 120-agent swarm • 99.2% deployment success rate • typically under 72 hours • full transparency • minimal supervision.

So: **Inevitable** = category and promise. **Transparent** = reason to believe (we show the work).

---

## IV. PAGE-BY-PAGE PLAN

### 4.1 Landing Page (`LandingPage.jsx`)

**Current state (summary):** Hero “Hello, Welcome to CrucibAI” + plan-first subtext; NEW badge (100 agents, Design/SEO, Swarm); 4 CTAs; large input panel; then many sections: What is CrucibAI, Key Features (6), For Every Need (5), How it works (3), Examples, Where can you use, How to use, Compare table, Better/Faster/Helpful, Real-world use cases, Limitations, Roadmap, FAQ, footer CTA, footer. Grid background, Outfit headlines, Inter body, kimi tokens (black, white, blue).

**Overstimulation:** Many sections in one scroll; hero competes with NEW badge and four buttons; “Key Features” is a second feature list after “What is CrucibAI” bullets. We don’t remove sections; we clarify hierarchy and shorten some blocks so the hero + proof dominate.

**Preserve (no structural change):**
- Nav (links, Get started, Sign in/Dashboard).
- Mobile menu.
- Main input panel (messages, attach, voice, submit, “Not sure where to start?” chips).
- “What are you building” / “Try these” behavior.
- Examples section (live examples + fallback cards, Fork, quality score).
- Where can you use CrucibAI (Web, API, Export) — keep accordion.
- Compare table (CrucibAI vs Kimi, Cursor, Manus, ChatGPT).
- Better / Faster / More helpful three cards.
- FAQ accordion (all questions; only light copy tweaks for “inevitable”/“outcome” where natural).
- Footer CTA + footer columns and links.

**Change (copy + light structure):**

1. **Hero**
   - **NEW badge:** Keep one badge; copy can become: “Inevitable AI — 120-agent swarm, 99.2% success, full transparency” (or shorter: “Inevitable AI” only).
   - **H1:** Replace “Hello, Welcome to CrucibAI” with **“Inevitable AI”** (or “CrucibAI — Inevitable AI” if you want name first).
   - **Subhead:** Replace current plan-first line with outcome-focused: **“Intelligence that doesn’t just act. It guarantees. Describe your vision. Watch it become inevitable.”** (Or the brand’s exact: “Describe your vision. Watch it become inevitable. No building. No waiting. No maybe. Just certainty.”)
   - **CTAs:** Primary stays “Get started” or **“Make It Inevitable”** (brand CTA). Others: Open Workspace, Templates, Pricing — keep. So one primary CTA label change to “Make It Inevitable” is the only CTA copy change if you adopt it.

2. **New block: Proof strip (insert once, right after hero, before input)**
   - Add a single **Proof** section between hero and the main input panel.
   - Content (short): **120-agent swarm** • **99.2% deployment success rate** • **Typically under 72 hours** • **Full transparency** • **Minimal supervision**.
   - Visual: One row of 5 items (icons or numbers + label), no long paragraphs. Keeps hero → proof → input flow clear. “Not promises. Measured.” or “Not promises. Proven.” as a small line under the strip.

3. **“What is CrucibAI?”**
   - Keep section. **Headline:** can stay or become “Why CrucibAI?”.
   - **Body:** First sentence outcome-focused: “CrucibAI is Inevitable AI — the platform where intelligence doesn’t just act, it makes outcomes inevitable.” Then keep plan-first, 120-agent swarm, no surprises. Add one line: “Full transparency: every phase, every agent, no black boxes.” Optionally: “Real websites and full-stack apps — Design Agent places hero and features; Layout Agent wires them in; we’re not wrappers.”
   - **Bullets:** Keep; optionally add “99.2% success,” “typically under 72 hours,” and “Export to PDF and Excel (reports, spreadsheets, invoices)” to the list.

4. **“CrucibAI Key Features”**
   - Keep the 6 items. **Section headline:** “Why it’s inevitable” or “What makes it inevitable” (so features support outcome).
   - **Subtext:** One line: “Not just features — the proof behind inevitable outcomes.” Keep the 6 feature titles/descriptions; only tweak any “fast/easy” to “certain”/“reliable” where it fits.

5. **“CrucibAI for Every Need”**
   - Keep 5 cards and CTAs. Optionally add one outcome line above: “Your idea → deployed app. Inevitable.”

6. **“How CrucibAI Works” (3 steps)**
   - Keep. **Subtext:** “Plan-first, 115 agents, full transparency. From description to reality.”
   - Step 3 can mention “iterate until it’s right — then export. Inevitable.”

7. **“See What CrucibAI Built” / Examples**
   - Keep. Subtext can say “Real apps from our 120-agent swarm. Inevitable outcomes, forkable.”

8. **“How to Use CrucibAI” (steps)**
   - Keep. Optional: last step “Receive your app — inevitable.”

9. **“Who Builds Better / Faster / More Helpful?”**
   - Keep. Add one line above or in the block: “Inevitable outcomes. Measured.” (replacing “physics” if it ever appeared).

10. **Limitations / Roadmap**
    - Keep. No need to change for brand.

11. **FAQ**
    - Keep all questions. In “What is CrucibAI?” answer: add “Inevitable AI” and “outcomes inevitable” once. In any answer that says “fast” or “easy,” optionally add “and reliable” or “with 99.2% success.” No structural change.

12. **Footer CTA**
    - **Headline:** “Make your idea inevitable” or “CrucibAI — Inevitable AI.”
    - **Button:** “Make It Inevitable” or “Get started” (consistent with hero).

13. **Footer tagline**
    - “Turn ideas into software” → “Turn ideas into inevitable outcomes” or keep and add “Inevitable AI.” under the logo.

**Reduce overstimulation (optional but recommended):**
- Slightly increase vertical spacing between “What is CrucibAI,” “Key Features,” and “For Every Need” so the page doesn’t feel like one long list.
- If the grid pattern feels busy, reduce opacity (e.g. `--kimi-grid: rgba(255,255,255,0.02)`) or use it only in hero; rest solid dark.
- Keep one NEW badge; avoid adding more floating badges.

**File:** `frontend/src/pages/LandingPage.jsx`. All changes are copy and one new Proof block (no new routes).

---

### 4.2 Features Page (`Features.jsx`)

**Current state:** “CrucibAI Features” headline; 13 feature cards in a 3-column grid; one CTA at bottom. Pure feature list.

**Problem:** Feature-dump; doesn’t lead with outcome or proof.

**Preserve:** PublicNav, PublicFooter, layout shell, and the fact that we do list capabilities. No removal of information.

**Change:**

1. **Headline and subtext**
   - **Headline:** “Why your outcome is inevitable” or “What makes CrucibAI inevitable.”
   - **Subtext:** “Not just features — proof. 120-agent swarm, 99.2% success, full transparency. Below is how we get you there.”

2. **Structure: outcome-first, then features as proof**
   - **Option A (recommended):** Add a short “Proof” strip at top (same 5 points: 115 agents, 99.2%, time, transparency, minimal supervision). Then group the 13 features into **3–4 pillars** with small headings, e.g.:
     - **Orchestration:** Describe & build, 20 AI agents, Plan-first, Iterate in chat.
     - **Quality & control:** Production-ready code, Security & quality, Design control, Templates, Pattern library, Prompt library.
     - **Visibility & control:** Usage & tokens, Shortcuts & commands.
     - **Ship:** Export & deploy, Web + mobile.
   - **Option B (lighter):** Keep the 13 cards in a grid; add the one Proof strip above the grid and change page headline/subtext only. Fewer changes, still outcome-first at top.

3. **Copy in cards**
   - Where a card says “fast” or “easy,” add “reliable” or “with 99.2% success” where it fits. No need to rewrite every card.

4. **CTA**
   - “Get started” or “Make It Inevitable” — match landing.

**File:** `frontend/src/pages/Features.jsx`.

---

### 4.3 Pricing Page (`Pricing.jsx`)

**Preserve:** Plan names, prices, feature lists, TokenCenter link, Enterprise CTA. No structural change.

**Change:** Only copy.
- **Page headline:** Add one line: “Predictable pricing for inevitable outcomes.” or keep as is.
- **Subtext:** Optionally “Plans that match how you build. 99.2% success, full transparency.”
- No “transparent AI” as headline; “inevitable” can appear once in subtext.

**File:** `frontend/src/pages/Pricing.jsx`.

---

### 4.4 Enterprise Page (`Enterprise.jsx`)

**Preserve:** Structure and value props.

**Change:** Headline or subtext once: “Enterprise-grade Inevitable AI. Full transparency, 99.2% success, full visibility.”

**File:** `frontend/src/pages/Enterprise.jsx`.

---

### 4.5 Other Public Pages (Templates, Benchmarks, Learn, Shortcuts, Prompts, Patterns, Privacy, Terms, etc.)

**Preserve:** All. No structural changes.

**Change (optional, minimal):**
- **Templates / Learn / Benchmarks:** In the main heading or one subtext line, add “Inevitable AI” or “from CrucibAI — Inevitable AI” so the brand appears. Don’t add new sections.
- **Footer (PublicFooter.jsx):** If there’s a tagline, make it “CrucibAI — Inevitable AI” or “Turn ideas into inevitable outcomes.” One line.

---

### 4.6 App Shell (Dashboard, Workspace, Layout, Settings)

**Preserve:** All behavior, sidebar, workspace, AgentMonitor, dashboard, settings. No product changes for brand.

**Change (optional):**
- **App title or sidebar brand:** “CrucibAI” can have a small “Inevitable AI” under it in the sidebar or in the browser tab title. Very light.
- **First-run or empty state:** If there’s a line like “Turn ideas into software,” change to “Make your idea inevitable” or add “Inevitable AI” once. Only if such copy exists.

**Files:** `Layout.jsx`, `App.js` (document title), any dashboard empty state.

---

## V. FEATURES: HOW TO TALK ABOUT THEM

**Rule:** Lead with outcome and proof; use features as evidence.

**Do:**
- “Your vision will exist. Guaranteed.” (outcome)
- “120-agent swarm. 99.2% success. Full transparency.” (proof)
- “Plan-first, 120-agent swarm, design-to-code, PDF/Excel export — that’s how we make it inevitable.” (features support)
- “Real websites and full-stack apps — Design Agent places hero and features; not wrappers.” (when comparing to Manus/others)

**Don’t:**
- “Fast, easy, simple” as hero or primary message (use “certain,” “reliable,” “inevitable”).
- Long lists of features with no outcome line above them.
- “Transparent AI” as the main tagline (use “Inevitable AI”; “full transparency” as proof).
- **Name models or image providers in public branding:** no OpenAI, Claude, Gemini, Together AI, or Nano Banana on landing, Pricing, Features, or marketing (see §0).

**Where features appear:**
- **Landing:** One “Key Features” block (6 items) + “How it works” (3 steps) + use cases. All stay; add outcome framing in headings/subtext.
- **Features page:** Proof strip + grouped or listed features with one outcome headline.
- **Pricing:** Feature lists per plan stay; add one outcome line at top.
- **Elsewhere:** No new feature sections; only light copy tweaks for consistency.

---

## VI. VISUAL IDENTITY

### 6.1 Colors

**Brand doc:** Primary dark #0A0E27, Primary light #FFFFFF, Accent #6366F1, Secondary gray #9CA3AF, Success #10B981.

**Current:** `--kimi-bg: #000000`, `--kimi-accent: #2196f3` (blue).

**Plan:**
- **Option A (full alignment):** Introduce CSS variables for brand palette and use them alongside or instead of kimi: e.g. `--brand-bg: #0A0E27`, `--brand-accent: #6366F1`, `--brand-success: #10B981`. Use for CTAs, links, and key highlights. Keep black as an alternative if #0A0E27 feels too soft.
- **Option B (accent only):** Change only accent from #2196f3 to #6366F1 so “Inevitable AI” and CTAs feel brand-aligned; keep black background.
- **Recommendation:** Start with **Option B** (accent + success green for success states). Add full palette later if you want the navy look.

**Files:** `frontend/src/index.css` (`:root`), optionally `tailwind.config.js` if you map new tokens to Tailwind classes.

### 6.2 Typography

**Brand doc:** Segoe UI (Microsoft Edge heritage).

**Current:** Outfit (headlines), Inter (body), JetBrains Mono (code). In `index.css`: `font-family: 'Inter', ...` for body; `h1–h6` use Outfit.

**Assessment:** Outfit + Inter is more distinctive and modern than Segoe UI for a dev/AI product. **Recommendation: keep Outfit + Inter + JetBrains Mono.** No change unless you explicitly want to try Segoe UI for body (not recommended).

**Sizes (brand):** 48–56px headlines, 24–32px subheadlines, 16–18px body, 12–14px captions. Your `kimi-hero`, `kimi-section`, `kimi-body` are in the right ballpark. Optional: nudge hero to 48px min on large screens for “Inevitable AI” impact. No big typography overhaul.

### 6.3 Overstimulation (Landing / Home)

**Causes:** Many sections, grid pattern, several CTAs, NEW badge, long feature list.

**Planned changes (already in §4.1):**
- One clear hero message (Inevitable AI + one subtext).
- One Proof strip (5 points) so proof is scannable, not buried.
- Slightly more spacing between sections (e.g. `py-24` instead of `py-20` on 2–3 sections).
- Optional: grid opacity 0.02 or grid only in hero; rest solid.
- One primary CTA (“Make It Inevitable”); secondary CTAs stay but don’t compete with hero.

**Don’t:** Remove sections (Examples, Compare, FAQ, etc.). We’re reducing density and clarifying hierarchy, not stripping content.

---

## VII. FRONT-END FILE LIST (What to Touch)

| File | Action |
|------|--------|
| `frontend/src/pages/LandingPage.jsx` | Hero copy, NEW badge, Proof block, “What is CrucibAI” and “Key Features” headings/subtext, “For Every Need” / “How it works” / Examples / Compare / FAQ / footer CTA and tagline — outcome language; spacing if desired. |
| `frontend/src/pages/Features.jsx` | Headline, subtext, Proof strip (new), optionally group 13 features into 3–4 pillars; card copy tweaks. |
| `frontend/src/pages/Pricing.jsx` | One headline or subtext line (inevitable / 99.2%). Preserve pricing strategy: free 50 credits, tiers, add-ons, annual; no model names on page. |
| `frontend/src/pages/Enterprise.jsx` | One headline or subtext line. |
| `frontend/src/index.css` | Optional: `--kimi-accent` to #6366F1; `--kimi-grid` opacity; optional `--brand-*` variables. |
| `frontend/tailwind.config.js` | Optional: extend colors with brand accent/success if you add new variables. |
| `frontend/src/components/PublicFooter.jsx` | Tagline “CrucibAI — Inevitable AI” or “Turn ideas into inevitable outcomes” if present. |
| `frontend/src/App.js` | Optional: document title “CrucibAI — Inevitable AI”. |
| `frontend/src/components/Layout.jsx` | Optional: sidebar or app brand line “Inevitable AI” (small). |

No new pages or routes. No backend changes for marketing copy unless you later add a CMS or config for hero/proof (see below).

---

## VIII. BACK-END

**Current:** Marketing copy is in frontend components (LandingPage, Features, etc.). No backend-driven hero or proof stats.

**Plan:**
- **Phase 1:** No backend changes. All copy and proof numbers live in frontend as they do now.
- **Phase 2 (optional):** If you want proof numbers (99.2%, 72 hours, 120-agent swarm) to be configurable, add a small config (e.g. `backend/config/brand.json` or env vars) and one API route like `GET /api/brand` returning `{ tagline, proof_stats }`. Frontend fetches once and uses in hero and Proof strip. Not required for launch.

**Backend files (only if Phase 2):** `backend/config/brand.json` (or similar), `server.py` (one read-only route). No DB.

---

## IX. IMPLEMENTATION ORDER (Phases)

**Phase 1 — Core brand (Week 1)**  
1. **Landing hero + Proof:** Update hero (H1, subtext, NEW badge, primary CTA to “Make It Inevitable”); add Proof strip; “Not promises. Measured.”  
2. **Landing copy pass:** “What is CrucibAI,” “Key Features,” “For Every Need,” “How it works,” Examples, Compare, Better/Faster/Helpful, footer CTA and tagline — outcome language and corrections (72hr, minimal supervision).  
3. **Features page:** Headline/subtext + Proof strip; optionally group features into pillars.  
4. **Color:** Accent to #6366F1 (and success green if desired) in CSS.  
5. **Spacing / grid (optional):** Slightly more section padding; grid opacity or hero-only grid.  
6. **No secret sauce on front:** Audit all public copy (landing, Features, Pricing, FAQ) and remove any model or image-provider names (OpenAI, Claude, Gemini, Together AI, Nano Banana). Use only “AI image generation,” “AI-generated visuals,” outcomes, and credits.

**Phase 2 — Consistency (Week 2)**  
6. Pricing, Enterprise: one line each.  
7. PublicFooter tagline; document title.  
8. FAQ: light edits (What is CrucibAI, any “fast” → “reliable” or add 99.2%).  
9. App shell: optional “Inevitable AI” in sidebar or title.

**Phase 3 — Optional**  
10. Backend config for proof stats if you want them editable.  
11. Press release and ProductHunt assets (from brand doc); not in codebase.  
12. A/B test hero variants (e.g. “Inevitable AI” vs “CrucibAI — Inevitable AI”) if you have analytics.

---

## X. MESSAGING DO’S AND DON’TS (From Brand Doc, Integrated)

**Do:**
- “Your vision will exist. Guaranteed.”
- “Intelligence that makes outcomes inevitable.”
- “99.2% success rate. Not promises — measured.”
- “Describe your vision. Watch it become inevitable.”
- Lead with outcome; use features as proof.

**Don’t:**
- “Fast, easy, simple” as hero or primary message.
- “AI tool, AI platform, AI assistant” as category (use “Inevitable AI platform”).
- “Try it, might work, possibly faster.”
- “Transparent AI” as main tagline (use as proof: “full transparency”).
- “Zero supervision” (use “minimal supervision” or “declare intent, come back to reality”).
- “Physics” (use “measured” or “proven”).
- **Name models or image providers in public branding** (no OpenAI, Claude, Gemini, Together AI, Nano Banana on website or marketing — §0).

---

## XI. WHAT WE PRESERVE (Checklist)

- [ ] Nav: all links, Get started, Sign in, Dashboard.  
- [ ] Landing: input panel, messages, attach, voice, chips, Examples (live + fallback), Where accordion, Compare table, Better/Faster/Helpful, FAQ (all questions), footer columns and links.  
- [ ] Features: all 13 capabilities (reorganized or not); PublicNav, PublicFooter.  
- [ ] Pricing: free tier (50 credits, landing_only), Starter/Builder/Pro/Agency, add-ons, annual, Gemini in model chain, referral; plans, prices, feature lists, Enterprise.  
- [ ] Templates, Benchmarks, Learn, Shortcuts, Prompts, Patterns: structure and content.  
- [ ] Auth, workspace, dashboard, AgentMonitor, settings, TokenCenter: no product changes.  
- [ ] Fonts: Outfit, Inter, JetBrains Mono (no Segoe UI unless you decide otherwise).  
- [ ] All existing routes and behavior.

---

## XII. SUMMARY

- **Brand:** Inevitable AI everywhere; “transparent” as proof, not tagline.  
- **Don’t expose secret sauce (§0):** No model names (OpenAI, Claude, Gemini) or image-provider names (Together AI, Nano Banana) on landing, Pricing, Features, FAQ, or marketing. Same as Manus. In-app: generic “Generating image…” only (no provider in main UI).  
- **Tiers:** We keep Free / Starter / Builder / Pro / Agency; no model names per tier on the site.  
- **Corrections:** 72hr → “typically under 72 hours”; zero → minimal supervision; physics → measured/proven.  
- **Landing:** New hero + Proof strip; outcome language in sections; same sections, less density.  
- **Features:** Outcome-first headline + Proof; features as proof (grouped or listed).  
- **Rest:** One line on Pricing/Enterprise; optional footer/title/sidebar.  
- **Visual:** Accent #6366F1; keep Outfit/Inter; optional spacing/grid tweak.  
- **No new pages or backend** for Phase 1; optional backend later for configurable proof stats.  
- **Implementation:** Phase 1 (hero, proof, copy, colors, audit no provider names) → Phase 2 (rest of site, FAQ) → Phase 3 (optional config, GTM assets).

---

**This plan is final for approval.** Once approved, implementation can follow the phases above. No code has been implemented in this document.
