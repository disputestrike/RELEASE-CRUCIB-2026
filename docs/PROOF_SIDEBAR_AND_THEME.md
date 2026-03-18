# Proof: Sidebar (Settings + Engine/Credits) & Theme (Black / White)

**Date:** Implemented per user approval.  
**Summary:** Settings removed from sidebar footer; only Engine Room + Credits in footer. Guest (collapsed or expanded) opens account dropdown with Settings, Credits & Billing, Upgrade, Log out. Dark theme has no white; light theme is all white with clear borders and legible text.

---

## 1. Settings removed from sidebar footer

| Change | File | Proof |
|--------|------|--------|
| Removed standalone "Settings" link from sidebar bottom | `frontend/src/components/Sidebar.jsx` | Bottom section now contains only **Engine Room** (toggle + items) and **Credits** (link with count). No `<Link to="/app/settings" className="sidebar-settings-link">` in `.sidebar-bottom`. |
| Removed Settings icon from collapsed strip | `frontend/src/components/Sidebar.jsx` | Collapsed strip has: Expand, New Task, New Project, Agents, Search, History, Engine Room, **Credits**, **Account** (Guest). No Settings icon. |
| Removed Settings-related CSS | `frontend/src/components/Sidebar.css` | `.sidebar-settings-link`, `.sidebar-settings-icon`, `.sidebar-settings-label` removed. Replaced by `.sidebar-collapsed-account-wrap`, `.sidebar-account-menu--dropup`, `.sidebar-account-menu-divider`. |

**Result:** Footer shows only **Engine Room** and **Credits**. Settings is only in the **Guest** account dropdown.

---

## 2. Guest opens account dropdown (expanded and collapsed)

| Change | File | Proof |
|--------|------|--------|
| Expanded: account trigger in footer unchanged | `frontend/src/components/Sidebar.jsx` | `.sidebar-footer` still has the account button and `.sidebar-account-menu` with Settings, Credits & Billing, Upgrade plan, Log out. |
| Collapsed: Guest icon opens same menu (drop-up) | `frontend/src/components/Sidebar.jsx` | In `.sidebar-collapsed-bottom`, the Account button uses `onClick={() => setAccountMenuOpen((o) => !o)}` and does **not** call `onToggleSidebar`. When `accountMenuOpen` is true, `.sidebar-account-menu.sidebar-account-menu--dropup` is rendered above the avatar with the same links: Settings, Credits & Billing, Upgrade plan, Log out. |
| Drop-up positioning | `frontend/src/components/Sidebar.css` | `.sidebar-account-menu--dropup` has `position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%); margin-bottom: 6px; min-width: 200px;`. |
| Outside click closes menu (expanded and collapsed) | `frontend/src/components/Sidebar.jsx` | `collapsedAccountRef` added and used on `.sidebar-collapsed-account-wrap`. `useEffect` close handler treats both `accountMenuRef.current` and `collapsedAccountRef.current` as “inside”, so clicking outside either closes the menu. |

**Result:** Clicking Guest (expanded or collapsed) opens the same account menu. Collapsed state shows it as a drop-up above the avatar. Settings, Credits & Billing, Upgrade, Log out are all in that menu.

---

## 3. Dark theme: no white

| Change | File | Proof |
|--------|------|--------|
| Credit Center uses theme variables | `frontend/src/pages/TokenCenter.jsx` | Root has class `credit-center`. Balance card, “Need more?” card, referral box, tabs, history section, usage section use `style={{ background: 'var(--theme-surface)', borderColor: 'var(--theme-border)', color: 'var(--theme-text)' }}` or `var(--theme-muted)`. No hardcoded `#F5F5F4`, `gray-200`, or white. |
| TokenCenter.css dark overrides | `frontend/src/pages/TokenCenter.css` | `[data-theme="dark"] .credit-center` overrides cards/sections, muted text, headings, inputs, and light backgrounds (e.g. `.bg-\[\#F5F5F4\]`) to use `var(--theme-surface)`, `var(--theme-border)`, `var(--theme-text)`, `var(--theme-muted)`. |
| Global theme (unchanged) | `frontend/src/index.css` | `[data-theme="dark"]` sets `--theme-bg: #0a0a0a`, `--theme-surface: #111113`, etc. `body` uses `var(--theme-bg)` and `var(--theme-text)`. |

**Result:** With black/dark toggle, Credit Center and app use dark backgrounds and theme colors; no white or light-gray surfaces.

---

## 4. Light theme: all white, borders, legible text

| Change | File | Proof |
|--------|------|--------|
| Light theme variables | `frontend/src/index.css` | `[data-theme="light"]` sets `--theme-bg: #FFFFFF`, `--theme-surface: #FFFFFF`, `--theme-surface2: #F5F5F4`, `--theme-border: rgba(0,0,0,0.12)`, `--theme-text: #1A1A1A`, `--theme-muted: #666666`. |
| Credit Center in light mode | `frontend/src/pages/TokenCenter.jsx` + `TokenCenter.css` | Same `var(--theme-*)` used in light mode; no extra black. `[data-theme="light"] .credit-center` in CSS ensures cards/sections use `var(--theme-surface2)` and borders `var(--theme-border)` so layout stays white with visible borders and text. |

**Result:** With white/light toggle, UI is white with clear borders and readable text.

---

## 5. File change list (proof of implementation)

| File | Changes |
|------|---------|
| `frontend/src/components/Sidebar.jsx` | Removed Settings link from `.sidebar-bottom`. Removed Settings icon from collapsed strip. Collapsed Account button toggles `accountMenuOpen` and renders `.sidebar-account-menu--dropup`. Added `collapsedAccountRef` and updated outside-click logic. Account menu divider uses class `.sidebar-account-menu-divider`. |
| `frontend/src/components/Sidebar.css` | Removed `.sidebar-settings-link` (and related). Added `.sidebar-collapsed-account-wrap`, `.sidebar-account-menu--dropup`, `.sidebar-account-menu-divider`. |
| `frontend/src/pages/TokenCenter.jsx` | Import `./TokenCenter.css`. Root div class `credit-center`. Balance card, “Need more?” card, referral box, tabs, bundle cards, history section, usage section use `var(--theme-surface)`, `var(--theme-border)`, `var(--theme-text)`, `var(--theme-muted)` via inline styles or classes. History rows and empty states use theme vars. |
| `frontend/src/pages/TokenCenter.css` | New file. Theme-aware rules for `.credit-center` and `[data-theme="dark"]` / `[data-theme="light"]` so cards and text follow theme with no leftover white in dark or black in light. |

---

## 6. How to verify

1. **Sidebar footer:** Open app → left sidebar. At bottom you should see only **Engine Room**, **credits** (with count), then **Guest**. No “Settings” row.
2. **Guest dropdown (expanded):** Click Guest → menu with Settings, Credits & Billing, Upgrade plan, Log out.
3. **Guest dropdown (collapsed):** Collapse sidebar (icon strip). Click the Guest avatar at bottom → same menu appears as a drop-up above the icon.
4. **Dark theme:** Toggle to black/dark. Credit Center and rest of app should have no white cards or panels; use dark backgrounds and theme text/muted colors.
5. **Light theme:** Toggle to white/light. Credit Center and app should be white with clear borders and readable text.

---

*End of proof.*
