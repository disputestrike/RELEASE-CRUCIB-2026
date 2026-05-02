#!/usr/bin/env node
/**
 * Strongest automated crosswalk verification (no browser).
 * From repo root: node scripts/verify-workspace-crosswalk.mjs
 *
 * Browser E2E (separate; needs API + auth + UI):
 *   cd frontend && npm run e2e:workspace-preview
 *   cd frontend && npm run e2e:workspace-crosswalk
 */
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');
const backend = path.join(root, 'backend');
const frontend = path.join(root, 'frontend');

function run(cwd, cmd, args, label) {
  console.log(`\n--- ${label} ---`);
  const r = spawnSync(cmd, args, { cwd, stdio: 'inherit', shell: true });
  if (r.status !== 0) {
    console.error(`FAIL: ${label} (exit ${r.status})`);
    process.exit(r.status ?? 1);
  }
  console.log(`OK: ${label}`);
}

run(backend, 'python', ['-m', 'pytest', 'tests/test_job_workspace.py', '-v', '--tb=line'], 'backend pytest tests/test_job_workspace.py');

run(frontend, 'npx', ['eslint', 'src/pages/CrucibAIWorkspace.jsx', 'src/workspace10/normalizeSseEvent.js', 'src/workspace10/agentLogs.js', 'src/workspace/workspaceFileUtils.js', 'src/components/AutoRunner/WorkspaceFileTree.jsx', 'src/components/AutoRunner/WorkspaceFileViewer.jsx', 'src/components/AutoRunner/ProofPanel.jsx', 'src/components/AutoRunner/FailureDrawer.jsx', 'src/components/AutoRunner/SystemExplorer.jsx', 'src/components/AutoRunner/WorkspaceActivityFeed.jsx', '--max-warnings', '0'], 'frontend eslint (workspace slice)');

run(frontend, 'npx', ['craco', 'test', '--watchAll=false', '--testPathPattern=workspaceFileUtils'], 'frontend jest workspaceFileUtils');

console.log('\nAll automated steps passed.');
console.log('Optional: cd frontend && npx cross-env DISABLE_ESLINT_PLUGIN=true npx craco build');
console.log('Browser E2E: cd frontend && npm run e2e:workspace-preview');
console.log('Browser E2E (workspace Code crosswalk): cd frontend && npm run e2e:workspace-crosswalk');
