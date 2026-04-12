/**
 * Unified workspace + Preview (Sandpack) smoke.
 *
 * Prerequisites:
 * - Backend + Postgres running (e.g. http://localhost:8000 — same as CRA proxy target)
 * - Optional: frontend at PLAYWRIGHT_BASE_URL (default http://localhost:3000); playwright.config
 *   can start `npm start` when reuseExistingServer allows.
 *
 * Run (dedicated project):
 *   npx playwright test --project=workspace-preview
 * Next execution target (plan payload):
 *   E2E_BUILD_TARGET=next_app_router npx playwright test --project=workspace-preview
 *
 * The second test creates a real job via /api/orchestrator/plan and writes `src/App.jsx` under
 * `backend/workspace/<project_id>/`, syncs from the UI, then asserts the Sandpack host + Sandbox label.
 */
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

function e2eBuildTarget() {
  return (process.env.E2E_BUILD_TARGET || 'vite_react').trim() || 'vite_react';
}

function apiBase() {
  let b = process.env.PLAYWRIGHT_API_URL || process.env.REACT_APP_BACKEND_URL || 'http://127.0.0.1:8000';
  b = String(b).replace(/\/$/, '');
  // CRA often uses REACT_APP_BACKEND_URL=http://localhost:3000 for same-origin /api proxy — that returns HTML to fetch(), not JSON.
  if (/:3000\b/.test(b)) {
    b = 'http://127.0.0.1:8000';
  }
  return b;
}

/** Playwright's default `request` uses frontend baseURL (:3000). Use a context rooted on the API for JSON routes. */
async function apiRequestContext(playwright) {
  return playwright.request.newContext({
    baseURL: apiBase(),
    extraHTTPHeaders: { Accept: 'application/json' },
  });
}

/** UnifiedWorkspace mounts `uw-root` (no legacy `.arp-topbar` wrapper). */
async function waitForUnifiedWorkspace(page) {
  await page.waitForSelector('[data-testid="unified-workspace-root"]', { timeout: 90000 });
}

/** Right-rail icon (distinct from `.arp-pane-tab` text "Preview"). */
async function openPreviewFromToolbar(page) {
  await waitForUnifiedWorkspace(page);
  await page.locator('.arp-right-toolbar button[title="Preview"]').click({ timeout: 30000 });
}

/** Dev mode exposes the Code pane tab; then open Code and assert API-driven tree + viewer shell. */
async function openCodeWorkspacePane(page) {
  await waitForUnifiedWorkspace(page);
  await page.getByRole('button', { name: 'Dev' }).click({ timeout: 15000 }).catch(() => {});
  await page.getByRole('button', { name: 'Code' }).click({ timeout: 15000 });
  await page.waitForSelector('.code-pane-main', { timeout: 20000 });
}

/**
 * Mirror backend _project_workspace_path sanitization (see server.py).
 */
function seedJobWorkspace(projectId, jsxInner) {
  const safe = String(projectId).replace(/\//g, '_').replace(/\\/g, '_');
  const root = path.join(__dirname, '..', '..', 'backend', 'workspace', safe);
  fs.mkdirSync(path.join(root, 'src'), { recursive: true });
  fs.writeFileSync(
    path.join(root, 'src', 'App.jsx'),
    `export default function App(){return <div>${jsxInner}</div>;}\n`,
    'utf8',
  );
  return root;
}

test.describe('Unified workspace preview', () => {
  test.describe.configure({ mode: 'serial' });
  test.setTimeout(180000);

  test('loads /app/workspace, opens Preview tab, shows preview shell', async ({ page, playwright }) => {
    const apiReq = await apiRequestContext(playwright);
    try {
      const health = await apiReq.get('/api/health').catch(() => null);
      test.skip(!health || !health.ok(), `No API at ${apiBase()}/api/health — start backend (uvicorn) and deps`);

      const gr = await apiReq.post('/api/auth/guest', { data: {} });
      if (!gr.ok()) {
        throw new Error(`guest auth failed: ${gr.status()} ${await gr.text()}`);
      }
      const guestJson = await gr.json();
      const token = guestJson.token;
      expect(token).toBeTruthy();

      await page.addInitScript((t) => {
        window.localStorage.setItem('token', t);
        window.localStorage.setItem('crucibai_onboarding_complete', '1');
        window.localStorage.setItem('crucibai_workspace_mode', 'developer');
        window.localStorage.setItem('crucibai_right_collapsed', 'false');
      }, token);

      await page.goto('/app/workspace', { waitUntil: 'domcontentloaded' });
      await openCodeWorkspacePane(page);
      await expect(page.locator('.wft-wrap')).toBeVisible({ timeout: 20000 });

      await openPreviewFromToolbar(page);
      await expect(page.locator('.preview-panel')).toBeVisible({ timeout: 20000 });
      await expect(page.locator('.preview-panel .pp-preview-body')).toBeVisible({ timeout: 20000 });
      await expect(page.locator('.pp-sandpack-host')).toBeVisible({ timeout: 90000 });
    } finally {
      await apiReq.dispose();
    }
  });

  test('job deep link + seeded workspace shows Sandpack preview shell', async ({ page, playwright }) => {
    const apiReq = await apiRequestContext(playwright);
    try {
      const health = await apiReq.get('/api/health').catch(() => null);
      test.skip(!health || !health.ok(), `No API at ${apiBase()}/api/health — start backend and postgres`);

      const gr = await apiReq.post('/api/auth/guest', { data: {} });
      expect(gr.ok()).toBeTruthy();
      const { token } = await gr.json();

      const planRes = await apiReq.post('/api/orchestrator/plan', {
        headers: { Authorization: `Bearer ${token}` },
        data: {
          goal: 'Minimal React hello page for E2E',
          mode: 'guided',
          build_target: e2eBuildTarget(),
        },
      });
      if (!planRes.ok()) {
        throw new Error(`plan failed: ${planRes.status()} ${await planRes.text()}`);
      }
      const planJson = await planRes.json();
      const jobId = planJson.job_id;
      expect(jobId).toBeTruthy();

      const jobRes = await apiReq.get(`/api/jobs/${jobId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(jobRes.ok()).toBeTruthy();
      const jobPayload = await jobRes.json();
      const job = jobPayload.job || jobPayload;
      const projectId = job.project_id;
      expect(projectId).toBeTruthy();

      const seededRoot = seedJobWorkspace(projectId, 'E2E workspace preview OK');
      try {
        const filesRes = await apiReq.get(`/api/jobs/${jobId}/workspace/files`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!filesRes.ok()) {
          throw new Error(`files list failed: ${filesRes.status()} ${await filesRes.text()}`);
        }
        const filesRaw = await filesRes.text();
        if (filesRaw.trimStart().toLowerCase().startsWith('<!')) {
          test.skip(
            true,
            'API returned HTML (SPA fallback) — restart uvicorn with latest server.py so /api/jobs/.../workspace/files is registered and /api/* is not index.html.',
          );
        }
        const filesJson = JSON.parse(filesRaw);
        expect(filesJson.files || []).toContain('src/App.jsx');

        await page.addInitScript((t) => {
          window.localStorage.setItem('token', t);
          window.localStorage.setItem('crucibai_onboarding_complete', '1');
          window.localStorage.setItem('crucibai_workspace_mode', 'developer');
          window.localStorage.setItem('crucibai_right_collapsed', 'false');
        }, token);

        await page.goto(`/app/workspace?jobId=${encodeURIComponent(jobId)}`, { waitUntil: 'domcontentloaded' });
        await waitForUnifiedWorkspace(page);

        const syncBtn = page
          .locator('[data-testid="unified-workspace-root"]')
          .locator('button[title="Reload files from server"]');
        await syncBtn.waitFor({ state: 'visible', timeout: 60000 });

        const filesPromise = page
          .waitForResponse((r) => r.url().includes(`/jobs/${jobId}/workspace/files`) && r.ok(), { timeout: 60000 })
          .catch(() => null);
        await syncBtn.click();
        await filesPromise;

        await openPreviewFromToolbar(page);

        await expect(page.locator('.pp-sandpack-host')).toBeVisible({ timeout: 90000 });
        // Sandpack may host the runtime iframe inside shadow / nested roots; assert shell + mode like test 1.
        await expect(page.locator('.preview-panel')).toContainText('Sandbox', { timeout: 30000 });
      } finally {
        try {
          fs.rmSync(seededRoot, { recursive: true, force: true });
        } catch {
          /* ignore cleanup */
        }
      }
    } finally {
      await apiReq.dispose();
    }
  });
});
