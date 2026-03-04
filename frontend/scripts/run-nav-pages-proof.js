#!/usr/bin/env node
/**
 * Run Nav & Pages click-through tests and write proof to docs/NAV_AND_PAGES_PROOF.md (test result section).
 * Usage: from repo root, node frontend/scripts/run-nav-pages-proof.js
 * Or from frontend: node scripts/run-nav-pages-proof.js
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const frontendDir = path.join(__dirname, '..');
const repoRoot = path.join(frontendDir, '..');
const proofPath = path.join(repoRoot, 'docs', 'NAV_AND_PAGES_PROOF.md');

process.chdir(frontendDir);
let output;
try {
  output = execSync(
    'npm test -- --testPathPattern="NavAndPagesClickThrough" --watchAll=false --no-cache 2>&1',
    { encoding: 'utf8', timeout: 60000 }
  );
} catch (e) {
  output = (e.stdout || '') + (e.stderr || '');
}

const proofContent = fs.readFileSync(proofPath, 'utf8');
const marker = '## 4. Last test run (evidence)';
const nextSection = '## 5. Summary';
const idx = proofContent.indexOf(marker);
const endIdx = proofContent.indexOf(nextSection, idx);
if (idx === -1 || endIdx === -1) {
  console.log('Proof doc structure changed; skipping update.');
  process.exit(output.includes('Tests:') && output.includes('passed') ? 0 : 1);
}

const before = proofContent.slice(0, idx + marker.length);
const after = proofContent.slice(endIdx);
const newSection = '\n\n```\n' + output.trim() + '\n```\n\n';
const updated = before + newSection + after;
fs.writeFileSync(proofPath, updated);
console.log('Updated', proofPath, 'with latest test output.');
process.exit(output.includes('10 passed') && output.includes('1 passed') ? 0 : 1);
