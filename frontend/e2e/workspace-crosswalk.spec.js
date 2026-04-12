/**
 * Browser-level proof for workspace Code pane: tree, typed viewer, openWorkspacePath, lazy bodies, sync, ZIP.
 * Run: npm run e2e:workspace-crosswalk
 */
const { test, expect } = require('@playwright/test');
const {
  e2eBuildTarget,
  apiBase,
  apiRequestContext,
  waitForUnifiedWorkspace,
  openCodeWorkspacePane,
  seedWorkspaceTextFiles,
  seedWorkspaceBinaryFile,
  rmWorkspaceRoot,
  tinyPngBuffer,
  patchJobGetToFailed,
  syntheticSteps,
  syntheticEvents,
  syntheticProof,
  fulfillJsonRoutes,
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

async function createGuidedPlanJob(apiReq, token) {
  const planRes = await apiReq.post('/api/orchestrator/plan', {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      goal: 'E2E workspace crosswalk fixture',
      mode: 'guided',
      build_target: e2eBuildTarget(),
    },
  });
  if (!planRes.ok()) {
    throw new Error(`plan failed: ${planRes.status()} ${await planRes.text()}`);
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

async function assertCodePaneShowsPath(page, posixPath) {
  await expect(page.locator('.arp-pane-tab.active').filter({ hasText: /^Code$/ })).toBeVisible({ timeout: 15000 });
  await expect(page.locator('.wfv-path')).toContainText(posixPath, { timeout: 20000 });
  const leaf = posixPath.split('/').pop();
  await expect(page.locator('.wft-row--selected .wft-label').first()).toHaveText(leaf);
}

async function clickCenterSync(page) {
  const syncBtn = page
    .locator('[data-testid="unified-workspace-root"]')
    .locator('.arp-center-toolbar')
    .getByRole('button', { name: 'Sync' });
  await syncBtn.click({ timeout: 30000 });
}

test.describe('Workspace crosswalk', () => {
  test.describe.configure({ mode: 'parallel' });
  test.setTimeout(180000);

  test('code tree: select file shows highlight and viewer', async ({ page, playwright }) => {
    const apiReq = await apiRequestContext(playwright);
    let root;
    try {
      const health = await apiReq.get('/api/health').catch(() => null);
      test.skip(!health || !health.ok(), `No API at ${apiBase()}/api/health`);

      const gr = await apiReq.post('/api/auth/guest', { data: {} });
      expect(gr.ok()).toBeTruthy();
      const { token } = await gr.json();
      const { jobId, projectId } = await createGuidedPlanJob(apiReq, token);
      root = workspaceProjectRoot(projectId);
      seedWorkspaceTextFiles(projectId, {
        'src/App.jsx': 'export default function App(){return <div>tree-e2e</div>;}\n',
        'src/tree-target.js': '// TREE_TARGET_UNIQUE\n',
      });

      await prepareWorkspaceSession(page, token);
      await page.goto(`/app/workspace?jobId=${encodeURIComponent(jobId)}`, { waitUntil: 'domcontentloaded' });
      await waitForUnifiedWorkspace(page);
      await clickCenterSync(page);
      await openCodeWorkspacePane(page);

      await page.getByRole('treeitem', { name: 'tree-target.js' }).click({ timeout: 20000 });
      await expect(page.locator('.wft-row--selected .wft-label').first()).toHaveText('tree-target.js');
      await expect(page.locator('.wfv-path')).toContainText('src/tree-target.js');
      await expect(page.locator('[data-testid="wfv-monaco"]')).toBeVisible({ timeout: 30000 });
      await expect(page.locator('.monaco-editor')).toContainText('TREE_TARGET_UNIQUE', { timeout: 30000 });
    } finally {
      await apiReq.dispose();
      if (root) rmWorkspaceRoot(root);
    }
  });

  test('viewer: markdown, image, and binary paths', async ({ page, playwright }) => {
    const apiReq = await apiRequestContext(playwright);
    let root;
    try {
      const health = await apiReq.get('/api/health').catch(() => null);
      test.skip(!health || !health.ok(), `No API at ${apiBase()}/api/health`);

      const gr = await apiReq.post('/api/auth/guest', { data: {} });
      expect(gr.ok()).toBeTruthy();
      const { token } = await gr.json();
      const { jobId, projectId } = await createGuidedPlanJob(apiReq, token);
      root = workspaceProjectRoot(projectId);
      seedWorkspaceTextFiles(projectId, {
        'src/App.jsx': 'export default function App(){return <div>types</div>;}\n',
        'src/crosswalk-types.md': '# CrosswalkTypesUniqueHeading\n\nhello **md**\n',
      });
      seedWorkspaceBinaryFile(projectId, 'src/crosswalk-pixel.png', tinyPngBuffer());
      seedWorkspaceBinaryFile(projectId, 'src/crosswalk.bin', Buffer.from([0, 1, 2, 255]));

      await prepareWorkspaceSession(page, token);
      await page.goto(`/app/workspace?jobId=${encodeURIComponent(jobId)}`, { waitUntil: 'domcontentloaded' });
      await waitForUnifiedWorkspace(page);
      await clickCenterSync(page);
      await openCodeWorkspacePane(page);

      await page.getByRole('treeitem', { name: 'crosswalk-types.md' }).click({ timeout: 20000 });
      await expect(page.locator('[data-testid="wfv-markdown"]')).toBeVisible({ timeout: 20000 });
      await expect(page.locator('[data-testid="wfv-markdown"]')).toContainText('CrosswalkTypesUniqueHeading');

      await page.getByRole('treeitem', { name: 'crosswalk-pixel.png' }).click({ timeout: 20000 });
      await expect(page.locator('[data-testid="wfv-image"]')).toBeVisible({ timeout: 20000 });

      await page.getByRole('treeitem', { name: 'crosswalk.bin' }).click({ timeout: 20000 });
      await expect(page.locator('[data-testid="wfv-binary"]')).toBeVisible({ timeout: 20000 });
      await expect(page.locator('[data-testid="wfv-binary"]')).toContainText('Binary file');
    } finally {
      await apiReq.dispose();
      if (root) rmWorkspaceRoot(root);
    }
  });

  test('openWorkspacePath: Timeline, Failure drawer, Proof index, Activity feed → Code pane', async ({
    page,
    playwright,
  }) => {
    const apiReq = await apiRequestContext(playwright);
    let root;
    try {
      const health = await apiReq.get('/api/health').catch(() => null);
      test.skip(!health || !health.ok(), `No API at ${apiBase()}/api/health`);

      const gr = await apiReq.post('/api/auth/guest', { data: {} });
      expect(gr.ok()).toBeTruthy();
      const { token } = await gr.json();
      const { jobId, projectId } = await createGuidedPlanJob(apiReq, token);
      root = workspaceProjectRoot(projectId);
      seedWorkspaceTextFiles(projectId, {
        'src/App.jsx': 'export default function App(){return <div>global</div>;}\n',
        'global/tl.txt': 'TL_UNIQUE\n',
        'global/fail.txt': 'FAIL_UNIQUE\n',
        'global/feed.txt': 'FEED_UNIQUE\n',
        'global/proof.txt': 'PROOF_UNIQUE\n',
      });

      await fulfillJsonRoutes(page, jobId, {
        stepsBody: syntheticSteps(jobId),
        eventsBody: syntheticEvents(jobId),
        proofBody: syntheticProof(jobId),
      });
      await patchJobGetToFailed(page, jobId);

      await prepareWorkspaceSession(page, token);
      await page.goto(`/app/workspace?jobId=${encodeURIComponent(jobId)}`, { waitUntil: 'domcontentloaded' });
      await waitForUnifiedWorkspace(page);
      await clickCenterSync(page);

      await expect(page.locator('.failure-drawer')).toBeVisible({ timeout: 30000 });
      await page.getByRole('button', { name: 'global/fail.txt' }).click();
      await assertCodePaneShowsPath(page, 'global/fail.txt');
      await expect(page.locator('[data-testid="wfv-monaco"]')).toContainText('FAIL_UNIQUE', { timeout: 20000 });

      await page.locator('.arp-pane-tabs button.arp-pane-tab').filter({ hasText: 'Proof' }).click();
      await page.getByRole('button', { name: 'global/proof.txt' }).click();
      await assertCodePaneShowsPath(page, 'global/proof.txt');
      await expect(page.locator('[data-testid="wfv-monaco"]')).toContainText('PROOF_UNIQUE', { timeout: 20000 });

      await page.getByRole('button', { name: 'global/feed.txt' }).click();
      await assertCodePaneShowsPath(page, 'global/feed.txt');
      await expect(page.locator('[data-testid="wfv-monaco"]')).toContainText('FEED_UNIQUE', { timeout: 20000 });

      await page.locator('.arp-pane-tabs button.arp-pane-tab').filter({ hasText: 'Timeline' }).click();
      await page.getByRole('button', { name: /^Jump to Code$/ }).click();
      await assertCodePaneShowsPath(page, 'global/tl.txt');
      await expect(page.locator('[data-testid="wfv-monaco"]')).toContainText('TL_UNIQUE', { timeout: 20000 });
    } finally {
      await apiReq.dispose();
      if (root) rmWorkspaceRoot(root);
    }
  });

  test('lazy file bodies: list before first body; no bulk text preload', async ({ page, playwright }) => {
    const apiReq = await apiRequestContext(playwright);
    let root;
    try {
      const health = await apiReq.get('/api/health').catch(() => null);
      test.skip(!health || !health.ok(), `No API at ${apiBase()}/api/health`);

      const gr = await apiReq.post('/api/auth/guest', { data: {} });
      expect(gr.ok()).toBeTruthy();
      const { token } = await gr.json();
      const { jobId, projectId } = await createGuidedPlanJob(apiReq, token);
      root = workspaceProjectRoot(projectId);
      seedWorkspaceTextFiles(projectId, {
        'src/App.jsx': 'export default function App(){return <div>lazy</div>;}\n',
        'src/lazy-a.txt': 'LAZY_A\n',
        'src/lazy-b.txt': 'LAZY_B\n',
        'src/lazy-c.txt': 'LAZY_C\n',
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
      await waitForUnifiedWorkspace(page);
      await clickCenterSync(page);
      await openCodeWorkspacePane(page);

      await expect(page.locator('.wft-wrap')).toBeVisible({ timeout: 20000 });
      await expect(page.locator('.wfv-path')).toContainText('src/App.jsx', { timeout: 30000 });
      await expect(page.locator('[data-testid="wfv-monaco"]')).toContainText('lazy', { timeout: 30000 });

      const iList = seq.indexOf('list');
      const iText = seq.indexOf('text');
      expect(iList, 'file list response should occur').toBeGreaterThanOrEqual(0);
      expect(iText, 'first text file body response should occur').toBeGreaterThanOrEqual(0);
      expect(iList).toBeLessThan(iText);
      expect(seq.filter((s) => s === 'text').length).toBe(1);

      await page.getByRole('treeitem', { name: 'lazy-c.txt' }).click({ timeout: 20000 });
      await expect(page.locator('.wfv-path')).toContainText('src/lazy-c.txt');
      await expect(page.locator('[data-testid="wfv-monaco"]')).toContainText('LAZY_C', { timeout: 20000 });
      expect(seq.filter((s) => s === 'text').length).toBe(2);
    } finally {
      await apiReq.dispose();
      if (root) rmWorkspaceRoot(root);
    }
  });

  test('Sync refreshes tree; prior partial file remains', async ({ page, playwright }) => {
    const apiReq = await apiRequestContext(playwright);
    let root;
    try {
      const health = await apiReq.get('/api/health').catch(() => null);
      test.skip(!health || !health.ok(), `No API at ${apiBase()}/api/health`);

      const gr = await apiReq.post('/api/auth/guest', { data: {} });
      expect(gr.ok()).toBeTruthy();
      const { token } = await gr.json();
      const { jobId, projectId } = await createGuidedPlanJob(apiReq, token);
      root = workspaceProjectRoot(projectId);
      seedWorkspaceTextFiles(projectId, {
        'partial/one.txt': 'ONE_LINE\n',
      });

      await patchJobGetToFailed(page, jobId);
      await fulfillJsonRoutes(page, jobId, {
        stepsBody: syntheticSteps(jobId),
        eventsBody: syntheticEvents(jobId),
        proofBody: syntheticProof(jobId),
      });

      await prepareWorkspaceSession(page, token);
      await page.goto(`/app/workspace?jobId=${encodeURIComponent(jobId)}`, { waitUntil: 'domcontentloaded' });
      await waitForUnifiedWorkspace(page);
      await clickCenterSync(page);
      await openCodeWorkspacePane(page);

      await expect(page.getByRole('treeitem', { name: 'one.txt' })).toBeVisible({ timeout: 20000 });

      seedWorkspaceTextFiles(projectId, {
        'partial/two.txt': 'TWO_LINE\n',
      });
      await clickCenterSync(page);

      await expect(page.getByRole('treeitem', { name: 'one.txt' })).toBeVisible({ timeout: 20000 });
      await expect(page.getByRole('treeitem', { name: 'two.txt' })).toBeVisible({ timeout: 20000 });
    } finally {
      await apiReq.dispose();
      if (root) rmWorkspaceRoot(root);
    }
  });

  test('Workspace ZIP triggers a download', async ({ page, playwright }) => {
    const apiReq = await apiRequestContext(playwright);
    let root;
    try {
      const health = await apiReq.get('/api/health').catch(() => null);
      test.skip(!health || !health.ok(), `No API at ${apiBase()}/api/health`);

      const gr = await apiReq.post('/api/auth/guest', { data: {} });
      expect(gr.ok()).toBeTruthy();
      const { token } = await gr.json();
      const { jobId, projectId } = await createGuidedPlanJob(apiReq, token);
      root = workspaceProjectRoot(projectId);
      seedWorkspaceTextFiles(projectId, {
        'src/App.jsx': 'export default function App(){return <div>zip</div>;}\n',
      });

      await prepareWorkspaceSession(page, token);
      await page.goto(`/app/workspace?jobId=${encodeURIComponent(jobId)}`, { waitUntil: 'domcontentloaded' });
      await waitForUnifiedWorkspace(page);
      await clickCenterSync(page);
      await openCodeWorkspacePane(page);

      const dl = page.waitForEvent('download', { timeout: 60000 });
      await page.locator('.code-pane-actions').getByRole('button', { name: /Workspace ZIP/ }).click();
      const download = await dl;
      const name = download.suggestedFilename();
      expect(name.toLowerCase()).toMatch(/\.zip$/);
    } finally {
      await apiReq.dispose();
      if (root) rmWorkspaceRoot(root);
    }
  });

  test('viewer toolbar trace from dag_node_completed + step roster', async ({ page, playwright }) => {
    const apiReq = await apiRequestContext(playwright);
    let root;
    try {
      const health = await apiReq.get('/api/health').catch(() => null);
      test.skip(!health || !health.ok(), `No API at ${apiBase()}/api/health`);

      const gr = await apiReq.post('/api/auth/guest', { data: {} });
      expect(gr.ok()).toBeTruthy();
      const { token } = await gr.json();
      const { jobId, projectId } = await createGuidedPlanJob(apiReq, token);
      root = workspaceProjectRoot(projectId);
      seedWorkspaceTextFiles(projectId, {
        'src/App.jsx': 'export default function App(){return <div>trace</div>;}\n',
        'src/trace-proof.txt': 'TRACE_FILE_BODY\n',
      });

      const traceStepId = 'st-trace-1';
      const traceTs = '2026-06-15T14:22:33Z';
      await fulfillJsonRoutes(page, jobId, {
        stepsBody: {
          job_id: jobId,
          steps: [
            {
              id: traceStepId,
              step_key: 'verify.files',
              agent_name: 'VerifierAgent',
              status: 'completed',
              order_index: 0,
              output_files: ['src/trace-proof.txt'],
            },
          ],
        },
        eventsBody: {
          job_id: jobId,
          events: [
            {
              id: 'ev-trace-dag',
              type: 'dag_node_completed',
              event_type: 'dag_node_completed',
              job_id: jobId,
              step_id: traceStepId,
              ts: traceTs,
              payload: {
                step_id: traceStepId,
                output_files: ['src/trace-proof.txt'],
              },
            },
          ],
        },
        proofBody: {
          job_id: jobId,
          success: true,
          bundle: {
            files: [],
            routes: [],
            database: [],
            verification: [],
            deploy: [],
            generic: [],
          },
          total_proof_items: 0,
          verification_proof_items: 0,
          quality_score: 0,
          category_counts: {},
          proof_index: { by_path: {}, by_proof_item_id: {} },
        },
      });

      await prepareWorkspaceSession(page, token);
      await page.goto(`/app/workspace?jobId=${encodeURIComponent(jobId)}`, { waitUntil: 'domcontentloaded' });
      await waitForUnifiedWorkspace(page);
      await clickCenterSync(page);
      await openCodeWorkspacePane(page);

      await page.getByRole('treeitem', { name: 'trace-proof.txt' }).click({ timeout: 20000 });
      await expect(page.locator('.wfv-path')).toContainText('src/trace-proof.txt');

      const traceEl = page.locator('.wfv-toolbar .wfv-trace').filter({ hasText: 'VerifierAgent' });
      await expect(traceEl).toBeVisible({ timeout: 20000 });
      await expect(traceEl).toContainText('verify.files');
      await expect(traceEl).toHaveAttribute('title', new RegExp(`Step\\s+${traceStepId}`));
      await expect(traceEl).toHaveAttribute('title', /2026-06-15T14:22:33/);
    } finally {
      await apiReq.dispose();
      if (root) rmWorkspaceRoot(root);
    }
  });
});
