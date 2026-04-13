# Kimi Implementation — Full QA Checklist

Use this list to verify end-to-end that the Kimi-inspired implementation is complete and functioning.

---

## Design (Kimi look)

- [ ] **Tokens** — `index.css` has `--kimi-bg`, `--kimi-text`, `--kimi-muted`, `--kimi-accent`. `tailwind.config.js` has `colors.kimi`, `fontSize.kimi-hero` (and other kimi-*).
- [ ] **Landing** — `/` uses black background, white/gray text, blue accents, grid pattern.
- [ ] **Nav** — Icons next to Features, Pricing, Templates, Prompts, How it works, Documentation; Get started / Dashboard.
- [ ] **Footer** — CTA block "CrucibAI Is Here to Turn Ideas into Software" with Try CrucibAI free + View Documentation; links Product / Resources / Legal; © 2026.
- [ ] **Features** — `/features` uses kimi colors and "CrucibAI Features" with feature cards.
- [ ] **Pricing** — `/pricing` uses kimi colors and "Free tier includes credits" copy.
- [ ] **Other public** — `/templates`, `/patterns`, `/learn`, `/shortcuts`, `/prompts` use `bg-kimi-bg` and `grid-pattern-kimi`.

---

## Content (Landing)

- [ ] **Hero** — "NEW — Plan-first builds & Swarm mode" badge; "Hello, Welcome to CrucibAI"; subline about plan-first; "Try CrucibAI free" button.
- [ ] **What is CrucibAI** — Section with paragraph and 6 bullets (research, coding, multimodal, plan-first, templates, 20 agents).
- [ ] **Key Features** — "CrucibAI Key Features" with 5 items (plan-first, 20 agents, design-to-code, multimodal, modes).
- [ ] **Where Can You Use** — Accordion with Web app, API (coming soon), Export & deploy.
- [ ] **How to Use** — 4 steps: Describe, Plan & build, Iterate, Ship.
- [ ] **Comparison table** — "CrucibAI vs Other AI Tools" with at least CrucibAI, Cursor, Manus, ChatGPT.
- [ ] **Use cases** — "How is CrucibAI Used in Real-World Applications?" with 4 bullets.
- [ ] **Limitations** — "What Are the Limitations of CrucibAI?" section.
- [ ] **Roadmap** — "What Are the Future Plans for CrucibAI?" with 4 bullets.
- [ ] **FAQ** — 12 questions, numbered, accordion (expand/collapse).
- [ ] **Footer CTA** — Headline + Try CrucibAI free + View Documentation.
- [ ] **Sign in to sync** — When logged out, "Sign in to save projects and sync across devices" above chat.

---

## Function (Workspace & backend)

- [ ] **Build mode** — In `/app/workspace`, "Build mode:" with Quick, Plan, Agent, Thinking.
- [ ] **Quick** — Mode Quick, submit "Build a todo app" → no plan step, direct build.
- [ ] **Plan** — Mode Plan, submit "Build me a dashboard" → "Planning..." then plan then build.
- [ ] **Agent** — Mode Agent, submit big prompt → plan requested; backend receives `swarm: true` when buildMode === 'agent'.
- [ ] **Thinking** — Mode Thinking, submit a question → backend uses step-by-step prompt (check via network tab: body has `mode: "thinking"`).
- [ ] **Design-to-code label** — Attach image in workspace → "Design-to-code: we'll generate UI from your screenshot or mockup." visible.
- [ ] **Image-to-code flow** — Attach image only (or image + prompt), submit → calls `/ai/image-to-code`, code appears.
- [ ] **Swarm balance** — If balance &lt; MIN_BALANCE * 1.5 and swarm=true, build/plan returns 402.
- [ ] **POST /ai/generate-readme** — Returns `{ "readme": "..." }` markdown.
- [ ] **POST /ai/generate-docs** — Returns `{ "docs": "..." }` markdown.
- [ ] **POST /ai/generate-faq-schema** — Body `{ "faqs": [ {"q":"?","a":"!"} ] }` → returns `{ "schema": { "@context", "@type": "FAQPage", "mainEntity": [...] } }`.

---

## Regression

- [ ] **Landing chat** — Type prompt, submit → redirect to workspace or auth; with image attach → design-to-code path.
- [ ] **Workspace build** — Plan mode + big prompt → plan then build; stream or non-stream completes.
- [ ] **Workspace modify** — After build, type "add a button" → modify runs, code updates.
- [ ] **Token balance** — When balance &lt; MIN_BALANCE, build/chat returns 402 with clear message.
- [ ] **Settings** — Account, General (language, theme), Usage (balance, Pricing link), Get help (Docs, support).
- [ ] **Public nav/footer** — All links (Features, Pricing, Templates, Learn, etc.) work; CTA buttons work.

---

## Sign-off

- [ ] All design items pass.
- [ ] All content items pass.
- [ ] All function items pass.
- [ ] No regressions on landing, workspace, settings, or public pages.

**Date:** _______________  
**Tester:** _______________
