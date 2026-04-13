# 🎨 MANUS-INSPIRED DESIGN SYSTEM

**Version:** 1.0  
**Date:** February 19, 2026  
**Status:** ✅ ACTIVE  
**Philosophy:** High-quality, professional, warm, premium ($100M work)

---

## 🎯 DESIGN PHILOSOPHY

### Core Principles
1. **Warm & Professional** - Light, approachable, premium feel
2. **High Quality** - Everything feels crafted, not basic
3. **3D Depth** - Subtle shadows and layering for dimension
4. **Progressive Disclosure** - Show what matters, hide complexity
5. **Fast Time to Action** - User accomplishes goal in <30 seconds
6. **Ease of Use** - Intuitive, no learning curve

### Inspiration
- **Manus:** Clean, organized, professional
- **Lovable:** Warm, friendly, approachable
- **OpenAI:** Premium, trustworthy, high-quality

---

## 🎨 COLOR PALETTE

### Primary Colors (Warm & Light)
```css
--kimi-bg: #FAFAF8;           /* Warm white background */
--kimi-bg-elevated: #FFFFFF;  /* Pure white for elevated surfaces */
--kimi-bg-card: #F9F8F6;      /* Warm gray for cards */
--kimi-bg-input: #F3F1ED;     /* Warm gray for inputs */
```

### Text Colors (Dark & Readable)
```css
--kimi-text: #1A1A1A;           /* Primary text - almost black */
--kimi-text-muted: #666666;     /* Secondary text - medium gray */
--kimi-text-secondary: #888888; /* Tertiary text - light gray */
```

### Accent Colors
```css
--kimi-accent: #3B82F6;  /* Professional blue */
--success: #10B981;      /* Green for success */
--warning: #999999;      /* Amber for warnings */
--error: #EF4444;        /* Red for errors */
```

### Borders & Dividers
```css
--kimi-border: rgba(0, 0, 0, 0.08);  /* Subtle borders */
--kimi-grid: rgba(0, 0, 0, 0.03);    /* Very subtle grid */
```

### Hex Color Reference
| Name | Hex | Usage |
|------|-----|-------|
| Warm White | #FAFAF8 | Main background |
| Pure White | #FFFFFF | Cards, elevated |
| Warm Gray | #F9F8F6 | Secondary background |
| Light Gray | #F3F1ED | Input fields |
| Dark Text | #1A1A1A | Primary text |
| Medium Gray | #666666 | Secondary text |
| Light Gray | #888888 | Tertiary text |
| Blue | #3B82F6 | Accent, links, buttons |
| Green | #10B981 | Success states |
| Amber | #999999 | Warnings |
| Red | #EF4444 | Errors |

---

## 📐 TYPOGRAPHY

### Font Stack
- **Headings:** Outfit (font-weight: 700)
- **Body:** Inter (font-weight: 400, 500)
- **Code:** JetBrains Mono (font-weight: 400)

### Type Scale
```css
h1: 32px / 40px (Outfit 700)    /* Page titles */
h2: 24px / 32px (Outfit 700)    /* Section titles */
h3: 20px / 28px (Outfit 700)    /* Subsection titles */
h4: 18px / 26px (Outfit 700)    /* Card titles */
body: 16px / 24px (Inter 400)   /* Body text */
small: 14px / 20px (Inter 400)  /* Small text */
code: 14px / 20px (JetBrains)   /* Code blocks */
```

### Letter Spacing
- Headings: -0.02em (tight)
- Body: 0em (normal)
- Code: 0em (normal)

---

## 🎭 SHADOWS & DEPTH

### Shadow System
```css
shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
```

### Elevation Levels
- **Level 0:** No shadow (background)
- **Level 1:** shadow-sm (inputs, subtle elements)
- **Level 2:** shadow-md (cards, panels)
- **Level 3:** shadow-lg (modals, dropdowns)
- **Level 4:** shadow-xl (floating elements)

---

## 🔲 SPACING SYSTEM

### Spacing Scale
```css
xs: 4px    /* Micro spacing */
sm: 8px    /* Small spacing */
md: 16px   /* Medium spacing */
lg: 24px   /* Large spacing */
xl: 32px   /* Extra large spacing */
2xl: 48px  /* 2x extra large spacing */
```

### Common Patterns
- **Card padding:** 24px (lg)
- **Section padding:** 32px (xl)
- **Element gap:** 16px (md)
- **Border radius:** 8px - 12px

---

## 🎨 COMPONENT STYLING

### Buttons
```css
Primary Button:
- Background: #3B82F6
- Text: #FFFFFF
- Padding: 12px 24px
- Border radius: 8px
- Shadow: shadow-md
- Hover: opacity 90%

Secondary Button:
- Background: #F3F1ED
- Text: #1A1A1A
- Padding: 12px 24px
- Border radius: 8px
- Shadow: shadow-sm
- Hover: background #E5E3E0
```

### Cards
```css
- Background: #FFFFFF
- Border: 1px solid rgba(0, 0, 0, 0.08)
- Padding: 24px
- Border radius: 12px
- Shadow: shadow-md
- Hover: shadow-lg
```

### Inputs
```css
- Background: #F3F1ED
- Border: 1px solid rgba(0, 0, 0, 0.08)
- Padding: 12px 16px
- Border radius: 8px
- Text: #1A1A1A
- Focus: border #3B82F6, shadow-md
```

### Dividers
```css
- Color: rgba(0, 0, 0, 0.08)
- Height: 1px
- Margin: 24px 0
```

---

## 📐 LAYOUT STRUCTURE

### 3-Column Layout (Primary)
```
┌─────────────────────────────────────────────────────┐
│ Sidebar (240px) │ Main (flex) │ Panel (320px)       │
│ • Navigation    │ • Content   │ • Preview           │
│ • Quick access  │ • Chat      │ • Code              │
│ • Projects      │ • Editor    │ • Settings          │
└─────────────────────────────────────────────────────┘
```

### Responsive Breakpoints
- **Mobile:** < 640px (single column)
- **Tablet:** 640px - 1024px (2 columns)
- **Desktop:** > 1024px (3 columns)

### Container Widths
- **Max width:** 1400px
- **Sidebar:** 240px (fixed)
- **Main:** flex (responsive)
- **Panel:** 320px (fixed)

---

## 🎬 ANIMATIONS & INTERACTIONS

### Micro-interactions
```css
Hover states:
- Button: opacity 90%, shadow increase
- Card: shadow increase, slight scale
- Link: color change, underline

Focus states:
- Input: border color change, shadow
- Button: ring outline

Active states:
- Navigation: highlight, bold text
- Tab: underline, color change
```

### Transitions
```css
- Duration: 200ms (fast), 300ms (normal)
- Easing: ease-in-out
- Properties: color, background, shadow, transform
```

### Animations
```css
- Fade in: opacity 0 → 1 (300ms)
- Slide up: translateY 20px → 0 (300ms)
- Pulse: subtle glow effect (2s loop)
```

---

## 🔍 ACCESSIBILITY

### Color Contrast
- Text on background: 7:1 (AAA)
- Text on secondary: 4.5:1 (AA)
- Focus indicators: always visible

### Typography
- Minimum font size: 14px
- Line height: 1.5 (24px for 16px text)
- Letter spacing: normal

### Interactive Elements
- Minimum touch target: 44px × 44px
- Focus ring: 2px solid #3B82F6
- Keyboard navigation: fully supported

---

## 📱 RESPONSIVE DESIGN

### Mobile (< 640px)
- Single column layout
- Full-width content
- Sidebar collapses to hamburger
- Touch-friendly buttons (48px+)

### Tablet (640px - 1024px)
- 2-column layout
- Sidebar visible or collapsible
- Optimized touch interactions

### Desktop (> 1024px)
- 3-column layout
- All panels visible
- Mouse/keyboard optimized

---

## ✨ PREMIUM FEEL ELEMENTS

### 3D Depth
- Layered shadows (multiple layers)
- Subtle elevation changes
- Depth through spacing

### Premium Typography
- Generous line height
- Proper letter spacing
- Hierarchy through weight/size

### Micro Details
- Subtle borders
- Refined shadows
- Smooth transitions
- Consistent spacing

### Visual Hierarchy
- Clear primary action
- Secondary actions in menus
- Tertiary actions in dropdowns

---

## 🎯 DESIGN CHECKLIST

Before shipping any component:
- [ ] Uses Manus-inspired color palette
- [ ] Proper typography hierarchy
- [ ] Consistent spacing (md/lg/xl)
- [ ] Appropriate shadows for elevation
- [ ] Responsive design verified
- [ ] Accessibility checked (contrast, focus)
- [ ] Micro-interactions smooth
- [ ] Premium feel achieved
- [ ] Not cluttered or overwhelming
- [ ] Fast time to action

---

## 📋 IMPLEMENTATION GUIDE

### CSS Variables
```css
/* Use these in your components */
background: var(--kimi-bg);
color: var(--kimi-text);
border: 1px solid var(--kimi-border);
accent: var(--kimi-accent);
```

### Tailwind Classes
```css
/* Tailwind integration */
bg-[#FAFAF8]      /* Warm white */
text-[#1A1A1A]    /* Dark text */
border-[#E5E3E0]  /* Subtle border */
shadow-md         /* Medium shadow */
rounded-lg        /* 8px border radius */
```

### Common Patterns
```jsx
/* Card */
<div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
  {content}
</div>

/* Button */
<button className="bg-blue-500 text-white px-6 py-3 rounded-lg shadow-md hover:shadow-lg transition">
  Click me
</button>

/* Input */
<input className="bg-gray-100 border border-gray-200 rounded-lg px-4 py-2 focus:border-blue-500 focus:shadow-md" />
```

---

## 🚀 DEPLOYMENT CHECKLIST

- [ ] All colors updated to Manus palette
- [ ] Typography hierarchy consistent
- [ ] Spacing system applied
- [ ] Shadows and depth verified
- [ ] Responsive design tested
- [ ] Accessibility verified
- [ ] Performance optimized
- [ ] Cross-browser tested
- [ ] Mobile tested
- [ ] Premium feel achieved

---

**Status:** ✅ DESIGN SYSTEM ACTIVE  
**Last Updated:** February 19, 2026  
**Next Review:** After Phase 2 (Layout Architecture)
