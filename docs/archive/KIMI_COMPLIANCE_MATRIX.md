# Kimi-Inspired Implementation — Compliance Matrix

Every item from the Kimi plan and gaps document is listed with implementation location and status.

| # | Feature / Item | Where implemented | Status |
|---|----------------|-------------------|--------|
| **Phase 1: Design** |
| 1 | Kimi-style design tokens (black, white, gray, blue) | `frontend/src/index.css` (--kimi-*), `tailwind.config.js` (colors.kimi, fontSize.kimi-*) | Done |
| 2 | Grid pattern for hero/sections | `index.css` (.grid-pattern-kimi) | Done |
| 3 | Apply to Landing | `LandingPage.jsx` (bg-kimi-bg, text-kimi-text, grid-pattern-kimi, kimi-hero, kimi-section, etc.) | Done |
| 4 | Apply to PublicNav | `PublicNav.jsx` (kimi-bg, kimi-text, kimi-muted, nav icons) | Done |
| 5 | Apply to PublicFooter | `PublicFooter.jsx` (kimi-bg, kimi-muted, CTA block) | Done |
| 6 | Apply to Features, Pricing | `Features.jsx`, `Pricing.jsx` (kimi-bg, kimi-text, kimi-muted, section tags) | Done |
| 7 | Apply to Templates, Patterns, Learn, Shortcuts, Prompts (public) | `TemplatesPublic.jsx`, `PatternsPublic.jsx`, `LearnPublic.jsx`, `ShortcutsPublic.jsx`, `PromptsPublic.jsx` | Done |
| **Phase 2: Content** |
| 8 | Hero with NEW badge | `LandingPage.jsx` (NEW — Plan-first builds & Swarm mode) | Done |
| 9 | Hero headline + subline + CTA | "Hello, Welcome to CrucibAI", subline, "Try CrucibAI free" | Done |
| 10 | "What is CrucibAI" section + bullets | `LandingPage.jsx` (What we do tag, paragraph, 6 bullets) | Done |
| 11 | Key Features (two-column, icon + title + desc) | `LandingPage.jsx` (Benefits tag, CrucibAI Key Features, 5 items) | Done |
| 12 | "Where Can You Use CrucibAI" accordion | `LandingPage.jsx` (whereItems, openWhere state, 3 items) | Done |
| 13 | "How to Use CrucibAI" steps (1–4) | `LandingPage.jsx` (id="how", 4 steps) | Done |
| 14 | FAQ accordion, numbered (12 questions) | `LandingPage.jsx` (faqs expanded, numbered, accordion) | Done |
| 15 | Footer CTA block (headline + Try Free + View Documentation) | `LandingPage.jsx` + `PublicFooter.jsx` | Done |
| 16 | Nav icons (Features, Pricing, How it works, Documentation) | `PublicNav.jsx` (Sparkles, CreditCard, Layout, FileText, HelpCircle, BookOpen) | Done |
| 17 | Section tags (Benefits, How it works, Access, Compare, etc.) | `LandingPage.jsx` (uppercase small tags above sections) | Done |
| 18 | Comparison table "CrucibAI vs Others" | `LandingPage.jsx` (comparisonRows, table) | Done |
| 19 | Use cases section | `LandingPage.jsx` (How is CrucibAI Used in Real-World Applications) | Done |
| 20 | Limitations section | `LandingPage.jsx` (What Are the Limitations) | Done |
| 21 | Roadmap / Future plans | `LandingPage.jsx` (What Are the Future Plans) | Done |
| 22 | "Sign in to save projects and sync" | `LandingPage.jsx` (when !user above chat box) | Done |
| **Phase 3: Function** |
| 23 | Build mode selector (Quick, Plan, Agent, Thinking) | `Workspace.jsx` (buildMode state, 4 buttons) | Done |
| 24 | Design-to-code label when image attached | `Workspace.jsx` ("Design-to-code: we'll generate UI from your screenshot...") | Done |
| 25 | Thinking mode (backend) | `server.py` (ChatMessage.mode, ai_chat + ai_chat_stream use step-by-step system prompt when mode=thinking) | Done |
| 26 | Swarm (build/plan parallel + token multiplier) | `server.py` (BuildPlanRequest.swarm, asyncio.gather(plan, suggestions), SWARM_TOKEN_MULTIPLIER=1.5, balance check) | Done |
| 27 | Pass mode in chat/stream | `Workspace.jsx` (body: { ..., mode: buildMode === 'thinking' ? 'thinking' : undefined }) | Done |
| 28 | Pass swarm in build/plan when Agent mode | `Workspace.jsx` (planRes = axios.post build/plan { prompt, swarm: buildMode === 'agent' }) | Done |
| 29 | Structured output: generate-readme | `server.py` POST /api/ai/generate-readme (GenerateReadmeBody) | Done |
| 30 | Structured output: generate-docs | `server.py` POST /api/ai/generate-docs (GenerateDocsBody) | Done |
| 31 | Structured output: generate-faq-schema | `server.py` POST /api/ai/generate-faq-schema (GenerateFaqSchemaBody, JSON-LD FAQPage) | Done |
| **Pre-existing (verified)** |
| 32 | Plan-first flow | `server.py` POST /api/build/plan, `Workspace.jsx` isBigBuild → plan then build | Done |
| 33 | Image-to-code | `server.py` POST /api/ai/image-to-code, Workspace handleBuild with images | Done |
| 34 | Multimodal input (landing + workspace) | LandingPage + Workspace attach files/images | Done |
| 35 | Pricing page, Usage, token balance | Pricing.jsx, Settings Usage tab, Layout sidebar | Done |
| 36 | Prepay / balance check | server MIN_BALANCE_FOR_LLM_CALL, 402, deduct min(usage, balance) | Done |
| 37 | Documentation / Get help links | Settings Get help, PublicFooter View Documentation, PublicNav Documentation | Done |

All 37 items above are implemented. See KIMI_CROSSWALK.md for Kimi → CrucibAI mapping and KIMI_PROOF_OF_IMPLEMENTATION.md for how to verify each.
