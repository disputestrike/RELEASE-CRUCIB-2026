// CF17 — Legacy pages manifest.
//
// Machine-readable version of docs/phase2/LEGACY_PAGES_INVENTORY.md. Imported
// by route guards and admin tooling so we can see disposition at runtime and
// log usage of pages flagged for deletion/migration.

export const LEGACY_PAGE_MANIFEST = {
  version: '2026-04-20.legacy-pages.v1',
  canonical_workspace: 'WorkspaceV3Shell',
  dispositions: {
    keep: 'canonical — stays',
    migrate: 'fold into WorkspaceV3Shell',
    'keep-behind-flag': 'retained for rollback behind feature flag',
    delete: 'superseded — remove next release cycle',
  },
  pages: [
    { file: 'AdminPanel.tsx',                       disposition: 'delete',            reason: 'superseded by AdminDashboard' },
    { file: 'Builder.jsx',                          disposition: 'delete',            reason: '/builder redirects to /app/workspace' },
    { file: 'UnifiedWorkspace.jsx',                 disposition: 'delete',            reason: 'superseded by WorkspaceV3Shell' },
    { file: '__tests__/UnifiedWorkspaceSurfaceMode.test.js', disposition: 'delete',   reason: 'test for deleted UnifiedWorkspace' },
    { file: 'AgentMonitor.jsx',                     disposition: 'migrate',           reason: 'fold into Workspace-V3 rail monitor' },
    { file: 'AgentsPage.jsx',                       disposition: 'migrate',           reason: 'new Agents tab inside Workspace-V3' },
    { file: 'EnvPanel.jsx',                         disposition: 'migrate',           reason: 'fold env editor into Settings' },
    { file: 'ProjectBuilder.jsx',                   disposition: 'migrate',           reason: 'reduce to trigger inside shell' },
    { file: 'UnifiedIDEPage.jsx',                   disposition: 'keep-behind-flag',  reason: 'power-user IDE; keep until V3 fully ships' },
    { file: 'WorkspaceVNext.jsx',                   disposition: 'keep-behind-flag',  reason: 'REACT_APP_WORKSPACE_LEGACY fallback' },
  ],
};

export function pageDispositionFor(filename) {
  const hit = LEGACY_PAGE_MANIFEST.pages.find((p) => p.file === filename);
  return hit ? hit.disposition : 'keep';
}

export function shouldWarnOnMount(filename) {
  const d = pageDispositionFor(filename);
  return d === 'delete' || d === 'migrate';
}
