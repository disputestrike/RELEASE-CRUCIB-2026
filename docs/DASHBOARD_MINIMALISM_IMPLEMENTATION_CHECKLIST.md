# Dashboard minimalism — implementation checklist (crosswalk)

**Purpose:** Verify every approved item from the Manus-style minimalism plan is implemented. Use this for compliance / sign-off before release.

**Related change:** Home `Dashboard.jsx` / `Dashboard.css`, sidebar `Sidebar.jsx` / `Sidebar.css`, Settings `Settings.jsx`, shared nav `frontend/src/config/engineRoomNav.js`.

---

## Home (`/app`) — main column

| # | Requirement | Verify |
|---|----------------|--------|
| H1 | Golden path **card removed** from default home | Open `/app` (no chat). No large “Golden path” bordered card. |
| H2 | (Removed) ~~“How builds work”~~ — link and modal removed per product decision | — |
| H3 | **No** full-width “What can I build?” **grid** on home | No 5-column skill cards on home. |
| H4 | Primary chips row **without** “Quick start” label | Chips row only; no uppercase label above chips. |
| H5 | **More** menu contains Import + all **SKILLS** starters + gallery CTA | Open More → Import code; template rows; footer “Browse templates & gallery” → `/app/templates`. |
| H6 | **Spacing / measure**: calmer vertical rhythm, narrower column | Content column max-width ~560px; increased gaps in `.home-messages`. |
| H7 | **Typography**: headline reads stronger | Greeting uses heavier weight / adjusted size (see `.dashboard-greeting-sub`). |

---

## Sidebar

| # | Requirement | Verify |
|---|----------------|--------|
| S1 | **Create**: single **“New”** primary + chevron menu | One row: New + ▼; menu: New task, New project. |
| S2 | **Knowledge** merged into **Library** | One “Library” row with chevron; nested: Prompts, Learn, Patterns. |
| S3 | **History** hidden when **empty** | Fresh guest with no tasks: History block absent. After a task exists: History returns. |
| S4 | **Engine Room** removed from sidebar | No wrench accordion in sidebar body; credits row still visible. |
| S5 | **Engine room** reachable from **account** menu | Footer account menu + collapsed account menu include “Engine room” → Settings tab. |
| S6 | Collapsed strip: **one** “New” (Plus), no Engine icon | Collapsed: Plus for new task; no wrench in bottom strip. |

---

## Settings

| # | Requirement | Verify |
|---|----------------|--------|
| E1 | New tab **Engine room** | Settings nav lists “Engine room”; selecting shows link list. |
| E2 | Engine list matches former sidebar list | Count / routes align with `ENGINE_ROOM_ITEMS` in `frontend/src/config/engineRoomNav.js`. |
| E3 | Deep-link from sidebar | Sidebar “Engine room” opens Settings with **Engine room** tab active (`state.openTab: 'engine'`). |

---

## Regression smoke

- [ ] `/app` submit prompt / chip still navigates to workspace with `taskId` where applicable.
- [ ] Import modal still opens from **Import code** (More menu).
- [ ] Live “Your builds” block still shows when projects exist.
- [ ] Settings other tabs unchanged (Account, Security, …).
- [ ] No console errors on `/app` and `/app/settings`.

---

**Sign-off:** Name / date when all rows checked.
