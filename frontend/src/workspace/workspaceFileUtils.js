/**
 * Workspace file paths + trace index helpers (API-first; no Sandpack as tree source).
 */

import axios from 'axios';

/** Posix path without leading slash — matches backend query param. */
export function normalizeWorkspacePath(p) {
  if (p == null || typeof p !== 'string') return '';
  return p
    .replace(/\\/g, '/')
    .replace(/\/+/g, '/')
    .replace(/^\/+/, '')
    .trim();
}

export function toEditorPath(posixNoLeading) {
  const n = normalizeWorkspacePath(posixNoLeading);
  if (!n) return '/';
  return `/${n}`;
}

const IMAGE_EXT = /\.(png|jpe?g|gif|webp|svg|ico|bmp)$/i;

export function guessViewerKind(posixPath) {
  const p = normalizeWorkspacePath(posixPath);
  if (!p) return 'text';
  if (IMAGE_EXT.test(p)) return 'image';
  if (/\.(zip|gz|tar|wasm|bin|exe|dll|so|dylib|pdf)$/i.test(p)) return 'binary';
  if (/\.(woff2?|ttf|eot)$/i.test(p)) return 'binary';
  return 'text';
}

/**
 * Fetch every page of GET .../workspace/files (bounded pages; non-blocking per request).
 */
export async function fetchAllWorkspaceFilePaths(listUrl, headers, pageSize = 500) {
  const all = [];
  let offset = 0;
  let guard = 0;
  const maxPages = 200;
  while (guard < maxPages) {
    guard += 1;
    const r = await axios.get(listUrl, { headers, params: { offset, limit: pageSize } });
    const batch = r.data?.files;
    if (!Array.isArray(batch)) break;
    for (const row of batch) {
      if (typeof row === 'string') all.push(normalizeWorkspacePath(row));
      else if (row && typeof row.path === 'string') all.push(normalizeWorkspacePath(row.path));
    }
    if (!r.data?.has_more) break;
    const next = r.data?.next_offset;
    offset = typeof next === 'number' ? next : offset + batch.length;
  }
  return [...new Set(all.filter(Boolean))].sort((a, b) => a.localeCompare(b));
}

/**
 * Last writer per path from real dag_node_completed events + step roster (no fabricated mapping).
 */
export function buildTraceIndexFromEvents(events, steps) {
  const byPath = {};
  const stepById = new Map((steps || []).map((s) => [String(s.id), s]));
  const ordered = [...(events || [])].sort((a, b) => {
    const ta = new Date(a.ts || a.created_at || 0).getTime();
    const tb = new Date(b.ts || b.created_at || 0).getTime();
    return ta - tb;
  });
  for (const ev of ordered) {
    const t = ev.type || ev.event_type;
    if (t !== 'dag_node_completed') continue;
    const payload = ev.payload && typeof ev.payload === 'object' ? ev.payload : {};
    const sid = String(payload.step_id || ev.step_id || '');
    const step = stepById.get(sid);
    const agent = step?.agent_name || payload.agent_name || '';
    const stepKey = step?.step_key || payload.step_key || '';
    const ts = ev.ts || ev.created_at || '';
    const eventId = String(ev.id ?? '');
    const files = payload.output_files;
    if (!Array.isArray(files)) continue;
    for (const fp of files) {
      const rel = normalizeWorkspacePath(String(fp));
      if (!rel) continue;
      byPath[rel] = {
        agent,
        step_key: stepKey,
        step_id: sid,
        ts,
        event_id: eventId,
      };
    }
  }
  return byPath;
}

export function pathsToNestedTree(paths) {
  const root = { name: '', segment: '', children: new Map(), isFile: false };
  for (const raw of paths || []) {
    const p = normalizeWorkspacePath(raw);
    if (!p) continue;
    const parts = p.split('/').filter(Boolean);
    let cur = root;
    parts.forEach((part, i) => {
      const isLast = i === parts.length - 1;
      if (!cur.children.has(part)) {
        cur.children.set(part, { name: part, segment: part, children: new Map(), isFile: isLast });
      }
      const node = cur.children.get(part);
      if (isLast) node.isFile = true;
      else node.isFile = false;
      cur = node;
    });
  }
  return root;
}
