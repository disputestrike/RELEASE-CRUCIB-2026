/**
 * Hooks layer — lifecycle interception points
 * Runtime hook system: onPromptSubmit, beforeToolCall, etc.
 */
class HookEngine {
  constructor() {
    this.hooks = {
      onPromptSubmit: [],
      beforeToolCall: [],
      afterToolCall: [],
      onFailure: [],
      onRunComplete: [],
      onContextCompact: [],
    };
  }

  register(hookName, fn) {
    if (!this.hooks[hookName]) this.hooks[hookName] = [];
    this.hooks[hookName].push(fn);
    return () => { this.hooks[hookName] = this.hooks[hookName].filter(f => f !== fn); };
  }

  async run(hookName, context) {
    const fns = this.hooks[hookName] || [];
    let ctx = { ...context };
    for (const fn of fns) {
      try { ctx = (await fn(ctx)) || ctx; } catch {}
    }
    return ctx;
  }
}

export const hookEngine = new HookEngine();

// Built-in hooks
hookEngine.register('onRunComplete', async (ctx) => {
  // Auto-save to memory after build
  if (ctx.jobId && ctx.goal) {
    const { memoryGraph } = await import('./memoryGraph');
    await memoryGraph.save('session', `build_${ctx.jobId}`, {
      goal: ctx.goal, status: ctx.status, quality: ctx.quality,
    }, ctx.quality > 75 ? 0.8 : 0.4);
  }
  return ctx;
});

hookEngine.register('onFailure', async (ctx) => {
  if (ctx.jobId) {
    const { memoryGraph } = await import('./memoryGraph');
    await memoryGraph.save('pattern', `failure_${ctx.errorType || 'unknown'}`, {
      error: ctx.error, fix: ctx.autoFix, agent: ctx.agentName,
    }, 0.7);
  }
  return ctx;
});
