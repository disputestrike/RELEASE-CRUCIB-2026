/**
 * WorkspaceErrorState — human-readable error display
 * NEVER shows raw backend exceptions (NoneType, traceback, etc.)
 * Always translates to actionable, calm messages with recovery options
 */
import React from 'react';

const KNOWN_ERRORS = [
  { pattern: /NoneType.*acquire|pool.*None|asyncpg|database/i,
    title: "Database connection unavailable",
    cause: "The build engine lost access to the database during startup.",
    fix: "Retrying connection automatically",
    action: "retry" },
  { pattern: /connection.*refused|ECONNREFUSED|network/i,
    title: "Engine offline",
    cause: "Cannot reach the build engine. It may still be starting up.",
    fix: "Reconnecting automatically",
    action: "retry" },
  { pattern: /timeout|timed out/i,
    title: "Build step timed out",
    cause: "A build step took longer than expected.",
    fix: "Retrying with extended timeout",
    action: "retry" },
  { pattern: /api.*failed|api.*error|http.*error/i,
    title: "API connection failed",
    cause: "The build engine API returned an error.",
    fix: "Checking endpoint and retrying",
    action: "retry" },
  { pattern: /auth|token|unauthorized|401/i,
    title: "Authentication required",
    cause: "Your session may have expired.",
    fix: "Refreshing your session",
    action: "reload" },
];

function classify(msg = '') {
  for (const e of KNOWN_ERRORS) {
    if (e.pattern.test(msg)) return e;
  }
  return {
    title: "Build needs attention",
    cause: "An unexpected issue occurred during the build.",
    fix: "Continue from the saved workspace or steer with a follow-up message",
    action: "retry",
  };
}

export default function WorkspaceErrorState({ error, onRetry, onSteer, onDebug, stage }) {
  const msg = typeof error === 'string' ? error : error?.message || JSON.stringify(error || '');
  const classified = classify(msg);
  const isOffline = stage === 'offline' || /offline|disconnected/i.test(msg);

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', padding: '40px 24px', maxWidth: 480, margin: '0 auto',
      textAlign: 'center',
    }}>
      {/* Icon */}
      <div style={{
        width: 48, height: 48, borderRadius: 12,
        background: isOffline ? '#f3f4f6' : '#fff0f0',
        border: `1px solid ${isOffline ? '#e5e7eb' : '#fee2e2'}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 22, marginBottom: 16,
      }}>
        {isOffline ? '⟳' : '⚠'}
      </div>

      {/* Title */}
      <div style={{ fontSize: 15, fontWeight: 600, color: '#111', marginBottom: 8 }}>
        {classified.title}
      </div>

      {/* Cause */}
      <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 6, lineHeight: 1.5 }}>
        {classified.cause}
      </div>

      {/* Fix status */}
      <div style={{
        fontSize: 12, color: '#10b981', marginBottom: 20,
        display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'center',
      }}>
        <span style={{
          display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
          background: '#10b981', animation: 'pulse 1.5s infinite',
        }} />
        {classified.fix}
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
        {onRetry && (
          <button onClick={onRetry} style={{
            padding: '8px 16px', background: '#10b981', color: '#fff',
            border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: 'pointer',
          }}>
            Retry build
          </button>
        )}
        {onSteer && (
          <button onClick={onSteer} style={{
            padding: '8px 16px', background: '#f3f4f6', color: '#374151',
            border: '1px solid #e5e7eb', borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: 'pointer',
          }}>
            Steer differently
          </button>
        )}
        {classified.action === 'reload' && (
          <button onClick={() => window.location.reload()} style={{
            padding: '8px 16px', background: '#f3f4f6', color: '#374151',
            border: '1px solid #e5e7eb', borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: 'pointer',
          }}>
            Reload session
          </button>
        )}
        {onDebug && (
          <button onClick={onDebug} style={{
            padding: '8px 16px', background: 'transparent', color: '#9ca3af',
            border: '1px solid #e5e7eb', borderRadius: 8, fontSize: 12, cursor: 'pointer',
          }}>
            View debug logs
          </button>
        )}
      </div>
    </div>
  );
}
