/**
 * One Workspace thread: Home + Workspace reuse the same build task row and job steer path
 * unless the user starts a truly new session ("New").
 */

const STORAGE_KEY = 'crucibai_canonical_workspace_task_id';

export function getCanonicalWorkspaceTaskIdFromStorage() {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return v != null && String(v).trim() ? String(v).trim() : null;
  } catch {
    return null;
  }
}

export function setCanonicalWorkspaceTaskId(taskId) {
  if (!taskId) return;
  try {
    localStorage.setItem(STORAGE_KEY, String(taskId));
  } catch {
    /* ignore */
  }
}

export function clearCanonicalWorkspaceTaskId() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

const OPEN_BUILD_STATUSES = new Set([
  'pending',
  'planned',
  'running',
  'queued',
  'blocked',
  'failed',
  'cancelled',
]);

export function pickOngoingWorkspaceBuildTask(storeTasks) {
  const tasks = Array.isArray(storeTasks) ? storeTasks : [];
  const canon = getCanonicalWorkspaceTaskIdFromStorage();
  if (canon) {
    const t = tasks.find(
      (x) => String(x?.id) === canon && String(x?.type || 'build').toLowerCase() === 'build',
    );
    if (t) return { task: t, id: canon, mode: 'canonical' };
  }
  const incomplete = [];
  for (const t of tasks) {
    if (!t || String(t.type || 'build').toLowerCase() !== 'build') continue;
    const s = String(t.status || '').toLowerCase();
    if (OPEN_BUILD_STATUSES.has(s)) incomplete.push(t);
  }
  incomplete.sort((a, b) => (b.createdAt ?? 0) - (a.createdAt ?? 0));
  if (incomplete[0]) {
    const t = incomplete[0];
    return { task: t, id: t.id, mode: 'open_fallback' };
  }
  return { task: null, id: null, mode: 'none' };
}

/**
 * Reuse the canonical (or newest open) build row so Recent shows one Workspace thread until "New".
 */
export function reuseOrCreateWorkspaceBuildTask({
  storeTasks,
  addTask,
  updateTask,
  name,
  prompt,
  status = 'pending',
}) {
  const picked = pickOngoingWorkspaceBuildTask(storeTasks);
  if (picked.id != null && picked.task) {
    updateTask(String(picked.id), {
      name: name != null ? String(name).slice(0, 120) : picked.task.name,
      ...(prompt !== undefined ? { prompt } : {}),
      status,
      type: 'build',
    });
    setCanonicalWorkspaceTaskId(String(picked.id));
    return String(picked.id);
  }
  const tid = addTask({
    name: String(name ?? 'Build').slice(0, 120),
    ...(prompt !== undefined ? { prompt: String(prompt) } : { prompt: '' }),
    status,
    type: 'build',
  });
  if (tid) setCanonicalWorkspaceTaskId(String(tid));
  return tid ?? null;
}
