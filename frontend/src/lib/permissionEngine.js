/**
 * Permission Engine — trust tiers + persistent rules + risk-aware approval
 * Beats Claude Code's hidden ML inference by being transparent and user-controlled
 * 
 * Trust tiers: safe → verified → untrusted → dangerous
 * Rules persist in localStorage and evolve with usage
 */

const TRUST_TIERS = { safe: 0.9, verified: 0.7, untrusted: 0.4, dangerous: 0 };

export class PermissionEngine {
  constructor() {
    this.rules = new Map();
  }

  async load() {
    try {
      const saved = localStorage.getItem('crucibai_permissions');
      if (saved) {
        const parsed = JSON.parse(saved);
        Object.entries(parsed).forEach(([tool, rule]) => this.rules.set(tool, rule));
      }
    } catch {}
  }

  async check(toolName, riskLevel = 0.5) {
    const rule = this.rules.get(toolName) || this._defaultRule(toolName, riskLevel);
    
    // Auto-approve trusted tools used recently
    if (rule.mode === 'allow' &&
        rule.trustTier === 'safe' &&
        Date.now() - rule.lastUsed < 86400000) { // 24h
      return { mode: 'allow', reason: 'Trusted — auto-approved', autoApproved: true };
    }
    
    // Block dangerous operations
    if (rule.trustTier === 'dangerous' || riskLevel > 0.85) {
      return { mode: 'block', reason: 'High-risk operation requires explicit approval' };
    }
    
    return {
      mode: rule.mode,
      reason: rule.mode === 'ask' ? 'Needs confirmation' : `Rule: ${rule.mode}`,
      trustTier: rule.trustTier,
      autoApproved: false,
    };
  }

  async record(toolName, userDecision, riskLevel = 0.5) {
    const existing = this.rules.get(toolName) || this._defaultRule(toolName, riskLevel);
    const updated = {
      ...existing,
      mode: userDecision,
      lastUsed: Date.now(),
      count: existing.count + 1,
      deniedCount: userDecision === 'deny' ? existing.deniedCount + 1 : existing.deniedCount,
    };
    
    // Evolve trust tier based on usage pattern
    updated.trustTier = this._computeTrustTier(updated, riskLevel);
    
    this.rules.set(toolName, updated);
    this._persist();
    return updated;
  }

  _computeTrustTier(rule, riskLevel) {
    if (riskLevel > 0.85) return 'dangerous';
    if (rule.deniedCount > 2) return 'untrusted';
    if (rule.count >= 5 && rule.deniedCount === 0 && riskLevel < 0.5) return 'safe';
    if (rule.count >= 2 && riskLevel < 0.7) return 'verified';
    return 'untrusted';
  }

  _defaultRule(toolName, riskLevel) {
    const tier = riskLevel > 0.85 ? 'dangerous'
               : riskLevel > 0.6 ? 'untrusted'
               : 'verified';
    return {
      toolName,
      mode: tier === 'dangerous' ? 'block' : 'ask',
      trustTier: tier,
      lastUsed: 0,
      count: 0,
      deniedCount: 0,
    };
  }

  _persist() {
    try {
      localStorage.setItem('crucibai_permissions',
        JSON.stringify(Object.fromEntries(this.rules)));
    } catch {}
  }

  getDashboard() {
    return Object.fromEntries(this.rules);
  }

  getStats() {
    const rules = Array.from(this.rules.values());
    return {
      total: rules.length,
      safe: rules.filter(r => r.trustTier === 'safe').length,
      verified: rules.filter(r => r.trustTier === 'verified').length,
      untrusted: rules.filter(r => r.trustTier === 'untrusted').length,
      dangerous: rules.filter(r => r.trustTier === 'dangerous').length,
    };
  }

  reset() {
    this.rules.clear();
    try { localStorage.removeItem('crucibai_permissions'); } catch {}
  }
}

export const permissionEngine = new PermissionEngine();
