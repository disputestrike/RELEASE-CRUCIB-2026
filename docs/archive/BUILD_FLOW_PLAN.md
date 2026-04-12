# Build Flow: Base44 / Manus vs CrucibAI

## Base44 flow (from “build me a bank software”)

1. **Plan** – AI responds with:
   - Key features (Dashboard, Accounts, Transactions, Transfers, Customers)
   - Design language (dark navy + white + gold, card-based UI, animations, typography)
   - Color palette (Primary, Secondary, Accent, Background, Cards)
   - Components list (Layout, sidebar, stats cards, charts, account cards, transaction table, transfer form, customer list)

2. **Entities** – “Wrote entities/Account”, “Wrote entities/Transaction”, “Wrote entities/Customer”

3. **UI components** – “Wrote dashboard/Metric Card”, “Wrote dashboard/Recent Transactions List”, “Wrote dashboard/Balance Chart”, “Wrote accounts/Account Card”, “Wrote accounts/Create Account Dialog”, “Wrote transactions/Transaction Dialog”, “Wrote transactions/Transactions Table”, “Wrote customers/Customer Dialog”

4. **Pages & layout** – “Wrote Dashboard Page”, “Wrote Accounts Page”, “Wrote Transactions Page”, “Wrote Customers Page”, “Wrote Layout”

5. **Sample data** – “Created …”, “Created …”, “Created …”

6. **Done** – “Your VaultBank banking platform is ready — it includes …”

7. **Suggestions** – “Add Loan Management”, “Implement Alerts System”, “Enhance Reporting Features” (for next steps)

---

## Manus flow (from “build me a bank software”)

1. **Clarify (optional)** – “Would you like web or mobile? Core features? Is ‘BE Bank’ the name?”

2. **Commit** – “I will begin building a web-based banking application called BE Bank…”

3. **Task progress (visible steps)**:
   - 1/6 – Initialize project with scaffold and database setup
   - 2/6 – Design and implement database schema for banking operations
   - 3/6 – Build backend API endpoints for banking features
   - 4/6 – Develop frontend user interface and dashboard
   - 5/6 – Test the application and deploy for user access
   - 6/6 – Deliver final application to user

4. **Execution** – “Manus is initializing your project” (0:07), “Knowledge recalled (11)”, Blueprint card

5. **Ongoing** – “Send message to Manus” for iterations; Visual Edit, Discuss, attachments

---

## CrucibAI implementation plan

### Phase 1 (implemented here)

- **Plan-first response** – For “big” prompts (e.g. “build me a … software/app/platform/dashboard”), call `POST /api/build/plan` to get a structured plan (features, design, colors, components). Show this in the workspace chat as the first assistant message (“Here’s my plan: … Let me build this now.”), then run the existing single-file build.
- **Landing → sign up → your build** – On landing, user types a prompt and clicks Build/Get started; if not logged in, redirect to `/auth?mode=register&redirect=/app/workspace?prompt=...`. After sign up, go to workspace with that prompt and optionally auto-start build.
- **Google sign up** – Add Google OAuth (backend redirect + callback; frontend “Sign in with Google” button).

### Phase 2 (later)

- **Multi-step “Wrote” updates** – Backend or frontend breaks the build into steps (e.g. plan → generate layout + pages in one or more LLM calls) and streams or appends “Wrote X” lines to the chat.
- **Multi-file output** – Generate multiple files (e.g. `Layout.jsx`, `Dashboard.jsx`, `App.js`) instead of a single `App.js`, and show a file tree + “Wrote …” for each.
- **Suggestions** – After build, call suggest-next or a dedicated endpoint and show “Suggestions” chips (e.g. “Add Loan Management”, “Implement Alerts”) that the user can click to modify.

---

## User flow summary

- **They type on landing** → we have sign up and then “your build”.
- **Pre-sign-up**: Landing shows prompt input and “What are you building?” cards; clicking Build without auth → sign up (or login) with redirect back to workspace + prompt; after auth, user lands in workspace with prompt pre-filled and can run build.
- **Google sign up** – Same flow, with “Sign in with Google” on auth page.
