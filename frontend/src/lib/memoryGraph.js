/**
 * Memory Graph — 5-layer dynamic memory with relevance decay
 * Transparent, searchable memory graph for the UI.
 * 
 * Layers:
 *   user     — preferences, style, defaults (persists forever)
 *   project  — stack decisions, architecture (persists per project)
 *   session  — current build state, active agents (clears on new build)
 *   pattern  — recurring fixes, successful patterns (grows over time)
 *   synthesis — AI-ranked cross-scope insights (auto-generated)
 */

const SCOPES = ['user', 'project', 'session', 'pattern', 'synthesis'];
const MAX_NODES_PER_SCOPE = 200;
const DECAY_RATE = 0.1; // relevance decay per day

export class MemoryGraph {
  constructor() {
    this.nodes = { user: [], project: [], session: [], pattern: [], synthesis: [] };
  }

  async save(scope, key, content, importance = 0.5) {
    if (!SCOPES.includes(scope)) return null;
    const existing = this.nodes[scope].find(n => n.key === key);
    const now = Date.now();
    
    const node = existing ? {
      ...existing,
      content,
      metadata: {
        ...existing.metadata,
        lastAccessed: now,
        accessCount: existing.metadata.accessCount + 1,
        importance: Math.max(existing.metadata.importance, importance),
      }
    } : {
      id: crypto.randomUUID(),
      scope,
      key,
      content,
      metadata: {
        createdAt: now,
        lastAccessed: now,
        accessCount: 1,
        relevance: 0.8,
        importance,
      }
    };

    this.nodes[scope] = this.nodes[scope].filter(n => n.key !== key).concat(node);
    this._updateRelevance(scope);
    this._prune(scope);
    this._persist(scope);
    return node;
  }

  async get(scope, key) {
    const node = this.nodes[scope]?.find(n => n.key === key);
    if (node) {
      node.metadata.lastAccessed = Date.now();
      node.metadata.accessCount++;
    }
    return node || null;
  }

  _updateRelevance(scope) {
    const now = Date.now();
    this.nodes[scope].forEach(n => {
      const daysSinceAccess = (now - n.metadata.lastAccessed) / (1000 * 60 * 60 * 24);
      n.metadata.relevance = Math.max(
        0.05,
        n.metadata.importance * Math.exp(-DECAY_RATE * daysSinceAccess)
      );
    });
  }

  _prune(scope) {
    this.nodes[scope] = this.nodes[scope]
      .filter(n => n.metadata.relevance > 0.05 || n.metadata.accessCount > 3)
      .sort((a, b) => b.metadata.relevance - a.metadata.relevance)
      .slice(0, MAX_NODES_PER_SCOPE);
  }

  _persist(scope) {
    try {
      localStorage.setItem(`crucibai_memory_${scope}`, JSON.stringify(this.nodes[scope]));
    } catch {}
  }

  async loadAll() {
    SCOPES.forEach(scope => {
      try {
        const saved = localStorage.getItem(`crucibai_memory_${scope}`);
        if (saved) this.nodes[scope] = JSON.parse(saved);
      } catch {}
    });
    // Refresh relevance after loading
    SCOPES.forEach(s => this._updateRelevance(s));
  }

  async search(query, scope = null) {
    const lower = query.toLowerCase();
    const target = scope
      ? (this.nodes[scope] || [])
      : Object.values(this.nodes).flat();
    
    return target
      .filter(n => {
        const contentStr = typeof n.content === 'string'
          ? n.content : JSON.stringify(n.content);
        return contentStr.toLowerCase().includes(lower) ||
               n.key.toLowerCase().includes(lower);
      })
      .sort((a, b) => b.metadata.relevance - a.metadata.relevance)
      .slice(0, 10);
  }

  exportGraph() {
    return { ...this.nodes };
  }

  getStats() {
    const stats = {};
    let total = 0;
    SCOPES.forEach(s => {
      const nodes = this.nodes[s];
      stats[s] = {
        count: nodes.length,
        highRelevance: nodes.filter(n => n.metadata.relevance > 0.7).length,
      };
      total += nodes.length;
    });
    return { ...stats, total };
  }

  clearScope(scope) {
    this.nodes[scope] = [];
    try { localStorage.removeItem(`crucibai_memory_${scope}`); } catch {}
  }
}

export const memoryGraph = new MemoryGraph();
