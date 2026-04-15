/**
 * Spawn Engine — parallel agent execution with virtualFS isolation
 * Frontend coordinates spawn; backend does the real work at /api/spawn/run
 */
import { eventBus } from './eventBus';
import { virtualFS } from './virtualFS';

export class SpawnEngine {
  constructor(jobId) {
    this.jobId = jobId;
  }

  async spawn(task, config = {}, context = {}, currentFiles = {}) {
    const branches = Math.min(config.branches || 4, 16);
    const strategy = config.strategy || 'diverse_priors';
    const aggregation = config.aggregation || 'consensus';
    const BASE = import.meta?.env?.VITE_BACKEND_URL || '';

    eventBus.emitLocal({ type: 'milestone.reached', jobId: this.jobId,
      timestamp: Date.now(), payload: { title: `Spawning ${branches} agents`, strategy } });

    const subagents = Array.from({ length: branches }, (_, i) => ({
      id: crypto.randomUUID(),
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
