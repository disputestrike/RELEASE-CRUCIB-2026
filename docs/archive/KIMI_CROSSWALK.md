# Kimi → CrucibAI Crosswalk

Mapping from Kimi AI website/product elements to CrucibAI implementation.

| Kimi element | CrucibAI implementation |
|--------------|-------------------------|
| **Design** |
| Deep black background | `--kimi-bg: #000000`, `bg-kimi-bg`, `grid-pattern-kimi` on public pages |
| White headings, gray body | `text-kimi-text`, `text-kimi-muted`, `text-kimi-secondary`; typography scale (kimi-hero, kimi-section, kimi-card, kimi-body, kimi-nav) |
| Vibrant blue accent | `--kimi-accent: #2196f3`, links and icons |
| Subtle grid overlay | `.grid-pattern-kimi` in index.css |
| Clean sans-serif, hierarchy | Outfit (headings) + Inter (body); Tailwind kimi font sizes |
| **Content structure** |
| "Hello, Welcome to Kimi AI" | "Hello, Welcome to CrucibAI" (LandingPage hero) |
| NEW badge (Kimi K2.5) | "NEW — Plan-first builds & Swarm mode" badge |
| "What is Kimi AI" + bullets | "What is CrucibAI?" section + 6 bullets (research, coding, multimodal, plan-first, templates, 20 agents) |
| Key Features (icon + title + desc) | "CrucibAI Key Features" two-column, 5 items (plan-first, 20 agents, design-to-code, multimodal, modes) |
| Where Can You Use (accordion) | "Where Can You Use CrucibAI?" accordion (Web app, API coming soon, Export & deploy) |
| How to Use (steps) | "How to Use CrucibAI" 4 steps (Describe, Plan & build, Iterate, Ship) |
| FAQ (many, numbered) | 12 FAQ items, numbered, accordion |
| Footer CTA (Try + View Documentation) | "CrucibAI Is Here to Turn Ideas into Software" + Try CrucibAI free + View Documentation (Landing + PublicFooter) |
| Nav with icons | PublicNav: Features (Sparkles), Pricing (CreditCard), Templates (Layout), Prompts (FileText), How it works (HelpCircle), Documentation (BookOpen) |
| Comparison table (vs tools) | "CrucibAI vs Other AI Tools" table (CrucibAI, Cursor, Manus, ChatGPT) |
| Benefits / section tags | "What we do", "Benefits", "Access", "How it works", "Compare", "Use cases", "Transparency", "Roadmap", "FAQ" |
| **Functionality** |
| Instant / Thinking / Agent / Swarm modes | Build mode: Quick (no plan), Plan (plan then build), Agent (plan + swarm when big), Thinking (step-by-step system prompt in chat) |
| Design-to-code (screenshot → code) | POST /ai/image-to-code; Workspace + Landing attach image → "Design-to-code" label and image-to-code flow |
| Plan-first | POST /build/plan; Workspace isBigBuild → plan then build |
| Swarm (parallel) | build/plan?swarm=true runs plan and suggestions in parallel (asyncio.gather); SWARM_TOKEN_MULTIPLIER 1.5 so users pay more |
| Thinking (deeper reasoning) | ChatMessage.mode=thinking → system prompt "Think step by step..." in POST /ai/chat and /ai/chat/stream |
| Structured outputs (docs, etc.) | POST /ai/generate-readme, /ai/generate-docs, /ai/generate-faq-schema |
| Free credits / tier messaging | Pricing copy "Free tier includes credits"; FAQ "Is CrucibAI free to use?" |
| Limitations / Future plans | Landing sections "What Are the Limitations" and "What Are the Future Plans for CrucibAI?" |
| Use cases | "How is CrucibAI Used in Real-World Applications?" (startups, internal tools, agencies, education) |
| Sign in to sync | "Sign in to save projects and sync across devices" on landing when not logged in |
