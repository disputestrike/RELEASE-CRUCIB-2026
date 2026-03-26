# Preview trust path (“run contract”)

This documents the sequence the **workspace** follows so preview (Sandpack) reflects real file state — used for compliance **Section 4.8**.

## Query parameters

| Param | Role |
|-------|------|
| `projectId` | Load saved project **workspace files** from the API and hydrate `files`. |
| `taskId` | Load **task** document files and hydrate `files` (returning session). |

## Sequence (high level)

1. **Route:** User opens `/app/workspace` (canonical). Legacy `/workspace` redirects to `/app/workspace` with query preserved (`App.js` `RedirectWorkspaceToApp`).
2. **Auth:** Most workspace API calls use `Authorization: Bearer <token>` from `useAuth()`.
3. **`taskId` path** (`Workspace.jsx`):  
   `GET /api/tasks/{taskId}` → read `task.files` (or `task.doc.files`) → `setFiles` → pick `activeFile` → after short delay set `filesReadyKey` / `currentVersion` to **force Sandpack remount** → `activePanel = 'preview'`.
4. **`projectId` path:**  
   `GET /api/projects/{id}/workspace/files` → for each path `GET /api/projects/{id}/workspace/file?path=…` → merge into `files` → same **remount** pattern (`filesReadyKey`) → `activePanel = 'preview'`.  
   A ref avoids duplicate full reload for the same `projectId` in one session.
5. **Preview:** `sandpackFiles` derives Sandpack-safe paths from `files` (root→`/src` mapping, exclusions). `SandpackProvider` `key={filesReadyKey}` (or equivalent) ensures preview catches API-hydrated state.
6. **Errors:** Failed fetches leave prior/local state; individual panels show errors where implemented (e.g. DB/Docs/Sandbox). Preview uses `SandpackErrorBoundary` for runtime errors.
7. **Post-build:** When a local build completes, the app may refetch `GET /api/projects/{id}` (e.g. `live_url`) and `build-history`. **Canonical artifact for editing** remains the merged workspace/task `files` map.
8. **Sync from server (project):** In the workspace **Explorer** header (when `projectId` + auth), **Refresh** clears the one-shot load guard and re-runs `GET …/workspace/files` + per-file fetches, then bumps `filesReadyKey` so Sandpack matches server workspace files (compliance **§4.8** post-build path).

## Verification (manual)

1. Create or open a project with known files; open `/app/workspace?projectId=…`.
2. Network tab: confirm workspace `files` + `file` requests succeed.
3. Confirm Preview updates after load (not stuck on default template).
4. Repeat with `taskId` on a task that has stored files.

## Code anchors

- Redirect: `frontend/src/App.js` — `RedirectWorkspaceToApp`, route `workspace`.
- Hydration: `frontend/src/pages/Workspace.jsx` — effects for `taskIdFromUrl`, `projectIdFromUrl`, `filesReadyKey`, `sandpackFiles`.
