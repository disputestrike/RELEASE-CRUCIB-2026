/**
 * Workspace integration smoke (CrucibAIWorkspace + RightPanel).
 * Replaces legacy UnifiedWorkspace crosswalk — file tree is button-based (see RightPanel).
 *
 * Run: npm run e2e:workspace-crosswalk
 */
const { test, expect } = require('@playwright/test');
const {
  e2eBuildTarget,
  apiBase,
  apiRequestContext,
  waitForCrucibWorkspace,
  openCodeWorkspacePane,
  seedWorkspaceTextFiles,
  rmWorkspaceRoot,
  workspaceProjectRoot,
} = require('./helpers/workspaceE2E.cjs');

async function prepareWorkspaceSession(page, token) {
  await page.addInitScript((t) => {
    window.localStorage.setItem('token', t);
    window.localStorage.setItem('crucibai_onboarding_complete', '1');
    window.localStorage.setItem('crucibai_workspace_mode', 'developer');
    window.localStorage.setItem('crucibai_right_collapsed', 'false');
  }, token);
}

async function createGuidedPlanJob(apiReq, token, test) {
  const planRes = await apiReq.post('/api/orchestrator/plan', {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      goal: 'E2E workspace crosswalk fixture',
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
  const jobRes = await apiReq.get(`/api/jobs/${jobId}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!jobRes.ok()) {
    throw new Error(`job get failed: ${jobRes.status()} ${await jobRes.text()}`);
  }
  const jobPayload = await jobRes.json();
  const job = jobPayload.job || jobPayload;
  const projectId = job.project_id;
  return { jobId, projectId };
}

async function syncFilesFromServer(page) {
  await page.getByRole('button', { name: 'Preview & code' }).click({ timeout: 15000 });
  await page.getByRole('button', { name: '📄 Code' }).click({ timeout: 15000 });
  await page.locator('[data-testid="workspace-files-refresh"]').click({ timeout: 30000 });
}

test.describe('Workspace crosswalk', () => {
  test.describe.configure({ mode: 'serial' });
  test.setTimeout(180000);

  test('code pane: seeded file appears and opens in viewer', async ({ page, playwright }) => {
    const apiReq = await apiRequestContext(playwright);
    let root;
    try {
      const health = await apiReq.get('/api/health').catch(() => null);
      test.skip(!health || !health.ok(), `No API at ${apiBase()}/api/health`);

      const gr = await apiReq.post('/api/auth/guest', { data: {} });
      expect(gr.ok()).toBeTruthy();
      const { token } = await gr.json();
      const { jobId, projectId } = await createGuidedPlanJob(apiReq, token, test);
      root = workspaceProjectRoot(projectId);
      seedWorkspaceTextFiles(projectId, {
        'src/App.jsx': 'export default function App(){return <div>tree-e2e</div>;}\n',
        'src/tree-target.js': '// TREE_TARGET_UNIQUE\n',
      });

      await prepareWorkspaceSession(page, token);
      await page.goto(`/app/workspace?jobId=${encodeURIComponent(jobId)}`, { waitUntil: 'domcontentloaded' });
      await waitForCrucibWorkspace(page);
      await syncFilesFromServer(page);

      await page.getByRole('button', { name: 'tree-target.js', exact: true }).click({ timeout: 20000 });
      await expect(page.locator('.monaco-editor, pre').first()).toContainText('TREE_TARGET_UNIQUE', { timeout: 25000 });
    } finally {
      await apiReq.dispose();
      if (root) rmWorkspaceRoot(root);
    }
  });

  test('list endpoint precedes first file body fetch', async ({ page, playwright }) => {
    const apiReq = await apiRequestContext(playwright);
    let root;
    try {
      const health = await apiReq.get('/api/health').catch(() => null);
      test.skip(!health || !health.ok(), `No API at ${apiBase()}/api/health`);

      const gr = await apiReq.post('/api/auth/guest', { data: {} });
      expect(gr.ok()).toBeTruthy();
      const { token } = await gr.json();
      const { jobId, projectId } = await createGuidedPlanJob(apiReq, token, test);
      root = workspaceProjectRoot(projectId);
      seedWorkspaceTextFiles(projectId, {
        'src/App.jsx': 'export default function App(){return <div>lazy</div>;}\n',
        'src/lazy-a.txt': 'LAZY_A\n',
      });

      const seq = [];
      page.on('response', (res) => {
        const u = res.url();
        if (!res.ok()) return;
        if (u.includes('/workspace/files')) seq.push('list');
        if (/\/workspace\/file\?/.test(u) && u.includes('path=') && !u.includes('/raw')) seq.push('text');
      });

      await prepareWorkspaceSession(page, token);
      await page.goto(`/app/workspace?jobId=${encodeURIComponent(jobId)}`, { waitUntil: 'domcontentloaded' });
      await waitForCrucibWorkspace(page);
      await syncFilesFromServer(page);

      await expect(page.locator('[data-testid="right-panel-root"]')).toBeVisible({ timeout: 20000 });
      const iList = seq.indexOf('list');
      const iText = seq.indexOf('text');
      expect(iList, 'file list response should occur').toBeGreaterThanOrEqual(0);
      expect(iText, 'first text file body response should occur').toBeGreaterThanOrEqual(0);
      expect(iList).toBeLessThan(iText);
    } finally {
      await apiReq.dispose();
      if (root) rmWorkspaceRoot(root);
    }
  });
});
