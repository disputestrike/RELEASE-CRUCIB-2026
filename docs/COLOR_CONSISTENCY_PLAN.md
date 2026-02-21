# Color consistency plan — Gray + light gray + black only

**Status: Applied** (global tokens + Credit Center, Export, Docs/Slides, Patterns, Prompt Library, Docs API, Audit Log, Add Payments, Agents). **Latest pass:** Sidebar (task status icons → gray), LearnPanel (orange → gray/black), Workspace, Builder, Settings, Pricing, AuthPage, LandingPage, TutorialsPage, ProjectBuilder, ShareView, Security, PromptsPublic, Privacy, PatternLibrary, ExamplesGallery, EnvPanel, Dmca, Cookies, Blog, Aup. **Still to do (optional):** AgentMonitor, Admin* (AdminUsers, AdminUserProfile, AdminLegal, AdminDashboard, AdminBilling, AdminAnalytics), and some components (ManusComputer, VibeCoding, AdvancedIDEUX, VoiceInput, EverythingSupport, ErrorBoundary, BuildProgress, QualityScore, DeployButton, toast destructive) if you want strict gray everywhere including admin and error states.

**Your palette (Fortune 500 / professional):**
- **Black:** `#1A1A1A` — primary text, primary buttons, primary emphasis
- **Gray (medium):** `#666666` or `#6B7280` — secondary/muted text
- **Light gray:** `#FAFAF8` (page bg), `#F3F1ED` or `#F5F5F4` (inputs, hover), `#FFFFFF` (cards, surfaces)
- **Borders:** `rgba(0, 0, 0, 0.08)` or `#E5E5E5`

**Out of scope:** Orange, green, emerald, amber, blue, red (except minimal for destructive/error if you approve), violet, purple, yellow, teal, cyan.

---

## 1. Global / design tokens

| Location | Issue | Fix |
|----------|--------|-----|
| `frontend/src/index.css` | `--primary`, `--ring`, `--chart-*`, `--destructive` use blue/orange/red/green | Set all to gray/black equivalents (e.g. primary/ring to 0 0% 10%; charts to gray scale; destructive keep only if you want one error color) |
| `frontend/src/styles/ColorShading.css` | `--manus-success`, `--manus-warning`, `--manus-error`, `--manus-info` (green/orange/red/blue) | Replace with gray variants for UI chrome; or keep only one “error” shade as dark gray/black if you approve |
| `frontend/src/styles/PremiumEffects.css` | `.gradient-orange`, orange box-shadows | Use gray/black gradients and `rgba(0,0,0,0.08)` (or similar) for shadows |
| `frontend/src/components/PremiumCard.css` | `gradient-orange`, orange borders | Gray/black only |
| `frontend/src/components/PremiumButton.css` | Orange box-shadows | Black/gray shadows only |
| `frontend/src/components/Sidebar.css` | `box-shadow` with orange tint; `.color-emerald` | Neutral shadow; remove or change `.color-emerald` to gray |
| `frontend/src/components/Layout.css` | `.status-green`, `.status-amber` | Use gray shades (e.g. darker gray = connected, lighter = checking) or keep one muted “success” gray if you approve |
| `frontend/src/components/RightPanel.css` | `.preview-dot.green` | Use gray |
| `frontend/src/pages/Dashboard.css` | Focus ring `rgba(255, 107, 53, …)`; chip hover orange tint | `rgba(0,0,0,0.12)` or gray |
| `frontend/src/pages/Workspace.css` | Orange-tinted backgrounds for states | Light gray only |
| `frontend/src/pages/WorkspaceRedesigned.css` | Orange focus ring | Gray/black ring |
| `frontend/src/components/VoiceWaveform.css` | Comment “orange accent” | Remove; use gray/black if any accent |

---

## 2. Engine Room & app pages (by page)

### Credit Center (`TokenCenter.jsx`)
- **Remove:** Green (`#10B981`, `emerald-600/500`, `green-500/20`, `text-green-400`), yellow (`text-yellow-500`), red (`text-red-400`), multi-color chart array (`COLORS`).
- **Replace:** Buttons → `bg-[#1A1A1A]` / `hover:bg-[#333]`; cards/surfaces → `#FAFAF8` or `#FFFFFF`, borders `rgba(0,0,0,0.08)`; dark panels `#0a0a0a` → use light gray (`#F5F5F4` or `#F3F1ED`) for consistency unless you want one dark card style (then use one gray, e.g. `#2D2D2D`).
- **Charts:** Single gray/black fill (e.g. `#1A1A1A`); axis/labels gray.
- **Status (purchase/bonus/usage):** Use gray shades instead of green/red (e.g. positive = darker gray, negative = lighter gray, or all one gray).
- **Icons:** Zap/yellow → neutral gray or black.

### Export Center (`ExportCenter.jsx`)
- **Remove:** Orange (buttons, borders, focus, spinner, status pills), emerald (icon, focus).
- **Replace:** Primary actions → black/gray; focus → gray ring; spinner → gray; status “completed”/“processing” → gray variants instead of green/orange.

### Docs / Slides / Sheets (`GenerateContent.jsx`)
- **Remove:** All `orange-600`, `orange-500`, `focus:ring-orange-500`, `text-red-600`.
- **Replace:** Tabs and buttons → black/gray; focus → gray; error text → gray or single muted “error” gray if you approve.

### Patterns (`PatternsPublic.jsx`, `PatternLibrary.jsx` if used)
- **Remove:** `orange-500/20`, `text-orange-400`, orange borders.
- **Replace:** Category active state → gray bg + black text; borders gray.

### Templates (`TemplatesPublic.jsx`, `TemplatesGallery.jsx`)
- **Remove:** Any orange/colored accents if present.
- **Replace:** Buttons and hovers → black/gray; keep `#1A1A1A` text.

### Prompt Library (`PromptLibrary.jsx`)
- **Remove:** `bg-orange-600`, `hover:bg-orange-500`, `text-orange-400`, `hover:text-orange-300`.
- **Replace:** Primary buttons → `#1A1A1A`; “Use”/links → gray or black; hover → light gray bg.

### Docs (API) page (`DocsPage.jsx`)
- **Remove:** HTTP method colors (emerald, orange, amber, red); orange icon/buttons/focus/code samples.
- **Replace:** Method badges → gray scale (e.g. one shade for GET, slightly different for POST, etc., all gray); buttons and focus → black/gray; code blocks → gray background, black/gray text; one optional “warning” callout in light gray if needed.

### Audit Log (`AuditLog.jsx`)
- **Remove:** `bg-orange-500`, `hover:bg-orange-600`, `bg-orange-500/20`, `text-orange-400`; success/error pills `green-500/20`, `text-green-400`, `red-500/20`, `text-red-400`.
- **Replace:** Buttons → black/gray; status pills → gray variants (e.g. “success” = darker gray, “failed” = lighter gray, or all same gray).

### Add Payments (`PaymentsWizard.jsx`)
- **Remove:** `bg-green-500/20`, `text-green-400`, `bg-orange-500/20`, `text-orange-400`, orange hover.
- **Replace:** Success state → light gray + black icon; CTAs → black/gray buttons; hover → gray.

### Shortcuts (`ShortcutCheatsheet.jsx`, `ShortcutsPublic.jsx`)
- **Audit:** You said Shortcuts has “messed up colors”; current grep showed mostly `#1A1A1A`. Scan for any remaining Tailwind color classes (orange, blue, etc.) and replace with gray/black.

### Agents (`AgentsPage.jsx`)
- **Remove:** `text-amber-400` (Zap icon), `bg-orange-600`, `hover:bg-orange-500`, `hover:border-orange-500/50`, `text-orange-400`, `text-green-400`, `text-red-400`, `text-amber-400` (status), modal orange tabs/buttons.
- **Replace:** All CTAs and tabs → black/gray; hover borders → gray; status (success/failed/pending) → gray shades; error text → gray or one muted tone.

### Benchmarks (`Benchmarks.jsx`)
- **No change** (you confirmed this page already uses the right colors).

---

## 3. Hover and focus (all pages)

- **Buttons:** `hover:bg-[#333]` or `hover:opacity-90` on black; on light buttons `hover:bg-[#F3F1ED]` (or similar light gray).
- **Links / secondary actions:** `hover:text-[#1A1A1A]` and/or `hover:underline`; no orange/blue/green.
- **Focus rings:** `focus:ring-2 focus:ring-gray-300` or `box-shadow: 0 0 0 3px rgba(0,0,0,0.08)`; remove all orange/blue rings.
- **Cards / rows:** `hover:bg-[#F5F5F4]` or `hover:border-[#E5E5E5]`; no colored borders or backgrounds.

---

## 4. Fonts

- **Primary:** Already using DM Sans in Dashboard/Sidebar — use **DM Sans** app-wide for UI (headings and body).
- **Consistency:** Replace any page using only generic `sans-serif` or other fonts with `font-family: 'DM Sans', sans-serif` (and keep Inter/Outfit/JetBrains only where you explicitly want code or special typography).

---

## 5. Icons to flag for your approval

These currently use color (or are “AI-ish”) and might need replacing or neutral styling:

- **Credit Center:** Zap (yellow) next to credits — suggest gray or black Zap, or different icon.
- **Export Center:** Rocket (emerald) — suggest gray/black Rocket or DocumentDown.
- **Agents:** Zap (amber) in header — suggest gray Zap or Bot icon in gray/black.
- **Docs page:** BookOpen (orange) — suggest gray/black.
- **Payments:** CreditCard in green success box — suggest same icon in gray.
- **Audit Log / Export / others:** Any Check, X, or status icons in green/red — suggest gray variants or one neutral “success” gray.

If you tell us “keep icon, only change color” we’ll only change color to gray/black; if you prefer different icons we can suggest alternatives per screen.

---

## 6. Implementation order (recommended)

1. **Global tokens** — `index.css`, `ColorShading.css`, `PremiumEffects.css`, `PremiumCard.css`, `PremiumButton.css`, `Sidebar.css`, `Layout.css`, `RightPanel.css`, `Dashboard.css`, `Workspace.css`, `WorkspaceRedesigned.css`, `VoiceWaveform.css`.
2. **Engine Room pages** — TokenCenter → ExportCenter → GenerateContent → Patterns → Templates → PromptLibrary → DocsPage → AuditLog → PaymentsWizard → Shortcuts → Agents.
3. **Pass 2** — Hover/focus audit on all touched pages; font pass (DM Sans) where still missing.
4. **Icons** — After colors are fixed, replace or restyle the flagged icons per your approval.

---

## 7. Summary

- **Colors:** Only black (`#1A1A1A`), gray (`#666666` / `#6B7280`), light gray (`#FAFAF8`, `#F3F1ED`, `#F5F5F4`), white (`#FFFFFF`), and borders `rgba(0,0,0,0.08)`.
- **No:** Orange, green, emerald, amber, blue, red (unless you approve one error color), violet, purple, yellow, teal, cyan in UI chrome.
- **Hover/focus:** Gray and black only.
- **Fonts:** DM Sans as default; consistent across app.
- **Icons:** Listed above for your approval before changing.

Once you confirm this plan (and any choices for “one error color” or “dark card” gray), we can apply it page by page and then do the icon pass.
