/**
 * ActionableError
 *
 * Replaces generic "Something went wrong" messages with a styled error
 * bubble that includes a short explanation and 1-3 action buttons.
 */
import { AlertTriangle, RefreshCw, ExternalLink, MessageCircle } from 'lucide-react';

/**
 * Given an error message string, returns metadata about what actions to show.
 */
function parseErrorActions(message) {
  const m = (message || '').toLowerCase();

  if (m.includes('rate limit') || m.includes('ratelimit') || m.includes('too many')) {
    return {
      icon: '⏱',
      title: 'Rate limit reached',
      detail: 'The AI service is busy. Wait 60 seconds and try again.',
      actions: [{ label: 'Retry', icon: 'retry' }],
    };
  }
  if (m.includes('insufficient credits') || m.includes('credit') || m.includes('402')) {
    return {
      icon: '💳',
      title: 'Insufficient credits',
      detail: 'You\'ve used all your credits. Add more to continue building.',
      actions: [
        { label: 'Get credits', icon: 'external', href: '/app/tokens' },
      ],
    };
  }
  if (m.includes('backend not available') || m.includes('cannot post') || m.includes('network') || m.includes('failed to fetch') || m.includes('connection')) {
    return {
      icon: '🔌',
      title: 'Connection error',
      detail: 'Could not reach the server. Check your internet connection.',
      actions: [
        { label: 'Retry', icon: 'retry' },
        { label: 'View setup guide', icon: 'external', href: 'https://github.com/disputestrike/CrucibAI#readme' },
      ],
    };
  }
  if (m.includes('api key') || m.includes('unauthorized') || m.includes('401')) {
    return {
      icon: '🔑',
      title: 'API key missing',
      detail: 'An AI API key is required. Add one in Settings.',
      actions: [{ label: 'Open Settings', icon: 'external', href: '/app/settings' }],
    };
  }
  if (m.includes('build failed') || m.includes('failed:')) {
    return {
      icon: '⚠️',
      title: 'Build failed',
      detail: message.slice(0, 120),
      actions: [
        { label: 'Retry', icon: 'retry' },
        { label: 'View logs', icon: 'logs' },
        { label: 'Contact support', icon: 'support', href: '/contact' },
      ],
    };
  }
  return {
    icon: '⚠️',
    title: 'Something went wrong',
    detail: message.slice(0, 140) || 'An unexpected error occurred.',
    actions: [
      { label: 'Retry', icon: 'retry' },
      { label: 'Contact support', icon: 'support', href: '/contact' },
    ],
  };
}

export default function ActionableError({ message, onRetry, onViewLogs }) {
  const { icon, title, detail, actions } = parseErrorActions(message);

  return (
    <div
      className="rounded-xl px-4 py-3 text-sm space-y-2.5 max-w-[75%]"
      style={{
        background: 'rgba(239,68,68,0.07)',
        border: '1px solid rgba(239,68,68,0.25)',
        color: 'var(--chat-text, #e4e4e7)',
      }}
    >
      {/* Title row */}
      <div className="flex items-start gap-2">
        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" style={{ color: '#f87171' }} />
        <div>
          <p className="font-medium text-sm" style={{ color: '#fca5a5' }}>{icon} {title}</p>
          <p className="text-xs mt-0.5 leading-relaxed" style={{ color: 'var(--theme-muted, #a1a1aa)' }}>{detail}</p>
        </div>
      </div>

      {/* Action buttons */}
      {actions.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pl-6">
          {actions.map((a, i) => {
            if (a.icon === 'retry' && onRetry) {
              return (
                <button
                  key={i}
                  type="button"
                  onClick={onRetry}
                  className="flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium transition hover:bg-white/10"
                  style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--theme-text, #e4e4e7)' }}
                >
                  <RefreshCw className="w-3 h-3" /> {a.label}
                </button>
              );
            }
            if (a.icon === 'logs' && onViewLogs) {
              return (
                <button
                  key={i}
                  type="button"
                  onClick={onViewLogs}
                  className="flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium transition hover:bg-white/10"
                  style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--theme-text, #e4e4e7)' }}
                >
                  <ExternalLink className="w-3 h-3" /> {a.label}
                </button>
              );
            }
            if (a.icon === 'support' || a.icon === 'external') {
              return (
                <a
                  key={i}
                  href={a.href || '/contact'}
                  target={a.href?.startsWith('http') ? '_blank' : undefined}
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium transition hover:bg-white/10"
                  style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--theme-text, #e4e4e7)' }}
                >
                  {a.icon === 'support' ? <MessageCircle className="w-3 h-3" /> : <ExternalLink className="w-3 h-3" />}
                  {a.label}
                </a>
              );
            }
            return null;
          })}
        </div>
      )}
    </div>
  );
}
