/**
 * Context Manager — semantic anchoring + adaptive folding
 * Keeps compaction transparent and user-visible.
 * 
 * Runtime goals:
 * - Their folding is hidden. Ours is visible in the UI.
 * - We preserve intent anchors (goals, decisions) permanently
 * - Low-signal tool output gets folded automatically
 * - User can unlock any folded turn
 */

const MAX_TOKENS = 128000;
const FOLD_THRESHOLD = 0.75; // fold when >75% full

export class ContextManager {
  constructor() {
    this.anchors = []; // never compressed
    this.turns = [];
  }

  addTurn(role, content, meta = {}) {
    const signalScore = this._computeSignalScore(role, content);
    const turn = {
      id: crypto.randomUUID(),
      role,
      content,
      signalScore,
      timestamp: Date.now(),
      folded: false,
      locked: meta.locked || false,
      ...meta
    };
    this.turns.push(turn);

    // Auto-anchor high-signal user turns (goals, decisions)
    if (role === 'user' && signalScore > 0.8) {
      this.anchors.push({
        id: turn.id,
        type: 'goal',
        content: content.slice(0, 200),
        locked: true,
        timestamp: turn.timestamp,
      });
    }
    this._enforceLimits();
    return turn;
  }

  _computeSignalScore(role, content) {
    if (role === 'system') return 0.95;
    if (role === 'user') {
      if (content.length > 100) return 0.85;
      if (content.length > 30) return 0.7;
      return 0.5;
    }
    if (role === 'tool') return 0.35; // tool outputs fold first
    // assistant messages
    if (content.includes('✓') || content.includes('complete') || content.includes('Error')) return 0.9;
    if (content.includes('building') || content.includes('created')) return 0.75;
    return 0.4;
  }

  _estimateTokens() {
    return this.turns.reduce((acc, t) => acc + Math.ceil(t.content.length / 4), 0);
  }

  _enforceLimits() {
    const tokens = this._estimateTokens();
    if (tokens > MAX_TOKENS * FOLD_THRESHOLD) {
      this._foldLowSignalTurns(tokens);
    }
  }

  _foldLowSignalTurns(currentTokens) {
    // Sort by signal score ascending — fold lowest first
    const foldable = this.turns
      .filter(t => !t.locked && !t.folded && t.role === 'tool')
      .sort((a, b) => a.signalScore - b.signalScore);

    let tokensToFree = currentTokens - (MAX_TOKENS * 0.6);
    for (const turn of foldable) {
      if (tokensToFree <= 0) break;
      const originalLen = turn.content.length;
      turn._originalContent = turn.content;
      turn.content = `[Folded ${turn.role} output — ${new Date(turn.timestamp).toLocaleTimeString()}]`;
      turn.folded = true;
      tokensToFree -= Math.ceil((originalLen - turn.content.length) / 4);
    }
  }

  unfold(turnId) {
    const turn = this.turns.find(t => t.id === turnId);
    if (turn && turn.folded && turn._originalContent) {
      turn.content = turn._originalContent;
      turn.folded = false;
    }
  }

  getOptimized() {
    // Return anchors first, then turns sorted by time
    const anchorIds = new Set(this.anchors.map(a => a.id));
    const nonAnchorTurns = this.turns.filter(t => !anchorIds.has(t.id));
    return [...this.anchors, ...nonAnchorTurns]
      .sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
  }

  getStats() {
    return {
      totalTurns: this.turns.length,
      foldedTurns: this.turns.filter(t => t.folded).length,
      anchors: this.anchors.length,
      estimatedTokens: this._estimateTokens(),
      tokenLimit: MAX_TOKENS,
      usagePercent: Math.round((this._estimateTokens() / MAX_TOKENS) * 100),
    };
  }

  clear() {
    this.turns = [];
    this.anchors = [];
  }
}

export const contextManager = new ContextManager();
