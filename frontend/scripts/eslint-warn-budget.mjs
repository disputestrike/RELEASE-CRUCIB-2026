/**
 * Fail if ESLint warning count for src/ exceeds ESLINT_WARN_BUDGET (default 50).
 */
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const budget = Number(process.env.ESLINT_WARN_BUDGET || "50");

let raw = "";
try {
  raw = execSync("npx eslint src -f json", {
    encoding: "utf8",
    cwd: root,
    maxBuffer: 32 * 1024 * 1024,
    stdio: ["ignore", "pipe", "pipe"],
  });
} catch (e) {
  raw = typeof e.stdout === "string" ? e.stdout : e.stdout?.toString?.() || "";
  if (!raw) {
    console.error(e.stderr?.toString?.() || e.message || e);
    process.exit(1);
  }
}

const results = JSON.parse(raw);
let warnings = 0;
for (const f of results) {
  for (const m of f.messages || []) {
    if (m.severity === 1) warnings += 1;
  }
}

if (warnings > budget) {
  console.error(`ESLint warnings ${warnings} exceed budget ${budget} (set ESLINT_WARN_BUDGET).`);
  process.exit(1);
}
console.log(`ESLint warning budget OK: ${warnings} <= ${budget}`);
