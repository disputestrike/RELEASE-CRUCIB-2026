/**
 * Virtual Filesystem — isolated layers per spawn agent
 * In-memory workspace isolation without requiring git.
 * Each spawn branch gets its own copy-on-write layer. Merges are explicit and visible.
 */

export class VirtualFS {
  constructor() {
    this.layers = new Map(); // agentId -> { base, changes }
  }

  createLayer(agentId, baseFiles = {}) {
    this.layers.set(agentId, {
      base: { ...baseFiles },
      changes: [],
    });
  }

  commitChange(agentId, change) {
    const layer = this.layers.get(agentId);
    if (!layer) throw new Error(`Layer ${agentId} not found`);
    layer.changes.push({ ...change, timestamp: Date.now() });
  }

  getLayerState(agentId) {
    const layer = this.layers.get(agentId);
    if (!layer) throw new Error(`Layer ${agentId} not found`);
    const state = { ...layer.base };
    for (const c of layer.changes) {
      if (c.action === 'delete') delete state[c.path];
      else state[c.path] = c.content || '';
    }
    return state;
  }

  mergeLayer(agentId, target) {
    const layer = this.layers.get(agentId);
    if (!layer) return { conflicts: [], merged: target };
    
    const conflicts = [];
    const merged = { ...target };
    
    for (const c of layer.changes) {
      const targetCurrent = merged[c.path];
      const baseVersion = layer.base[c.path];
      
      // Conflict: target changed the file AND our branch changed it differently
      if (targetCurrent !== undefined &&
          targetCurrent !== baseVersion &&
          c.action !== 'delete') {
        conflicts.push({
          path: c.path,
          base: baseVersion || '',
          ours: c.content || '',
          theirs: targetCurrent,
        });
      } else {
        if (c.action === 'delete') delete merged[c.path];
        else if (c.content !== undefined) merged[c.path] = c.content;
      }
    }
    
    this.layers.delete(agentId);
    return { conflicts, merged };
  }

  deleteLayer(agentId) {
    this.layers.delete(agentId);
  }

  getLayerCount() {
    return this.layers.size;
  }

  getActiveLayers() {
    return Array.from(this.layers.keys());
  }
}

export const virtualFS = new VirtualFS();
