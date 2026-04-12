/**
 * Shared helpers for UnifiedWorkspace Playwright specs (API-rooted fetch + disk seeding).
 */
const fs = require('fs');
const path = require('path');

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

async function waitForUnifiedWorkspace(page) {
  await page.waitForSelector('[data-testid="unified-workspace-root"]', { timeout: 90000 });
}

async function openCodeWorkspacePane(page) {
  await waitForUnifiedWorkspace(page);
  await page.getByRole('button', { name: 'Dev' }).click({ timeout: 15000 }).catch(() => {});
  await page.locator('.arp-pane-tabs').getByRole('button', { name: 'Code', exact: true }).click({ timeout: 15000 });
  await page.waitForSelector('.code-pane-main', { timeout: 20000 });
}

function workspaceProjectRoot(projectId) {
  const safe = String(projectId).replace(/\//g, '_').replace(/\\/g, '_');
  return path.join(__dirname, '..', '..', '..', 'backend', 'workspace', safe);
}

/** Write UTF-8 text files under backend/workspace/<projectId>/ */
function seedWorkspaceTextFiles(projectId, relToContent) {
  const root = workspaceProjectRoot(projectId);
  for (const [rel, content] of Object.entries(relToContent)) {
    const full = path.join(root, ...rel.split('/'));
    fs.mkdirSync(path.dirname(full), { recursive: true });
    fs.writeFileSync(full, content, 'utf8');
  }
  return root;
}

function seedWorkspaceBinaryFile(projectId, relPath, buf) {
  const root = workspaceProjectRoot(projectId);
  const full = path.join(root, ...relPath.split('/'));
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, buf);
  return root;
}

function rmWorkspaceRoot(root) {
  try {
    fs.rmSync(root, { recursive: true, force: true });
  } catch {
    /* ignore */
  }
}

/** Minimal 1×1 PNG (transparent). */
function tinyPngBuffer() {
  return Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
    'base64',
  );
}

/**
 * Merge job GET to `failed` and optionally override fields; keep steps/events/proof on the wire
 * unless you add other routes.
 */
async function patchJobGetToFailed(page, jobId) {
  await page.route(
    (url) => {
      const s = url.href || String(url);
      const needle = `/api/jobs/${jobId}`;
      const i = s.indexOf(needle);
      if (i < 0) return false;
      const rest = s.slice(i + needle.length);
      if (rest !== '' && !rest.startsWith('?') && !rest.startsWith('#')) return false;
      return true;
    },
    async (route) => {
      const req = route.request();
      if (req.method() !== 'GET') {
        await route.continue();
        return;
      }
      const res = await route.fetch();
      let j;
      try {
        j = await res.json();
      } catch {
        await route.fulfill({ response: res });
        return;
      }
      const job = j.job ?? j;
      const nextJob = { ...job, status: 'failed' };
      const body = j.job !== undefined ? { ...j, job: nextJob } : nextJob;
      await route.fulfill({
        status: res.status(),
        contentType: 'application/json',
        body: JSON.stringify(body),
      });
    },
  );
}

function syntheticSteps(jobId) {
  return {
    steps: [
      {
        id: 'e2e-step-fail-1',
        step_key: 'e2e.fail_step',
        agent_name: 'E2EAgent',
        status: 'failed',
        order_index: 0,
        output_files: ['global/tl.txt', 'global/fail.txt'],
        error_message: 'E2E simulated failure',
        retry_count: 0,
        started_at: '2026-01-01T12:00:00Z',
        created_at: '2026-01-01T12:00:00Z',
      },
    ],
    job_id: jobId,
  };
}

function syntheticEvents(jobId) {
  return {
    events: [
      {
        id: 'e2e-ev-dag-1',
        type: 'dag_node_completed',
        event_type: 'dag_node_completed',
        job_id: jobId,
        step_id: 'e2e-step-fail-1',
        ts: '2026-01-01T12:01:00Z',
        payload: { output_files: ['global/feed.txt'] },
      },
    ],
    job_id: jobId,
  };
}

function syntheticProof(jobId) {
  return {
    job_id: jobId,
    success: true,
    bundle: {
      files: [{ id: 'pf1', type: 'generic', payload: { note: 'e2e' } }],
      routes: [],
      database: [],
      verification: [],
      deploy: [],
      generic: [],
    },
    total_proof_items: 1,
    verification_proof_items: 0,
    quality_score: 1,
    category_counts: { generic: 1 },
    proof_index: {
      by_path: {
        'global/proof.txt': [{ id: 'pf1', type: 'generic' }],
      },
      by_proof_item_id: {},
    },
  };
}

async function fulfillJsonRoutes(page, jobId, { stepsBody, eventsBody, proofBody }) {
  await page.route(`**/api/jobs/${jobId}/steps**`, async (route) => {
    if (route.request().method() !== 'GET') {
      await route.continue();
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(stepsBody) });
  });
  await page.route(`**/api/jobs/${jobId}/events**`, async (route) => {
    if (route.request().method() !== 'GET') {
      await route.continue();
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(eventsBody) });
  });
  await page.route(`**/api/jobs/${jobId}/proof**`, async (route) => {
    if (route.request().method() !== 'GET') {
      await route.continue();
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(proofBody) });
  });
}

module.exports = {
  e2eBuildTarget,
  apiBase,
  apiRequestContext,
  waitForUnifiedWorkspace,
  openCodeWorkspacePane,
  workspaceProjectRoot,
  seedWorkspaceTextFiles,
  seedWorkspaceBinaryFile,
  rmWorkspaceRoot,
  tinyPngBuffer,
  patchJobGetToFailed,
  syntheticSteps,
  syntheticEvents,
  syntheticProof,
  fulfillJsonRoutes,
};
