/**
 * Trust Panel State — quality, security, cost, token tracking
 * Real-time trust signals wired to job events
 */

import { API } from '../App';

export class TrustPanelState {
  constructor() {
    this.quality = 0;
    this.security = null;   // 'passed' | 'failed' | 'scanning' | null
    this.errors = 0;
    this.warnings = 0;
    this.deployReady = false;
    this.tokensUsed = 0;
    this.estimatedCostUSD = 0;
    this.listeners = new Set();
  }

  update(patch) {
    Object.assign(this, patch);
    this.listeners.forEach(fn => fn({ ...this }));
  }

  subscribe(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  fromJobEvent(event) {
    const t = event?.type || '';
    const p = event?.payload || {};

    if (t === 'job.complete') {
      this.update({
        quality: p.qualityScore || 0,
        deployReady: (p.qualityScore || 0) >= 60,
        errors: 0,
      });
    }
    if (t === 'issue.detected') {
      this.update({ errors: this.errors + 1 });
    }
    if (t === 'issue.fixed') {
      this.update({ errors: Math.max(0, this.errors - 1) });
    }
    if (t === 'phase.complete' && p.phaseName?.toLowerCase().includes('security')) {
      this.update({ security: 'passed' });
    }
    if (t === 'phase.error' && p.phaseName?.toLowerCase().includes('security')) {
      this.update({ security: 'failed' });
    }
  }

  async loadFromJob(jobId, token) {
    if (!jobId || !token) return;
    try {
      const res = await fetch(`${API}/builds/${jobId}/quality`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        this.update({
          quality: data.overall || 0,
          security: data.security > 60 ? 'passed' : 'failed',
          deployReady: (data.overall || 0) >= 60,
        });
      }
    } catch {}
  }

  getLabel() {
    if (this.quality >= 90) return { text: 'Exceptional', color: '#10b981' };
    if (this.quality >= 75) return { text: 'Production Ready', color: '#10b981' };
    if (this.quality >= 60) return { text: 'Good', color: '#f59e0b' };
    if (this.quality > 0)   return { text: 'Needs Work', color: '#ef4444' };
    return { text: 'Pending', color: '#9ca3af' };
  }
}

export const trustPanelState = new TrustPanelState();
