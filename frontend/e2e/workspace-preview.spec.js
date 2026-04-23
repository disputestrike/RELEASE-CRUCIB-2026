/**
 * CrucibAI workspace + Preview (Sandpack) smoke.
 *
 * Prerequisites:
 * - Backend + Postgres running (e.g. http://localhost:8000 — same as CRA proxy target)
 * - Optional: frontend at PLAYWRIGHT_BASE_URL (default http://localhost:3000)
 *
 * Run:
 *   npx playwright test --project=workspace-preview
 */
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');
const {
  waitForCrucibWorkspace,
  openCodeWorkspacePane,
} = require('./helpers/workspaceE2E.cjs');

function e2eBuildTarget() {
  return (process.env.E2E_BUILD_TARGET || 'vite_react').trim() || 'vite_react';
}

function apiBase() {
  let b = process.env.PLAYWRIGHT_API_URL || process.env.REACT_APP_BACKEND_URL || 'http://127.0.0.1:8000';
  b = String(b).replace(/\/$/, '');
  if (/:3000\b/.test(b)) {
    b = 'http://127.0.0.1:8000';
  }
  return b;
}

async function apiRequestContext(playwright) {
  return playwright.request.newContext({
    baseURL: apiBase(),
    extraHTTPHeaders: { Accept: 'application/json' },
  });
}

async function openPreviewInRightPanel(page) {
  await waitForCrucibWorkspace(page);
  await page.getByRole('button', { name: 'Preview & code' }).click({ timeout: 15000 });
  await page.getByRole('button', { name: '👁 Preview' }).click({ timeout: 15000 });
}

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

test.describe('CrucibAI workspace preview', () => {
  test.describe.configure({ mode: 'serial' });
  test.setTimeout(180000);

  test('loads /app/workspace, opens Code in right panel', async ({ page, playwright }) => {
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
      await expect(page.locator('[data-testid="right-panel-root"]')).toBeVisible({ timeout: 20000 });
      await expect(page.getByText(/Files \(\d+\)/)).toBeVisible({ timeout: 20000 });
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
        const errText = await planRes.text();
        if (
          planRes.status() >= 500 &&
          /Database|pool|NoneType|acquire|not ready/i.test(errText)
        ) {
          test.skip(
            true,
            `Orchestrator / plan needs PostgreSQL (docker compose up -d postgres). ${planRes.status()} ${errText.slice(0, 240)}`,
          );
        }
        throw new Error(`plan failed: ${planRes.status()} ${errText}`);
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
            'API returned HTML (SPA fallback) — restart uvicorn with latest server.py so /api/jobs/.../workspace/files is registered.',
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
        await waitForCrucibWorkspace(page);

        await page.getByRole('button', { name: 'Preview & code' }).click({ timeout: 15000 });
        await page.getByRole('button', { name: '📄 Code' }).click({ timeout: 15000 });

        const syncBtn = page.locator('[data-testid="workspace-files-refresh"]');
        await syncBtn.waitFor({ state: 'visible', timeout: 60000 });

        const filesPromise = page
          .waitForResponse((r) => r.url().includes(`/jobs/${jobId}/workspace/files`) && r.ok(), { timeout: 60000 })
          .catch(() => null);
        await syncBtn.click();
        await filesPromise;

        await openPreviewInRightPanel(page);

        await expect(page.locator('.sp-wrapper, iframe[title="Live Preview"]').first()).toBeVisible({ timeout: 90000 });
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
