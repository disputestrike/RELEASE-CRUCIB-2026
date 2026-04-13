# Mobile Apps + App Store / Play Store: Full End-to-End Plan

**Recommendation: Yes — add it.**  
Web + mobile are the two main surfaces. Adding native/cross-platform mobile (React Native/Expo, Flutter) and a clear path to **Apple App Store** and **Google Play Store** gives you full coverage and a clear edge over Devin and others who don’t offer “prompt → store-ready app” in one flow.

---

## 1. Requirements (what we’re adding)

| ID | Requirement | Priority |
|----|-------------|----------|
| M1 | User can request a **mobile app** (build_kind: mobile or explicit “iOS/Android app”) and get a **real mobile project**, not a web wrapper. | P0 |
| M2 | Output is a **runnable mobile project**: **Expo (React Native)** as primary, **Flutter** as optional/second stack. | P0 |
| M3 | Project includes **native config** (app.json, eas.json for Expo; or pubspec + Android/iOS for Flutter) so users can build **iOS** and **Android** binaries. | P0 |
| M4 | **Export** includes a **“Store submission pack”**: app metadata (title, description, keywords), icon/splash specs, screenshot placeholders, and a **step-by-step guide** for App Store Connect and Google Play Console. | P0 |
| M5 | (Later) Optional **build step**: run `eas build` (Expo) or `flutter build` in sandbox so we can produce build artifacts or at least validate the project. | P1 |
| M6 | (Later) **Store submit**: either one-click (EAS Submit / Fastlane / Play API where possible) or a “Submit to stores” agent that produces exact commands and checklist. | P2 |

**Out of scope for v1:** Full automation of Apple/Google review, signing key generation in our UI, or hosting the binaries ourselves. We produce the **project + store pack + instructions**; user (or future integration) does the final submit.

---

## 2. Technical stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Primary mobile framework** | **Expo (React Native)** | Same JS/React ecosystem as our web stack; simpler than bare React Native; EAS Build + EAS Submit for builds and store submission. |
| **Secondary option** | **Flutter** | For users who want Dart/native feel; we can add a “Flutter” branch in Stack Selector and a Flutter UI agent. |
| **Build** | **EAS Build** (Expo Application Services) | Cloud builds for iOS/Android; no need for user to have Xcode/Android Studio locally. |
| **Store submission** | **EAS Submit** (Expo) for Expo apps; **Fastlane** or Play Console API for Flutter or advanced flows | EAS Submit can push to App Store Connect and Play Console; for Flutter we output scripts or docs. |
| **Config files** | app.json, eas.json (Expo); AndroidManifest.xml, Info.plist (generated or templated) | Stored in project state and written into workspace like we do for web (App.jsx, server.py). |

**Integration points in our stack:**

- **Plan:** Already has `build_kind: mobile`; extend so plan explicitly says “Expo” or “Flutter” and “targets: iOS, Android.”
- **Stack Selector:** When build_kind is mobile, recommend “Expo (React Native)” or “Flutter” with one line on when to pick which.
- **Agents:** New or extended agents (see below) produce mobile UI, native config, and store pack.
- **Workspace / state:** Same project state (plan, requirements, stack, artifacts); new artifact types: `mobile_app` (Expo or Flutter project files), `store_pack` (metadata + guide).
- **Export:** New export type “Mobile project + Store pack” (ZIP with Expo/Flutter project + a `store-submission/` folder with metadata, icon/screenshot specs, and `SUBMIT_TO_APPLE.md` / `SUBMIT_TO_GOOGLE.md`).

---

## 3. How it flows within what we have

### 3.1 Current flow (web)

1. User creates project with prompt (optional build_kind).
2. `build_kind` is inferred or set (e.g. fullstack, mobile).
3. Plan phase: Planner, Requirements, **Stack Selector** → plan + stack.
4. Execution: **Frontend Generation** (React/JSX), **Backend Generation**, Database, Test, Security, UX, Deployment, etc.
5. Post-phase: autonomy loop (tests/security retry).
6. We build `deploy_files`: App.jsx, server.py, schema.sql, tests.
7. User sees Build state, Event timeline; export ZIP/GitHub/Deploy (Vercel/Netlify).

### 3.2 New flow when build_kind = mobile

1. **Same** project creation; `build_kind` = mobile (explicit or inferred from “iOS app”, “Android app”, “mobile app”).
2. **Plan phase** (unchanged structurally): Planner, Requirements, **Stack Selector**.
   - **Stack Selector** for mobile: system prompt addition — “When build_kind is mobile, recommend Expo (React Native) or Flutter. Output: 'Mobile stack: Expo' or 'Flutter', targets: iOS, Android.”
3. **Execution phases** — two ways to implement:

   **Option A (minimal): Mobile branch inside existing agents**  
   - **Stack Selector** output includes `mobile_stack: expo | flutter`.  
   - **Frontend Generation**: When `mobile_stack` is set, we pass a different system prompt: “You are Mobile Frontend (Expo/React Native). Output only valid React Native/Expo component code (App.js, use React Native components). No markdown.” So one agent, two behaviors (web vs mobile) by context.  
   - Add **one new agent**: **Native Config Agent** (depends_on: Stack Selector). Outputs app.json, eas.json for Expo (or pubspec.yaml + Android/iOS hints for Flutter).  
   - Add **one new agent**: **Store Prep Agent** (depends_on: Frontend Generation or Mobile Frontend, Native Config). Outputs: app name, short description, long description, keywords, icon size list, screenshot sizes for Apple + Google, and a markdown checklist for submission.

   **Option B (cleaner long-term): Dedicated mobile agents**  
   - **Mobile UI Agent** (Expo/RN): depends_on Stack Selector; only runs when build_kind=mobile; outputs Expo React Native app code (App.js, screens, navigation).  
   - **Flutter UI Agent** (optional): same idea for Flutter; runs when stack=Flutter.  
   - **Native Config Agent**: app.json, eas.json (Expo) or Flutter project structure.  
   - **Store Prep Agent**: metadata + SUBMIT_TO_APPLE.md, SUBMIT_TO_GOOGLE.md.  
   - **Deployment Agent** (existing): when build_kind=mobile, also output “EAS Build” and “EAS Submit” steps.

   **Recommendation:** Start with **Option A** (branch in Frontend + two new agents: Native Config, Store Prep) so we don’t explode the DAG; later split into dedicated Mobile UI / Flutter UI if needed.

4. **Post-phase:** Same autonomy loop; for mobile we might add a “Config validation” step (e.g. app.json valid) instead of pytest/npm test when there’s no web backend.
5. **State and deploy_files:**  
   - When build_kind is mobile, we still use `results["Frontend Generation"]` (or a dedicated key like `results["Mobile UI Agent"]` if we add it) for the main app code.  
   - We add `results["Native Config Agent"]` → write app.json, eas.json into project.  
   - We add `results["Store Prep Agent"]` → write store metadata and markdown guides into project.  
   - **deploy_files** for mobile: e.g. `App.js`, `app.json`, `eas.json`, `package.json`, `babel.config.js`, `store-submission/SUBMIT_TO_APPLE.md`, `store-submission/SUBMIT_TO_GOOGLE.md`, `store-submission/metadata.json`.  
   - Workspace preview: for Expo we could show “Expo project ready; run `npx expo start` locally or use EAS Build for iOS/Android.” (We can add a “Mobile preview” panel that points to Expo Go or EAS build link later.)
6. **Export:**  
   - **Export ZIP** (mobile): same as now but with mobile project layout + `store-submission/` folder.  
   - **Export for App Store / Play Store**: same ZIP; we add a short UI label “Includes store submission guide” and link to docs.

### 3.3 DAG changes (concrete)

- **agent_dag.py**  
  - Add **Native Config Agent**: `depends_on: ["Stack Selector"]`; system prompt: “You are a Native Config Agent. For an Expo app, output valid app.json and eas.json (JSON only). Include name, slug, version, ios.bundleIdentifier, android.package. For EAS Build: build profile for preview and production.”  
  - Add **Store Prep Agent**: `depends_on: ["Frontend Generation", "Native Config Agent"]` (or "Mobile UI Agent" when we have it). System prompt: “You are a Store Prep Agent. Output a JSON with: app_name, short_description, long_description, keywords (array), icon_sizes_apple, icon_sizes_android, screenshot_sizes_apple, screenshot_sizes_android. Then output two markdown docs: SUBMIT_TO_APPLE.md and SUBMIT_TO_GOOGLE.md with step-by-step submission (App Store Connect, Play Console), including signing, screenshots, and review checklist.”

- **server.py**  
  - **Frontend Generation**: when `build_kind == "mobile"` (and optionally stack says Expo), call Frontend with a mobile-specific system prompt: “You are Frontend Generation for a mobile app. Output only Expo/React Native code (App.js, React Native components, no DOM). No markdown.”  
  - **Orchestration** (run_orchestration_v2): when building `deploy_files`, if `build_kind == "mobile"`, collect:  
    - Main app code from Frontend Generation (or Mobile UI Agent).  
    - Native config from Native Config Agent → app.json, eas.json.  
    - Store Prep output → metadata.json, SUBMIT_TO_APPLE.md, SUBMIT_TO_GOOGLE.md.  
    - Optionally a minimal package.json and babel.config.js for Expo so the ZIP is `npm install` + `npx expo start` ready.

- **Infer build_kind** (_infer_build_kind): already have “mobile”; ensure phrases like “iOS app”, “Android app”, “App Store”, “Play Store”, “mobile app” set build_kind to `"mobile"`.

### 3.4 Tool executor (optional for v1)

- Add a tool or allowlist command for **run**: e.g. `npx create-expo-app` or `npx expo export` / `eas build --non-interactive` so that in future we can run a build in sandbox and show “Build for iOS/Android started.” For v1, we can skip this and only emit the project + docs.

---

## 4. Implementation phases

| Phase | What | Deliverable |
|-------|------|-------------|
| **1 – Requirements & design** | Lock M1–M4; confirm Option A (branch in Frontend + 2 new agents). | This doc + ticket list. |
| **2 – Plan + Stack** | Extend plan prompt for mobile (Expo/Flutter); Stack Selector recommends Expo or Flutter when build_kind=mobile. | Plan and stack output include mobile stack. |
| **3 – Mobile frontend branch** | When build_kind=mobile, Frontend Generation uses mobile system prompt; output is Expo/RN code. | deploy_files include App.js (Expo) instead of App.jsx (web). |
| **4 – Native Config agent** | Add Native Config Agent to DAG; implement in server (new agent run + persist app.json, eas.json). | Project has valid app.json, eas.json. |
| **5 – Store Prep agent** | Add Store Prep Agent; output metadata.json + SUBMIT_TO_APPLE.md, SUBMIT_TO_GOOGLE.md. | Export ZIP includes store-submission/ folder. |
| **6 – State & deploy_files** | Orchestration builds mobile deploy_files (Expo project + store pack); workspace shows “Mobile project” when applicable. | One export = full Expo project + store guide. |
| **7 – Export & UI** | Export ZIP for mobile projects includes correct layout; Settings/Docs mention “Mobile apps + App Store / Play Store”. | User can download and follow store docs. |
| **8 (P1)** | Optional: EAS Build in sandbox or “Build for iOS/Android” button that runs `eas build` and returns build URL. | Better UX for non-experts. |
| **9 (P2)** | Optional: EAS Submit or “Submit to stores” agent that produces one-click submit or exact Fastlane/Play API steps. | “Push to App Store / Play Store” in messaging. |

---

## 5. User communication (how we say it)

### 5.1 Messaging goals

- We build **web and mobile** — one prompt to app, then to **App Store and Play Store**.
- We’re **better than Devin** (and others) on **mobile + store**: full path from idea to store-ready app and submission guide, not just code.

### 5.2 Copy and placement

| Place | Message |
|-------|--------|
| **Landing hero** | “Build web and mobile apps. Ship to the App Store and Google Play.” |
| **Features** | “Mobile apps: Build iOS and Android with Expo (React Native) or Flutter. Get a store submission pack and step-by-step guides for Apple and Google.” |
| **Comparison (vs Devin, etc.)** | “CrucibAI: From prompt to store-ready mobile app — including App Store and Play Store submission guides. Devin: General coding; no dedicated mobile → store flow.” |
| **Docs** | New page: “Building mobile apps” (how to choose mobile, Expo vs Flutter, what you get in the ZIP). New page: “Submitting to Apple App Store and Google Play” (links to SUBMIT_TO_APPLE.md / SUBMIT_TO_GOOGLE.md and EAS docs). |
| **Workspace** | When project is mobile: badge or label “Mobile project (Expo)” and “Export includes store submission guide.” |
| **Export modal** | For mobile projects: “Download mobile project + App Store / Play Store submission guide.” |

### 5.3 Competitive one-liner

- **Devin:** Great at general coding and long tasks; no dedicated “build mobile app → push to App Store / Play Store” flow.  
- **CrucibAI:** Build web **and** mobile; get a runnable Expo (or Flutter) project plus a **store submission pack** and step-by-step guides for **Apple and Google**. That’s how we beat Devin (and others) on mobile.

---

## 6. Summary

- **Should we add it?** **Yes.**  
- **What we’re adding:** Real mobile projects (Expo first, Flutter option), native config (app.json, eas.json), and a **Store submission pack** (metadata + SUBMIT_TO_APPLE.md / SUBMIT_TO_GOOGLE.md). Optional later: EAS Build in-product, EAS Submit or Fastlane-style submit.
- **How it fits:** Same plan → DAG → state → export flow; `build_kind: mobile` triggers mobile stack, mobile frontend output, two new agents (Native Config, Store Prep), and mobile deploy_files + store-submission folder in export.
- **How we say it:** “Build web and mobile — ship to the App Store and Google Play” everywhere; position as the platform that takes you all the way to store-ready and beats Devin on mobile + store coverage.

Use this doc as the single source of truth for requirements, implementation, technical stack, flow, and user communication.
