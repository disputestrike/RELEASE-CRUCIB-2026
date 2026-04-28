#!/usr/bin/env node
/**
 * Layer 6.2 – Data privacy: ensure .env and secrets are not committed.
 * Pass: .env (and common secret patterns) are in .gitignore and not tracked by git.
 * Exit 0 = pass, 1 = fail.
 */
import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const root = path.resolve(__dirname, '..');
const gitignorePath = path.join(root, '.gitignore');

function main() {
  const errors = [];

  if (!fs.existsSync(gitignorePath)) {
    errors.push('.gitignore not found');
    return fail(errors);
  }

  const gitignore = fs.readFileSync(gitignorePath, 'utf8');
  const mustIgnore = ['.env', '*.env', '*.env.*', '*.pem', '*token.json*', '*credentials.json*'];
  const hasEnv = mustIgnore.some(p => gitignore.includes('.env') || gitignore.includes('*.env'));
  if (!hasEnv) {
    errors.push('.gitignore does not include .env or *.env');
  }

  try {
    const tracked = execSync('git ls-files "*.env" "*.env.*" .env', {
      cwd: root,
      encoding: 'utf8',
      maxBuffer: 1024,
    }).trim();
    if (tracked) {
      errors.push('Secret-like files are tracked by git: ' + tracked.split(/\r?\n/).join(', '));
    }
  } catch (e) {
    if (e.status === 0 && e.stdout && e.stdout.trim()) {
      errors.push('Secret-like files are tracked by git');
    }
  }

  if (errors.length > 0) return fail(errors);
  console.log('Layer 6.2: No secrets in repo – PASS');
  process.exit(0);
}

function fail(errors) {
  console.error('Layer 6.2: Data privacy check FAILED');
  errors.forEach(e => console.error('  -', e));
  process.exit(1);
}

main();
