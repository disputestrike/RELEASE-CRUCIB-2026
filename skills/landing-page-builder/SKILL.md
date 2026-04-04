---
name: landing-page-builder
description: Build a high-conversion marketing landing page with hero, features, pricing, testimonials, FAQ, and email waitlist. Use when the user wants a landing page, marketing page, product page, waitlist page, or promotional site. Triggers on phrases like "build a landing page", "create a product page", "I need a marketing site", "build a waitlist page", "create a hero + features page".
metadata:
  version: '1.0'
  category: build
  icon: 🏠
  color: '#06b6d4'
---

# Landing Page Builder

## When to Use This Skill

Apply this skill when the user wants a marketing or product page:

- "Build me a landing page for X"
- "Create a product marketing page"
- "I need a waitlist signup page"
- "Build a page that explains my product and captures emails"
- Any request for a marketing site, product page, or conversion-focused page

## What This Skill Builds

A high-conversion, design-quality landing page:

**Page Sections (in order)**
1. **Navigation** — logo left, links center, CTA right, mobile hamburger
2. **Hero** — bold headline, subheadline, 2 CTA buttons, product mockup/illustration, social proof badge
3. **Social Proof** — logo strip of 4-6 trusted brands/customers
4. **Features Grid** — 6 cards with icon, title, description (from lucide-react icons)
5. **How It Works** — 3-step numbered process (horizontal or vertical)
6. **Testimonials** — 3 testimonial cards with avatar, name, role, company, quote, star rating
7. **Pricing** — 3-tier table (Free/Pro/Enterprise) with toggle (monthly/annual), feature checkmarks
8. **FAQ** — accordion with 6-8 questions, smooth animation
9. **Final CTA** — full-width banner with email input and submit button
10. **Footer** — 4-column grid with links, social icons, copyright

**Design Quality**
- Framer Motion animations (fade-in on scroll, staggered cards)
- Tailwind CSS with consistent design tokens
- Clean sans-serif typography (Inter via @fontsource)
- Gradient backgrounds on hero (subtle, not garish)
- Card hover effects with subtle shadow lift
- Fully responsive (mobile-first)
- Dark mode support via `prefers-color-scheme`

**Conversion Elements**
- Email waitlist captures to API endpoint
- CTA buttons in 3 places (hero, middle, bottom)
- Social proof numbers (users, reviews, uptime)
- Urgency/scarcity messaging where appropriate

**Technical**
- Single-file React component (or multi-section components)
- MemoryRouter compatible for Sandpack preview
- No external images (use emoji, SVGs, or Tailwind gradients)
- SEO-ready meta tags in HTML template
- Fast load (no heavy libraries)

## Instructions

1. **Extract the product** — name, value proposition, target audience, key features, pricing, social proof

2. **Generate all content first** — headline, subheadline, 6 feature descriptions, 3 testimonials, pricing tiers, FAQ questions — make it specific to the product (no Lorem ipsum)

3. **Build in 2 passes**:
   - Pass 1: Config + all content data in `src/const.ts` with TypeScript interfaces
   - Pass 2: All section components + App.tsx composing them in order

4. **Headline formula**: "[Verb] [outcome] for [audience] without [pain]"
   - ✅ "Launch your SaaS in a weekend, not a month"
   - ❌ "The best platform for all your needs"

5. **Animation rules**:
   - Hero: fade in + slide up on load
   - Feature cards: staggered fade in on scroll (`whileInView`)
   - Section transitions: subtle opacity (no jarring movements)
   - CTA button: scale on hover

## Example Input → Output

Input: "Landing page for Stackr — a tool that helps developers track their side project portfolio, showcase their work, and find collaborators"

Output includes:
- Headline: "Your side projects deserve to be seen"
- Features: Project showcase, collaboration finder, activity tracker, embed widget, GitHub sync, public profile
- Testimonials: 3 developer personas with realistic quotes
- Pricing: Free (3 projects), Pro ($9/mo, unlimited), Team ($25/mo, team features)
- `/src/const.ts` — all content data typed
- `/src/App.tsx` — full single-page composition
- `/src/components/` — Nav, Hero, Features, Pricing, FAQ, Footer
