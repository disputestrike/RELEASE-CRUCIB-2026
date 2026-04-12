# CrucibAI × Kimi-Inspired Plan — Approval Required

This document breaks down what to implement from [Kimi AI](https://kimik2ai.com/) into three phases: **1) Color, font, typography**, **2) Content strategy and structure**, **3) Functional features**. **No code will be written until you approve.**

---

## Phase 1: Color Strategy, Font Size, and Font Type (Kimi-style)

### 1.1 Kimi’s Visual System (Summary)

| Element | Kimi approach | Target for CrucibAI |
|--------|----------------|---------------------|
| **Background** | Deep black `#000000` or near-black `#0a0a0a` / `#111111` | Primary page background |
| **Primary text** | Pure white `#FFFFFF` for headings and key copy | All main headings, nav labels, primary CTAs |
| **Secondary text** | Light gray `#CCCCCC`–`#e0e0e0` for body/descriptions | Paragraphs, feature descriptions, footer copy |
| **Accent** | Vibrant blue (e.g. `#2196F3`) for links, key terms, icons | Links, “New” badges, feature icons, emphasis |
| **UI surfaces** | Very dark gray for cards/inputs; light gray borders | Cards, inputs, borders (`#141415`, `#1C1C1E`, `#333`) |
| **Grid** | Subtle dark grid overlay on hero/sections | Optional grid pattern on hero |
| **Buttons** | Primary: white bg + black text; secondary: dark bg + white border | Match Kimi’s CTA style |

**Font (Kimi):**  
- Clean, modern **sans-serif** (Inter / Open Sans / Roboto–style).  
- **Hierarchy:**  
  - **Hero headline:** Very large, bold (e.g. ~3rem–4rem).  
  - **Section titles:** Large, bold (~1.5rem–2rem).  
  - **Feature/card titles:** Medium-large, bold (~1.125rem).  
  - **Body:** Comfortable reading size (~1rem), regular weight.  
  - **Nav / footer / small UI:** Standard small size (~0.875rem).

### 1.2 Implementation Steps (Phase 1)

1. **Define Kimi-style design tokens**
   - Add to `frontend/src/index.css` (and/or Tailwind):
     - `--kimi-bg: #000000` (or `#0a0a0a`)
     - `--kimi-bg-elevated: #111111` / `#141415`
     - `--kimi-text: #FFFFFF`
     - `--kimi-text-muted: #a3a3a3` (zinc-400) or `#CCCCCC`
     - `--kimi-accent: #2196F3` (or keep current blue, ensure it’s used consistently)
     - `--kimi-border: rgba(255,255,255,0.08)` or `#262626`
   - Optionally add a **subtle grid** utility (e.g. `.grid-pattern-kimi`) for hero/sections.

2. **Apply to public surfaces**
   - **Landing:** `LandingPage.jsx` — background `#000` or `#0a0a0a`, headings white, body light gray, accent blue for links/icons/“New” badges.
   - **PublicNav:** Same black bar, white/gray nav links, white or accent for active/CTA.
   - **PublicFooter:** Black background, white “CrucibAI”, gray links, optional blue accent for one key link (e.g. “Documentation”).
   - **Features, Pricing, Templates, Patterns, Learn, Shortcuts, Prompts:** Same palette and type scale.

3. **Typography**
   - Keep **Outfit** for headings and **Inter** for body (already in use), or switch to a single sans-serif (e.g. Inter everywhere) to match Kimi’s uniformity.
   - Enforce **size scale:** hero `text-4xl md:text-6xl` (or larger), section `text-3xl`, card titles `text-lg`/`text-xl`, body `text-base`, nav/footer `text-sm`.

4. **Tailwind**
   - In `tailwind.config.js`, optionally add `kimi` color aliases that map to the same hex values so we use `bg-kimi-bg`, `text-kimi`, `text-kimi-muted`, `accent-kimi` consistently.

**Deliverables:** One source of truth for Kimi-style colors/fonts; all public pages and Layout (sidebar) using that system.

---

## Phase 2: Content Strategy and Structure (Kimi-style, CrucibAI voice)

### 2.1 Kimi’s Content Patterns (What to Mirror)

- **Hero:** One strong headline + one short sentence + single primary CTA (e.g. “Try Kimi K2 & 2.5”). Optional “NEW” badge.
- **“What is X”:** One clear definition paragraph + bullet list of key traits (research, coding, multimodal, agentic, etc.).
- **Key Features:** Section title + list of features, each with **icon + bold title + short description** (e.g. 128K context, MoE, Agentic Intelligence, Multimodal, Personalization).
- **Where / How to use:** “Where Can You Use” / “How to Use” with **accordions or steps** (Web & Mobile, API, Local Deployment, etc.).
- **FAQ:** Many questions with short answers; numbered or with clear headings; expandable (accordion).
- **Footer CTA:** One last headline + subline + two buttons (e.g. “Try … Free” + “View Documentation”).
- **Navigation:** Icons next to nav items (Features, API, App, Pricing, How It Works, GitHub).

### 2.2 CrucibAI Content Plan (Our Strategy, Their Structure)

1. **Landing hero**
   - **Headline:** One line that states value (e.g. “Hello, Welcome to CrucibAI” or “Turn Ideas into Working Software”).
   - **Subline:** One sentence: plan-first AI that builds apps from a single prompt; coding, docs, and iteration in one place.
   - **CTA:** “Try CrucibAI” / “Start building” (existing flow).
   - Optional: “NEW” or “New: Plan-first builds” badge.

2. **“What is CrucibAI” section**
   - One short paragraph: AI that turns prompts into apps; plan-first flow, code generation, attach files/images.
   - Bullets: Research & summarization (docs), Coding & debugging, Multimodal (text + images + files), Plan-first agentic workflow, Templates & patterns.

3. **“Key Features” section**
   - Reuse/refine existing feature list; present with **icon + bold title + 1–2 line description** (Kimi-style layout).
   - Optional: one column with a strong visual or “CrucibAI” wordmark + “Key Features” (two-column like Kimi).

4. **“Where Can You Use CrucibAI”**
   - **Web app** (browser), **API** (if/when we have one), **Export & deploy** (ZIP/GitHub). Each as accordion item with short copy.

5. **“How to Use CrucibAI”**
   - Steps: 1) Describe on landing or in workspace, 2) Get a plan + suggestions (plan-first), 3) Generate and iterate in chat, 4) Export or push to GitHub. Optional “Try on CrucibAI.com” / “Use in workspace” / “Deploy locally” (when applicable).

6. **FAQ**
   - Expand existing FAQ; use **accordions** and clear question headings (e.g. “What is CrucibAI?”, “Is CrucibAI free?”, “What can I build?”, “Design-to-code?”, “How do I get better results?”). Optionally number entries (Kimi-style).

7. **Footer**
   - Headline: e.g. “CrucibAI Is Here to Turn Ideas into Software.”
   - Subline: “Plan, build, and ship with AI. No code required.”
   - Buttons: “Try CrucibAI Free” + “View Documentation” (link to /learn).
   - Copyright + About, Privacy, Terms, Contact (or Get help).

8. **Nav**
   - Add small icons next to: Features, Pricing, Templates, Prompts, How it works, Documentation (or Learn). Optional: GitHub if we have a repo.

**Deliverables:** Copy and structure in `LandingPage.jsx`, `Features.jsx`, and any new “How it works” / “Where to use” sections; accordion components where needed; footer CTA block.

---

## Phase 3: Functional Features from Kimi to Implement in CrucibAI

Below is a **list of Kimi’s software/strategy** and **what we can implement in CrucibAI** (short-term vs. later).

### 3.1 Already Aligned or Partially Done

- **Multimodal input:** We have text + attach files/images on landing and workspace. ✅  
- **Plan-first flow:** We have `POST /api/build/plan` and plan + suggestions in workspace. ✅  
- **Pricing/usage transparency:** Pricing page, Usage in Settings, token balance in sidebar. ✅  
- **Prepay / balance:** Backend checks balance, returns 402, deducts up to balance. ✅  
- **Documentation / Get help:** Links in Settings and footer to Learn, support. ✅  

### 3.2 High-Value Additions (Implement Soon)

| Kimi feature | What to implement in CrucibAI |
|--------------|-------------------------------|
| **Design-to-code** | Screenshot/mockup → code: strengthen image handling and prompts so “upload UI screenshot” yields structured HTML/CSS/React. Backend: ensure images are passed to vision-capable model; frontend: promote “paste screenshot” in landing/workspace. |
| **Agent mode (multi-step)** | Plan-first is a start; extend to explicit “agent mode”: break task into steps, show progress, run tools (e.g. write file, run command), iterate. Backend: orchestration layer; frontend: step-by-step UI. |
| **Structured outputs** | Beyond code: generate README, API docs, user stories, comparison tables (e.g. JSON/Markdown). Dedicated prompts or endpoints for “generate docs from code” / “generate FAQ schema.” |
| **“How it works” + “Where to use”** | Dedicated sections (or pages) with accordions explaining Web app, API, Export; and steps 1–2–3–4. Content only + simple components. |
| **Clear feature explanations** | Key Features section with icons and short descriptions (Phase 2). Optional “CrucibAI vs others” comparison table (like Kimi’s tool comparison). |

### 3.3 Medium-Term (Roadmap)

| Kimi feature | CrucibAI implementation idea |
|--------------|-----------------------------|
| **Long context** | Prefer models with larger context; show “context used” or “max context” in UI if we expose model info. |
| **Personalization** | Remember user preferences (e.g. stack, style) in backend; use in system prompt or project defaults. |
| **API access** | Public API for “prompt → plan” and “prompt → code” so developers can integrate CrucibAI (billing via tokens). |
| **Multiple modes** | “Instant” (fast, short) vs “Plan” (plan-first) vs “Agent” (multi-step) as selectable modes in workspace. |
| **Coding-focused prompts** | Presets: “Explain code,” “Debug this error,” “Generate tests,” “Refactor.” Buttons or prompt library entries. |

### 3.4 Later / Optional

| Kimi feature | CrucibAI implementation idea |
|--------------|-----------------------------|
| **Agent swarm / parallel agents** | Multiple sub-agents for different subtasks (e.g. frontend, backend, tests) running in parallel; requires significant backend orchestration. |
| **Docs/Slides/Sheets-style products** | Dedicated “CrucibAI Docs” or “CrucibAI Slides” (generate docs/decks from prompt). Separate from main “build app” flow. |
| **Local deployment** | Document or support self-hosted/on-prem for enterprises (if ever offered). |
| **GitHub link in nav** | If repo is public, add to PublicNav and footer. |
| **FAQ schema / SEO** | Generate JSON-LD FAQ schema from FAQ content for rich results. |

---

## Approval Checklist

Before implementation, please confirm:

- [ ] **Phase 1:** Approve Kimi-style colors (black, white, gray, blue accent), font hierarchy, and application to all public pages + Layout.
- [ ] **Phase 2:** Approve content structure (hero, What is CrucibAI, Key Features, Where/How to use, FAQ accordions, footer CTA, nav icons).
- [ ] **Phase 3:** Approve which functional items to prioritize (e.g. design-to-code, agent mode, structured outputs, “How it works” / “Where to use” sections).

Once you approve (by phase or in full), implementation can proceed in that order: **Phase 1 → Phase 2 → Phase 3** (with Phase 3 split into quick wins vs. roadmap).

---

## References

- Kimi AI: https://kimik2ai.com/
- Current CrucibAI: `frontend/src/pages/LandingPage.jsx`, `Features.jsx`, `Pricing.jsx`, `PublicNav.jsx`, `PublicFooter.jsx`, `index.css`, `tailwind.config.js`
