# Images, Videos & Legal – Implementation Summary

This document confirms **full implementation**, **continuity**, **functionality**, and **legal handling** for CrucibAI as requested.

---

## 1. IMAGES (Together.ai)

### Implemented
- **`backend/agents/image_generator.py`**
  - `generate_image(prompt)` – calls Together.ai (FLUX.1-schnell), returns image URL or base64.
  - `parse_image_prompts(llm_output)` – parses LLM JSON `{ "hero", "feature_1", "feature_2" }`.
  - `generate_images_for_app(design_description, prompts_dict)` – generates hero + feature images; uses `prompts_dict` when provided, otherwise derives from `design_description`.
- **DAG**  
  - **Image Generation** agent now outputs **JSON only** (hero, feature_1, feature_2 prompts).  
  - After the LLM returns, the server parses that JSON and calls `generate_images_for_app()`; result is stored as `results["Image Generation"]["images"]` and on the project as `project.images`.
- **Orchestration**  
  - When building `deploy_files`, frontend JSX is passed through `_inject_media_into_jsx(fe, images, videos)`: placeholders `CRUCIBAI_HERO_IMG`, `{{HERO_IMAGE}}`, etc. are replaced; if none exist, a media section (hero image + feature images grid) is prepended to the component return.
- **Frontend**  
  - **AgentMonitor**: when `project.status === 'completed'` and `project.images` exist, a “Generated media” block shows hero + feature_1 + feature_2 thumbnails.
- **Config**  
  - `TOGETHER_API_KEY` and optional `TOGETHER_IMAGE_MODEL` in `backend/.env` (see `.env.example`).  
  - If `TOGETHER_API_KEY` is missing, Image Generation still runs (LLM returns prompts only); no images are generated and no errors.

### Proof / continuity
- Same flow for any domain (basketball, tanks, solar, etc.): **Stack Selector** → **Image Generation** (LLM → JSON prompts → Together.ai) → images stored and injected into generated app.
- Cost: Together.ai on the order of ~$0.005–0.02 per image; 3 images per app keeps margin positive vs token pricing.

---

## 2. VIDEOS (Pexels)

### Implemented
- **`backend/agents/video_generator.py`**
  - `find_video(query)` – calls Pexels Video Search API, returns one HD video URL.
  - `parse_video_queries(llm_output)` – parses LLM JSON `{ "hero", "feature" }` (search queries).
  - `generate_videos_for_app(design_description, queries_dict)` – finds hero and feature videos; uses `queries_dict` when provided, otherwise derives from `design_description`.
- **DAG**  
  - **Video Generation** agent added; `depends_on: ["Image Generation"]`; outputs **JSON only** (hero, feature search queries).  
  - After the LLM returns, the server parses and calls `generate_videos_for_app()`; result is stored as `results["Video Generation"]["videos"]` and on the project as `project.videos`.
- **Orchestration**  
  - Same `_inject_media_into_jsx`: placeholders `CRUCIBAI_HERO_VIDEO`, `{{HERO_VIDEO}}`, etc. are replaced; if none, a hero video block is prepended when `videos.hero` exists.
- **Frontend**  
  - **AgentMonitor**: when `project.videos` exist, “Generated media” shows hero video and feature video (autoPlay, muted, loop).
- **Config**  
  - `PEXELS_API_KEY` in `backend/.env`.  
  - If missing, Video Generation still runs (LLM returns queries only); no video URLs and no errors.

### Proof / continuity
- Domain-aware: LLM produces search queries from the same project context (e.g. “basketball training”, “solar panels”), so Pexels returns relevant stock videos. Legal: Pexels content is used per their API terms (no scraping).

---

## 3. LEGAL COMPLIANCE (AUP + Admin)

### Implemented
- **`backend/agents/legal_compliance.py`**
  - `check_request(prompt)` – keyword-based check against prohibited categories (illegal, adult, gambling, harassment, etc.). Returns `{ "allowed", "reason", "category" }`.
- **Project creation**  
  - Before creating a project and starting orchestration, the server runs `legal_check_request(prompt)`.  
  - If not allowed: request is logged to `db.blocked_requests` (user_id, prompt, reason, category, timestamp, status: `"blocked"`), and the API returns **400** with the reason (reference to AUP).
- **Admin**
  - **GET `/api/admin/legal/blocked-requests`** – list blocked requests (optional `?status=blocked|reviewed`).
  - **POST `/api/admin/legal/review/{request_id}`** – body `{ "action": "false_positive" | "confirmed" | "escalated" }`; updates document with `status: "reviewed"`, `review_action`, `reviewed_by`, `reviewed_at`.
- **Frontend**
  - **Admin Legal** page: `/app/admin/legal` – lists blocked requests, filter (All / Blocked / Reviewed), review actions (False positive, Confirm, Escalate). Linked from Admin Dashboard.
- **Legal pages**
  - **AUP**: `/aup` – Acceptable Use Policy (summary + appeals contact).
  - **DMCA**: `/dmca` – DMCA & Copyright (takedown, counter-notice, repeat infringers).
  - **Terms** and **Privacy** already existed; **PublicFooter** updated with links to AUP and DMCA.

### Legal considerations (as requested)
- **No scraping / illegal use**: Image and video flows use only Together.ai and Pexels APIs under their terms; no scraping or unauthorized data use.
- **AUP enforcement**: Prohibited prompts are blocked before any build; logged for audit and admin review; appeals path documented (e.g. appeals@crucibai.com).
- **DMCA**: Policy and contact (dmca@crucibai.com) published; admin can review and escalate; repeat-infringer handling described.
- **Property management / legal alternatives**: The spec’s “legal way” (user-submitted data, legal APIs, no scraping) is aligned with what CrucibAI generates (apps that users fill with their own data or licensed sources). The legal compliance agent blocks requests that clearly ask for illegal or policy-violating builds.

---

## 4. DEPENDENCIES & CONFIG

- **Backend**
  - `together>=1.0.0` added to `requirements.txt`.
  - `backend/.env.example` documents:
    - `TOGETHER_API_KEY`, `TOGETHER_IMAGE_MODEL`
    - `PEXELS_API_KEY`
- **Optional**
  - If neither Together nor Pexels keys are set, builds still complete; only image/video URLs are omitted and no media is injected.

---

## 5. END-TO-END FLOW (confirmation)

1. User submits a build (e.g. “Build a SaaS landing for basketball training”).
2. **Legal**: `check_request(prompt)` runs; if blocked → 400 + log; else continue.
3. **Orchestration** (DAG): Planner → Requirements → Stack Selector → (parallel) Frontend, Backend, DB, API, Test, **Image Generation** → **Video Generation** → Security, UX, etc. → Deployment, Export agents.
4. **Image Generation**: LLM returns JSON prompts → `generate_images_for_app()` → `project.images` and injection into JSX.
5. **Video Generation**: LLM returns JSON queries → `generate_videos_for_app()` → `project.videos` and injection into JSX.
6. **Frontend**: Completed project shows “Generated media” (images + videos) in AgentMonitor; deployed app includes hero/feature images and hero (and optionally feature) video when URLs are present.

---

## 6. CHECKLIST (for your approval)

- [x] Together.ai image agent + integration in DAG and orchestration.
- [x] Pexels video agent + integration in DAG and orchestration.
- [x] Frontend display of images/videos in build completion (AgentMonitor).
- [x] Generated code includes image/video URLs (placeholder replace + prepend section).
- [x] Legal compliance agent (keyword AUP check) before project creation.
- [x] Blocked requests logged and admin endpoints (list + review).
- [x] Admin Legal UI (list, filter, review actions) and link from Admin Dashboard.
- [x] Legal docs: AUP and DMCA pages and footer links; Terms/Privacy unchanged.
- [x] Legal and ethical use: no scraping; Pexels/Together used per their terms; AUP and DMCA documented and enforced.

You can approve this implementation and ship with the optional env vars (`TOGETHER_API_KEY`, `PEXELS_API_KEY`) set when you want images and videos enabled.

---

## 7. LEGAL COVERAGE ON WEBSITE (where things live)

| Where | What's covered |
|-------|----------------|
| **Public footer (PublicFooter.jsx)** | Links: Privacy, Terms, Acceptable Use, DMCA |
| **Landing page footer** | Same: Privacy, Terms, AUP, DMCA |
| **App shell footer (Layout.jsx)** | Same: Privacy, Terms, AUP, DMCA |
| **Auth / signup (AuthPage.jsx)** | "By creating an account you agree to our Terms and Privacy Policy" with links (register only) |
| **Project creation (ProjectBuilder.jsx)** | On 400 (e.g. AUP block): error message + "View Acceptable Use Policy" link + appeals@crucibai.com |
| **Routes** | `/terms`, `/privacy`, `/aup`, `/dmca` – all public |
| **Admin** | `/app/admin/legal` – blocked requests list + review; linked from Admin Dashboard |

So legal is implemented on the website and in the right places for users and admins.
