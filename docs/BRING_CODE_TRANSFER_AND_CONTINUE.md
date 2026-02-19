# How We Get Users to Bring Their Code to Us — Transfer, Fix, Continue, Rebuild

**Purpose:** How users working elsewhere (local, Git, other builders) can **transfer** their project to CrucibAI, and how we **receive, understand, give feedback, fix, continue, or rebuild** — so we're ready to receive code, review it, and do everything (edit, fix, improve, adjust, navigate, understand).

---

## 1. How do we get them to transfer?

**Ways to bring code in:**

| Source | How they transfer | What we do |
|--------|--------------------|------------|
| **Paste / manual** | User pastes code (single file or multiple path→code) in the app. | Accept via **Import** in Workspace or Dashboard: "Paste or upload files" → we create an **imported project** and load files into the workspace so they can edit, run Security scan, Validate-and-fix, and continue building. |
| **Upload ZIP** | User uploads a ZIP of their project (e.g. export from Replit, Bolt, or local folder). | Backend unpacks ZIP (safe paths, size limit), creates project, writes files to workspace path; frontend opens project in Workspace with files loaded. |
| **Git URL** | User pastes a public Git repo URL (GitHub, GitLab, etc.). | Backend clones (or fetches archive) in a sandbox, creates project, writes files to workspace; user gets project in Workspace. Optional: branch/tag. |
| **Other builders** | Export from Manus, Bolt, Replit, v0, etc. (usually ZIP or Git). | Same as ZIP or Git: we receive the export and treat it as "imported project." |

So: **we support (1) paste, (2) upload ZIP, (3) Git URL.** That covers local (ZIP/paste), Git, and other builders (ZIP export).

---

## 2. What happens after we receive code?

**Steps (we stand it up, understand it, then help):**

1. **Receive** — Paste, ZIP upload, or Git URL → we create an **imported** project and persist files in the project workspace.
2. **Stand up in our system** — Files live in the project workspace; user opens the project in **Workspace** (editor + preview). We don't run `npm install` or a full build on import by default; we show the code and structure.
3. **Understand** — We always have the project structure and file contents when we stand it up (file tree, paths, code). On top of that we can run:
   - **Security scan** on the imported files (existing `POST /ai/security-scan`).
   - **Accessibility check** (existing `POST /ai/accessibility-check`).
   - **Validate-and-fix** for syntax/errors (existing `POST /ai/validate-and-fix`).
   - **"Understand this project"** (LLM summary) — stack, structure, entry points, scripts. Can be run automatically after import or on demand (e.g. button or chat: "Summarize this project"). Optional = we don't have to run the LLM on every import to save tokens; the system already "understands" via the files and structure.
4. **Give feedback** — Report from security scan, a11y, and (if run) "understand" summary. Show in Workspace or a small "Import report" panel.
5. **Fix / improve / continue** — User can:
   - **Edit** in the Workspace (we already have editor + files).
   - **Fix** — Use "Validate-and-fix" and apply suggestions; or ask in chat "fix the login bug" and we modify code (existing chat/modify flow).
   - **Improve** — Same: "add dark mode," "make it responsive" via chat.
   - **Continue** — Keep working in Workspace; run build/deploy when ready.
6. **Rebuild from start (with permission)** — If they prefer to start over: "Rebuild this from scratch based on this code" → we treat it as a new build (prompt derived from project or they type a new one). They explicitly choose "rebuild from start" so we don't overwrite without permission.

**Abandon / adjust / change:** All of that is "edit and improve" in Workspace; they can delete files, add files, or run a new build in a new project if they want a clean slate.

---

## 3. What we need in product (implemented or to implement)

| Capability | Status | Notes |
|------------|--------|--------|
| **Import: paste** | Implemented | `POST /projects/import` with `source: "paste"`, `files: { path, code }[]` → create project, write files to workspace, return project_id. Frontend: "Import" in Workspace/Dashboard → paste or add files → submit. |
| **Import: ZIP upload** | Implemented | Same endpoint `source: "zip"`, multipart file or base64 chunk; backend unpacks (safe paths, max size), write to workspace, return project_id. |
| **Import: Git URL** | Implemented | `POST /projects/import` with `source: "git"`, `git_url: string`; backend fetches (e.g. `git clone --depth 1` or GitHub archive API), write to workspace, return project_id. |
| **Open imported project in Workspace** | Implemented | Frontend navigates to Workspace with project_id; loads files from backend (GET workspace files + content) or from project state. |
| **Security scan / A11y on imported** | Existing | User runs Security scan and Accessibility check from Workspace on current files (same as for built code). |
| **Understand this project (summary)** | Implemented | Optional `POST /projects/{id}/understand` or prompt in chat: "Summarize this project (stack, structure, entry points)." Returns short report. |
| **Fix / continue in chat** | Existing | Workspace already has chat + modify; user can say "fix X" or "add Y" and we update code. |
| **Rebuild from start** | Product | User clicks "Rebuild from scratch" and confirms; we create a *new* project and run orchestration with a prompt (e.g. "Build an app like the one in [imported project]" or they type a new prompt). No overwrite of imported project without permission. |

---

## 4. User flow (seamless transfer)

1. User goes to **Dashboard** or **Workspace**.
2. Clicks **"Import project"** (or "Bring your code").
3. Chooses:
   - **Paste / add files** — Add one or more files (path + content); submit.
   - **Upload ZIP** — Select file; we unpack and create project.
   - **Git URL** — Paste repo URL; we fetch and create project.
4. We create the project, persist files, and open it in **Workspace** (editor + preview).
5. We optionally show **"Import report"**: "We received N files. Run Security scan and Accessibility check to get feedback."
6. User can **navigate** (file tree), **understand** (optional summary), **edit**, **fix** (validate-and-fix or chat), **improve** (chat), or **rebuild from start** (new project, with permission).

---

## 5. Summary

- **How do we get users to bring code?** — By supporting **paste**, **ZIP upload**, and **Git URL** in an **Import** flow that creates a project and opens it in the Workspace.
- **How do we fix broken code / continue / rebuild?** — **Fix:** Validate-and-fix and chat-driven edits. **Continue:** Work in the same project in Workspace. **Rebuild:** Explicit "Rebuild from scratch" that creates a new project (with their permission).
- **Stand up and understand:** Files are stored in the project workspace; we **understand** the project as soon as it's stood up (we have the file tree and contents). We can also run Security scan, A11y, and an optional LLM summary ("Understand this project") for a written report; we **give feedback** in the report and in Workspace.
- **Everything:** Receive → review (security, a11y, summary) → give feedback → edit, fix, improve, navigate, understand; optionally abandon or rebuild from start with permission.

This doc is the product spec for "bring your code" and transfer/continue/rebuild. Implementation: see backend `POST /projects/import` and frontend Import UI.
