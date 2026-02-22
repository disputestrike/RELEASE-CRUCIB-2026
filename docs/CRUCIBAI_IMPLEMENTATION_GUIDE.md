# CRUCIBAI WEBSITE IMPLEMENTATION GUIDE
## "Inevitable AI" Rebrand - Complete Technical Specification

**Version:** 1.0  
**Status:** Ready for Implementation  
**Date:** February 16, 2026

---

## OVERVIEW

This guide provides the complete technical specification for implementing the CrucibAI "Inevitable AI" rebrand on the website. It includes:

- ✅ Brand messaging framework
- ✅ Typography system updates
- ✅ Layout patterns (Microsoft Edge-inspired)
- ✅ Image integration (6 hero images uploaded to CDN)
- ✅ Component structure
- ✅ Content mapping
- ✅ Implementation checklist

---

## PART 1: TYPOGRAPHY SYSTEM

### Current State
- Generic sizing
- Standard hierarchy
- Limited visual impact

### Target State (Microsoft Edge-Inspired)
- **Font Family:** Segoe UI (fallback: system fonts)
- **Headlines:** 48-56px, weight 700-800, line-height 1.2-1.3
- **Subheadings:** 32-40px, weight 600, line-height 1.3-1.4
- **Body Text:** 16-18px, weight 400, line-height 1.5-1.6
- **Labels:** 14-16px, weight 500, line-height 1.5
- **Letter Spacing:** Generous (0.5px-1px on headlines)

### CSS Updates Required

```css
/* Add to client/src/index.css */

@import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;500;600;700;800&display=swap');

:root {
  --font-sans: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
  
  /* Typography scale */
  --text-xs: 12px;
  --text-sm: 14px;
  --text-base: 16px;
  --text-lg: 18px;
  --text-xl: 24px;
  --text-2xl: 32px;
  --text-3xl: 40px;
  --text-4xl: 48px;
  --text-5xl: 56px;
  
  /* Line heights */
  --leading-tight: 1.2;
  --leading-normal: 1.5;
  --leading-relaxed: 1.6;
  
  /* Letter spacing */
  --tracking-tight: -0.5px;
  --tracking-normal: 0px;
  --tracking-wide: 0.5px;
  --tracking-wider: 1px;
}

body {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
}

/* Heading styles */
h1 {
  font-size: var(--text-5xl);
  font-weight: 700;
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-wide);
  margin-bottom: 1.5rem;
}

h2 {
  font-size: var(--text-4xl);
  font-weight: 700;
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-wide);
  margin-bottom: 1.25rem;
}

h3 {
  font-size: var(--text-3xl);
  font-weight: 600;
  line-height: var(--leading-normal);
  letter-spacing: var(--tracking-normal);
  margin-bottom: 1rem;
}

h4 {
  font-size: var(--text-2xl);
  font-weight: 600;
  line-height: var(--leading-normal);
  margin-bottom: 0.75rem;
}

p {
  font-size: var(--text-lg);
  line-height: var(--leading-relaxed);
  margin-bottom: 1rem;
}

small, .text-sm {
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}
```

---

## PART 2: COLOR SYSTEM

### Brand Colors

| Color | Hex | Usage | OKLCH |
|-------|-----|-------|-------|
| **Background** | #0A0E27 | Main background | oklch(0.08 0.01 280) |
| **Surface** | #1A1F3A | Cards, containers | oklch(0.15 0.02 280) |
| **Text Primary** | #FFFFFF | Headlines, main text | oklch(1 0 0) |
| **Text Secondary** | #B0B8D4 | Subtext, metadata | oklch(0.72 0.01 280) |
| **Accent Primary** | #6366F1 | CTAs, highlights | oklch(0.55 0.25 280) |
| **Accent Secondary** | #8B5CF6 | Secondary actions | oklch(0.60 0.25 280) |
| **Success** | #10B981 | Success states | oklch(0.60 0.20 160) |
| **Warning** | #999999 | Warnings | oklch(0.65 0.20 50) |
| **Error** | #EF4444 | Errors | oklch(0.55 0.25 20) |

### CSS Updates

```css
:root {
  /* Brand colors */
  --color-bg-primary: #0A0E27;
  --color-bg-surface: #1A1F3A;
  --color-text-primary: #FFFFFF;
  --color-text-secondary: #B0B8D4;
  --color-accent-primary: #6366F1;
  --color-accent-secondary: #8B5CF6;
  --color-success: #10B981;
  --color-warning: #999999;
  --color-error: #EF4444;
}

.dark {
  --background: var(--color-bg-primary);
  --foreground: var(--color-text-primary);
  --card: var(--color-bg-surface);
  --card-foreground: var(--color-text-primary);
  --accent: var(--color-accent-primary);
  --accent-foreground: var(--color-text-primary);
}
```

---

## PART 3: LAYOUT PATTERNS (Microsoft Edge-Inspired)

### Pattern 1: Hero Section (50/50 Text-Image Split)

```jsx
// client/src/components/HeroSection.tsx

export function HeroSection() {
  return (
    <section className="py-20 bg-background">
      <div className="container">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          {/* Text Left */}
          <div className="flex flex-col justify-center">
            <h1 className="text-5xl font-bold leading-tight mb-6 text-foreground">
              Inevitable AI
            </h1>
            <p className="text-xl text-text-secondary mb-8 leading-relaxed">
              Intelligence that doesn't just act. Intelligence that guarantees.
            </p>
            <p className="text-lg text-text-secondary mb-8 leading-relaxed">
              Describe your vision. Watch it become inevitable.
            </p>
            <div className="flex gap-4">
              <button className="px-8 py-3 bg-accent-primary text-white rounded-lg font-semibold hover:opacity-90">
                Make It Inevitable
              </button>
              <button className="px-8 py-3 border border-accent-primary text-accent-primary rounded-lg font-semibold hover:bg-accent-primary/10">
                Learn More
              </button>
            </div>
          </div>

          {/* Image Right */}
          <div className="flex justify-center">
            <img
              src="https://files.manuscdn.com/user_upload_by_module/session_file/310519663280407830/fDtpUwJzwBybukaq.png"
              alt="AI Code Generation"
              className="rounded-2xl shadow-2xl w-full h-auto"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
```

### Pattern 2: Feature Grid (3x3 or 4x3)

```jsx
// client/src/components/FeatureGrid.tsx

const agents = [
  { id: 1, name: 'Frontend Specialist', icon: '🎨', description: 'React, Vue, Angular' },
  { id: 2, name: 'Backend Specialist', icon: '⚙️', description: 'Node, Python, Go' },
  { id: 3, name: 'Database Specialist', icon: '🗄️', description: 'PostgreSQL, MongoDB' },
  // ... 112 more agents
];

export function FeatureGrid() {
  return (
    <section className="py-20 bg-background">
      <div className="container">
        <h2 className="text-4xl font-bold mb-4 text-foreground">
          115 Specialized Agents
        </h2>
        <p className="text-lg text-text-secondary mb-12">
          Infrastructure-grade orchestration at application scale.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {agents.map(agent => (
            <div
              key={agent.id}
              className="p-6 bg-card rounded-xl border border-border hover:border-accent-primary transition-colors"
            >
              <div className="text-4xl mb-4">{agent.icon}</div>
              <h3 className="text-lg font-semibold mb-2 text-foreground">
                {agent.name}
              </h3>
              <p className="text-sm text-text-secondary">
                {agent.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
```

### Pattern 3: Text Left + Image Right (Alternating)

```jsx
// client/src/components/ValueProposition.tsx

export function ValueProposition() {
  const propositions = [
    {
      audience: 'Solo Developers',
      benefit: 'Your idea → Deployed app (72 hours, not 6 months)',
      image: 'https://files.manuscdn.com/user_upload_by_module/session_file/310519663280407830/jkBRhMwLwnLQqEAD.png',
    },
    {
      audience: 'Startups',
      benefit: 'Your MVP → Market validation (weeks, not quarters)',
      image: 'https://files.manuscdn.com/user_upload_by_module/session_file/310519663280407830/YAlIGIjbIasgUKPy.png',
    },
    {
      audience: 'Enterprises',
      benefit: 'Your vision → Production reality (full visibility, zero risk)',
      image: 'https://files.manuscdn.com/user_upload_by_module/session_file/310519663280407830/mvcjYRFGkRTvPwhD.png',
    },
  ];

  return (
    <section className="py-20 bg-background">
      <div className="container">
        <h2 className="text-4xl font-bold mb-12 text-foreground">
          What This Means for You
        </h2>

        {propositions.map((prop, idx) => (
          <div
            key={idx}
            className={`grid grid-cols-1 lg:grid-cols-2 gap-12 items-center mb-20 ${
              idx % 2 === 1 ? 'lg:grid-flow-dense' : ''
            }`}
          >
            <div className={idx % 2 === 1 ? 'lg:col-start-2' : ''}>
              <h3 className="text-3xl font-bold mb-4 text-foreground">
                {prop.audience}
              </h3>
              <p className="text-xl text-text-secondary leading-relaxed">
                {prop.benefit}
              </p>
            </div>

            <div className={idx % 2 === 1 ? 'lg:col-start-1 lg:row-start-1' : ''}>
              <img
                src={prop.image}
                alt={prop.audience}
                className="rounded-2xl shadow-2xl w-full h-auto"
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
```

### Pattern 4: Proof Section (Metrics Display)

```jsx
// client/src/components/ProofSection.tsx

export function ProofSection() {
  const metrics = [
    { label: 'Specialized Agents', value: '115', icon: '🤖' },
    { label: 'Success Rate', value: '99.2%', icon: '✅' },
    { label: 'Time to Delivery', value: '72 hrs', icon: '⚡' },
    { label: 'Transparency', value: '100%', icon: '👁️' },
  ];

  return (
    <section className="py-20 bg-card">
      <div className="container">
        <h2 className="text-4xl font-bold mb-4 text-foreground text-center">
          The Proof
        </h2>
        <p className="text-lg text-text-secondary text-center mb-12">
          Not promises. Physics.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {metrics.map((metric, idx) => (
            <div key={idx} className="text-center">
              <div className="text-5xl mb-4">{metric.icon}</div>
              <div className="text-4xl font-bold text-accent-primary mb-2">
                {metric.value}
              </div>
              <p className="text-text-secondary">{metric.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
```

### Pattern 5: Evolution Timeline

```jsx
// client/src/components/EvolutionSection.tsx

export function EvolutionSection() {
  return (
    <section className="py-20 bg-background">
      <div className="container">
        <h2 className="text-4xl font-bold mb-12 text-foreground text-center">
          The Evolution
        </h2>

        <img
          src="https://files.manuscdn.com/user_upload_by_module/session_file/310519663280407830/xWBngfMecVgztKYO.png"
          alt="Evolution of AI"
          className="rounded-2xl shadow-2xl w-full h-auto mb-8"
        />

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 text-center">
          <div>
            <h3 className="text-xl font-bold text-foreground mb-2">ChatGPT</h3>
            <p className="text-text-secondary">AI that thinks</p>
          </div>
          <div>
            <h3 className="text-xl font-bold text-foreground mb-2">Cursor</h3>
            <p className="text-text-secondary">AI that assists</p>
          </div>
          <div>
            <h3 className="text-xl font-bold text-foreground mb-2">Manus</h3>
            <p className="text-text-secondary">AI that acts</p>
          </div>
          <div>
            <h3 className="text-xl font-bold text-accent-primary mb-2">CrucibAI</h3>
            <p className="text-text-secondary">AI that guarantees</p>
          </div>
        </div>
      </div>
    </section>
  );
}
```

---

## PART 4: MESSAGING CONTENT MAP

### Homepage Sections

| Section | Headline | Subheadline | CTA | Image |
|---------|----------|-------------|-----|-------|
| **Hero** | Inevitable AI | Intelligence that doesn't just act. Intelligence that guarantees. | Make It Inevitable | Hero 1: AI Code Generation |
| **Proof** | The Proof | 115 agents, 99.2% success, 72 hours, full transparency | N/A | N/A (Metrics display) |
| **Value Props** | What This Means for You | Outcome-focused benefits | Explore Use Cases | Hero 2, 3, 4 (alternating) |
| **Architecture** | The Architecture | Infrastructure-grade AI at application scale | Learn More | Hero 4: Enterprise Scale |
| **Evolution** | The Evolution | ChatGPT → Cursor → Manus → CrucibAI | Start Free Trial | Hero 6: Evolution Timeline |
| **CTA** | Ready to Make Your Ideas Inevitable? | Join developers and enterprises | Get Started | N/A |

---

## PART 5: IMAGE INTEGRATION

### CDN URLs (Ready to Use)

```javascript
const heroImages = {
  aiCodeGeneration: 'https://files.manuscdn.com/user_upload_by_module/session_file/310519663280407830/fDtpUwJzwBybukaq.png',
  teamCollaboration: 'https://files.manuscdn.com/user_upload_by_module/session_file/310519663280407830/YAlIGIjbIasgUKPy.png',
  developerWorkflow: 'https://files.manuscdn.com/user_upload_by_module/session_file/310519663280407830/jkBRhMwLwnLQqEAD.png',
  enterpriseScale: 'https://files.manuscdn.com/user_upload_by_module/session_file/310519663280407830/mvcjYRFGkRTvPwhD.png',
  speedCertainty: 'https://files.manuscdn.com/user_upload_by_module/session_file/310519663280407830/kNZJkgJjOOJjIfZi.png',
  evolutionAI: 'https://files.manuscdn.com/user_upload_by_module/session_file/310519663280407830/xWBngfMecVgztKYO.png',
};
```

### Image Styling

```css
/* Image styling for consistency */
img {
  border-radius: 1rem; /* 16px rounded corners */
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  max-width: 100%;
  height: auto;
  display: block;
}

/* Responsive images */
@media (max-width: 768px) {
  img {
    border-radius: 0.75rem; /* 12px on mobile */
  }
}
```

---

## PART 6: IMPLEMENTATION CHECKLIST

### Phase 1: Typography & Colors (Day 1)

- [ ] Update `client/src/index.css` with typography system
- [ ] Add Segoe UI font import
- [ ] Update color variables (dark theme)
- [ ] Test typography on all pages
- [ ] Verify contrast and readability

### Phase 2: Create Components (Day 2)

- [ ] Create `HeroSection.tsx` component
- [ ] Create `FeatureGrid.tsx` component
- [ ] Create `ValueProposition.tsx` component
- [ ] Create `ProofSection.tsx` component
- [ ] Create `EvolutionSection.tsx` component
- [ ] Create `CTASection.tsx` component

### Phase 3: Update Home Page (Day 2)

- [ ] Replace `Home.tsx` with new content
- [ ] Integrate all components
- [ ] Add hero images (CDN URLs)
- [ ] Test responsive design
- [ ] Verify all CTAs work

### Phase 4: Testing & QA (Day 3)

- [ ] Test on desktop (1920px, 1440px, 1024px)
- [ ] Test on tablet (768px)
- [ ] Test on mobile (375px, 414px)
- [ ] Verify image loading (CDN)
- [ ] Check performance (Lighthouse)
- [ ] Validate accessibility (a11y)
- [ ] Test all interactive elements

### Phase 5: Launch (Day 3)

- [ ] Deploy to production
- [ ] Verify live site
- [ ] Monitor performance
- [ ] Collect user feedback

---

## PART 7: DEPLOYMENT NOTES

### Before Deploying

1. ✅ All images uploaded to CDN (6/6 complete)
2. ⏳ Components created and tested
3. ⏳ Home page updated with new content
4. ⏳ Typography and colors applied globally
5. ⏳ Responsive design verified
6. ⏳ Performance optimized

### Deployment Command

```bash
# From /home/ubuntu/crucibai-frontend-v2
pnpm run build
pnpm run deploy
```

### Rollback Plan

If issues occur:
```bash
git revert HEAD
pnpm run build
pnpm run deploy
```

---

## NEXT STEPS

1. **Approve this implementation guide**
2. **I will update `client/src/index.css`** with typography and colors
3. **I will create all React components** with the layout patterns
4. **I will update `Home.tsx`** with the new content
5. **I will show you the LIVE preview** for feedback
6. **You provide feedback** (changes, adjustments, approvals)
7. **I will iterate** until perfect
8. **Deploy to production**

---

*Implementation Guide | Version 1.0 | Status: Ready for Execution*
