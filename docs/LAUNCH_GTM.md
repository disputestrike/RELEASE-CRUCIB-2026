# Launch GTM — Save for Our Launch

**Purpose:** Single reference for post-build strategy and what the product must deliver for launch. The code and app must be ready to support this GTM.

---

## The Real Game Begins After the Product Works

> Building the product is actually the easy part.

**When the product works — you stop being a builder and start being a founder.** Those are two completely different jobs.

- The code getting to 10/10 buys you maybe **3 months of advantage** before competitors copy features.
- What they **cannot** copy: your users, your community, your data flywheel, and your brand. **That’s what you’re actually building after launch.**

---

## What Actually Wins (Execution, Not Just Features)

- **Lovable didn’t win because of features.** They won because Anton Osika posted obsessively on Twitter, answered every support ticket personally for the first 6 months, and shipped fixes within hours of complaints.
- **The product was a vehicle. The execution was the weapon.**

---

## Our Single Biggest Unique Card: Mobile App Build

- **Nobody in the top 10** takes a prompt all the way to an **Expo project with App Store submission guides**.
- The day that works flawlessly and someone posts:  
  **“I just submitted my iOS app to the App Store and I don’t know how to code”**  
  — that tweet gets 50,000 retweets and you wake up to 20,000 signups.

**That’s the moment. Everything before it is preparation for that moment.**

---

## What the Code & App Must Do for This GTM

1. **Mobile app build path**  
   - Prompt → full Expo project + App Store / Play Store submission guides (Native Config Agent, Store Prep Agent, app.json, eas.json, SUBMIT_TO_APPLE.md, SUBMIT_TO_GOOGLE.md).  
   - Verified in codebase: `agent_dag.py`, `server.py` mobile branch, ExportCenter / deploy flows.

2. **Quick build / “fast first build”**  
   - Optional **Quick build** so users see a preview in ~2 minutes (fewer phases).  
   - Clear copy in UI: “Quick build — preview in ~2 min” so the “fast first build” promise is explicit.

3. **Version / build history**  
   - Users can see **build history** (past builds, status, quality, tokens) so “version history” is not outstanding.

4. **Landing, dashboard, workspace, export, tokens, pricing**  
   - All wired so the app is the vehicle for community, support, and execution post-launch.

---

## Next Step

> Want to go build it? Get the database running and start executing.

- Backend: `DATABASE_URL` set, run server (e.g. uvicorn).
- Frontend: `cd frontend && npm install && npm run dev`.
- Smoke-test: landing → auth → create project (optional Quick build) → AgentMonitor → Workspace → Export (ZIP / GitHub / deploy) → TokenCenter / Pricing.  
- **Smoke-test mobile:** create a mobile project → confirm Expo + store submission artifacts in build output.

This doc is the single source for **what we’re building toward at launch** and **what the app must be ready to do** for the GTM.
