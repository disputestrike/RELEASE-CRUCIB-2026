export function normalizeWorkspacePath(p) {
  const s = String(p || '').trim().replace(/\\/g, '/').replace(/^\/+/, '');
  return s ? `/${s}` : '';
}

export function isWorkspaceDbPath(relPath) {
  const p = String(relPath || '').replace(/\\/g, '/').toLowerCase();
  return (
    p.endsWith('.sql')
    || p.includes('schema')
    || p.includes('migration')
    || p.includes('/db/')
    || p.includes('knexfile')
    || p.endsWith('prisma/schema.prisma')
  );
}

export function isWorkspaceDocPath(relPath) {
  const p = String(relPath || '').replace(/\\/g, '/').toLowerCase();
  return p.endsWith('.md') || p.endsWith('.mdx');
}

export function docSortKey(relPath) {
  const n = String(relPath || '').toLowerCase();
  if (/readme/i.test(n)) return 0;
  if (n.startsWith('docs/')) return 1;
  return 2;
}

export function extractSqlTableNames(sql) {
  const s = sql || '';
  return [...s.matchAll(/CREATE TABLE(?:\s+IF NOT EXISTS)?\s+"?(\w+)"?/gi)].map((m) => m[1]).filter(Boolean);
}
