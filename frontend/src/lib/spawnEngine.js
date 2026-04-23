/**
 * Spawn Engine — parallel agent execution with virtualFS isolation
 * Frontend coordinates spawn; backend does the real work at /api/spawn/run
 */
import { eventBus } from './eventBus';
import { virtualFS } from './virtualFS';

function normalizeBranchCount(raw, fallback = 4) {
  const n = Number(raw);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(1, Math.floor(n));
}

function makeId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `sa_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export class SpawnEngine {
  constructor(jobId) {
    this.jobId = jobId;
  }

  async spawn(task, config = {}, context = {}, currentFiles = {}) {
    const branches = normalizeBranchCount(config.branches || 4, 4);
    const strategy = config.strategy || 'diverse_priors';
    const aggregation = config.aggregation || 'consensus';
    const BASE = (typeof process !== 'undefined' && process.env?.REACT_APP_API_URL) || '';

    eventBus.emitLocal({ type: 'milestone.reached', jobId: this.jobId,
      timestamp: Date.now(), payload: { title: `Spawning ${branches} agents`, strategy } });

    const subagents = Array.from({ length: branches }, (_, i) => ({
      id: makeId(),
      role: this._role(strategy, i, branches),
    }));

    subagents.forEach(a => {
      virtualFS.createLayer(a.id, currentFiles);
      eventBus.emitLocal({ type: 'subagent.started', jobId: this.jobId,
        timestamp: Date.now(), payload: { subagentId: a.id, role: a.role } });
    });

    const results = await Promise.all(subagents.map(async (agent) => {
      try {
        const res = await fetch(`${BASE}/api/spawn/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ jobId: this.jobId, subagentId: agent.id, task, config, context }),
        });
        const data = await res.json();
        if (data.files) {
          Object.entries(data.files).forEach(([path, content]) =>
            virtualFS.commitChange(agent.id, { path, action: 'modify', content }));
        }
        eventBus.emitLocal({ type: 'subagent.complete', jobId: this.jobId,
          timestamp: Date.now(), payload: { subagentId: agent.id } });
        return { id: agent.id, status: 'complete', result: data };
      } catch (err) {
        virtualFS.deleteLayer(agent.id);
        eventBus.emitLocal({ type: 'subagent.failed', jobId: this.jobId,
          timestamp: Date.now(), payload: { subagentId: agent.id, error: String(err) } });
        return { id: agent.id, status: 'failed' };
      }
    }));

    let mergedFiles = { ...currentFiles };
    let allConflicts = [];
    results.forEach(r => {
      if (r.status === 'complete') {
        const { conflicts, merged } = virtualFS.mergeLayer(r.id, mergedFiles);
        mergedFiles = merged;
        allConflicts.push(...conflicts);
      } else {
        virtualFS.deleteLayer(r.id);
      }
    });

    const success = results.filter(r => r.status === 'complete').length;
    const confidence = success / results.length;
    return {
      consensus: results.find(r => r.status === 'complete')?.result || null,
      confidence,
      successCount: success,
      mergedFiles,
      conflicts: allConflicts,
      subagentResults: results,
    };
  }

  _role(strategy, i, total) {
    const maps = {
      diverse_priors: ['architect','engineer','reviewer','optimizer'],
      role_based: ['frontend','backend','database','security'],
      adversarial: ['proponent','critic','neutral','synthesizer'],
      optimistic_pessimistic: ['optimist','pessimist','realist','pragmatist'],
    };
    const list = maps[strategy] || maps.diverse_priors;
    return list[i % list.length];
  }
}

export async function runParallelSpawnProbe({
  jobId,
  task,
  currentFiles = {},
  axios,
  API,
  token,
  postSpawn,
  createDiskLayers = true,
  branches = 4,
  mode = 'swan',
}) {
  const branchCount = normalizeBranchCount(branches, 4);
  const subagentIds = Array.from({ length: branchCount }, () => makeId());

  const cleanupWorktreeIds = [];
  if (createDiskLayers && axios && API && token) {
    await Promise.all(
      subagentIds.map(async (id) => {
        const wid = `spawn-${String(jobId || 'job')}-${id.slice(0, 10)}`;
        try {
          await axios.post(
            `${API}/worktrees/create`,
            { id: wid },
            { headers: { Authorization: `Bearer ${token}` } },
          );
          cleanupWorktreeIds.push(wid);
        } catch {
          // Worktree creation is best-effort.
        }
      }),
    );
  }

  const doPost =
    typeof postSpawn === 'function'
      ? postSpawn
      : (body) =>
          axios.post(`${API}/spawn/run`, body, {
            headers: { Authorization: `Bearer ${token}` },
          });

  const body = {
    jobId,
    task,
    config: { branches: branchCount, mode },
    context: { subagent_ids: subagentIds },
  };

  const response = await doPost(body);
  const payload = response?.data || {};
  const subagentResults = Array.isArray(payload.subagentResults) ? payload.subagentResults : [];

  let mergedFiles = { ...currentFiles };
  const mergeConflicts = [];

  subagentResults.forEach((r) => {
    const sid = r?.id;
    if (!sid) return;
    virtualFS.createLayer(sid, mergedFiles);
    const changedFiles = r?.result?.files;
    if (changedFiles && typeof changedFiles === 'object') {
      Object.entries(changedFiles).forEach(([path, content]) => {
        virtualFS.commitChange(sid, { path, action: 'modify', content: String(content ?? '') });
      });
    }
    const merged = virtualFS.mergeLayer(sid, mergedFiles);
    mergedFiles = merged.merged;
    if (Array.isArray(merged.conflicts) && merged.conflicts.length) {
      mergeConflicts.push(...merged.conflicts);
    }
  });

  if (createDiskLayers && axios && API && token && cleanupWorktreeIds.length) {
    await Promise.all(
      cleanupWorktreeIds.map(async (wid) => {
        try {
          await axios.post(
            `${API}/worktrees/delete`,
            { id: wid },
            { headers: { Authorization: `Bearer ${token}` } },
          );
        } catch {
          // Best-effort cleanup.
        }
      }),
    );
  }

  return {
    ...payload,
    mergedFiles,
    mergeConflicts,
    subagentResults,
    swarm: {
      mode,
      requestedBranches: branchCount,
      actualBranches: subagentResults.length || branchCount,
      ...(payload.swarm || {}),
    },
  };
}
