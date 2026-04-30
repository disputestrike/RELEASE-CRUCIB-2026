import { AlertTriangle, RefreshCw, ExternalLink, MessageCircle } from 'lucide-react';

function parseErrorActions(message) {
  const m = (message || '').toLowerCase();

  if (m.includes('rate limit') || m.includes('ratelimit') || m.includes('too many')) {
    return {
      title: 'Still working on it',
      detail: 'The AI service is busy. I can try again in a moment.',
      actions: [{ label: 'Retry', icon: 'retry' }],
    };
  }

  if (m.includes('insufficient credits') || m.includes('credit') || m.includes('402')) {
    return {
      title: 'Credits needed',
      detail: 'Add credits to continue this conversation.',
      actions: [{ label: 'Get credits', icon: 'external', href: '/app/tokens' }],
    };
  }

  if (m.includes('backend not available') || m.includes('cannot post') || m.includes('network') || m.includes('failed to fetch') || m.includes('connection')) {
    return {
      title: 'Reconnecting',
      detail: 'I could not reach the server for a moment. Your workspace is still saved.',
      actions: [
        { label: 'Retry', icon: 'retry' },
        { label: 'Setup guide', icon: 'external', href: 'https://github.com/disputestrike/CrucibAI#readme' },
      ],
    };
  }

  if (m.includes('api key') || m.includes('unauthorized') || m.includes('401')) {
    return {
      title: 'Provider setup needed',
      detail: 'Add an AI provider key in Settings to keep building.',
      actions: [{ label: 'Open Settings', icon: 'external', href: '/app/settings' }],
    };
  }

  if (m.includes('build failed') || m.includes('failed:')) {
    return {
      title: 'Another pass needed',
      detail: 'I found something in the workspace that needs repair. The current files are saved.',
      actions: [
        { label: 'Continue', icon: 'retry' },
        { label: 'Details', icon: 'logs' },
        { label: 'Contact support', icon: 'support', href: '/contact' },
      ],
    };
  }

  return {
    title: 'Needs another pass',
    detail: 'I need another pass to continue this workspace. Your progress is still saved.',
    actions: [
      { label: 'Retry', icon: 'retry' },
      { label: 'Contact support', icon: 'support', href: '/contact' },
    ],
  };
}

export default function ActionableError({ message, onRetry, onViewLogs }) {
  const { title, detail, actions } = parseErrorActions(message);

  return (
    <div
      className="rounded-xl px-4 py-3 text-sm space-y-2.5 max-w-[75%]"
      style={{
        background: 'var(--theme-surface, #ffffff)',
        border: '1px solid var(--theme-border, #d8d8d8)',
        color: 'var(--theme-text, #111111)',
      }}
    >
      <div className="flex items-start gap-2">
        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" style={{ color: 'var(--theme-text, #111111)' }} />
        <div>
          <p className="font-medium text-sm" style={{ color: 'var(--theme-text, #111111)' }}>{title}</p>
          <p className="text-xs mt-0.5 leading-relaxed" style={{ color: 'var(--theme-muted, #666666)' }}>{detail}</p>
        </div>
      </div>

      {actions.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pl-6">
          {actions.map((a, i) => {
            if (a.icon === 'retry' && onRetry) {
              return (
                <button
                  key={i}
                  type="button"
                  onClick={onRetry}
                  className="flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium transition"
                  style={{ background: '#f7f7f7', border: '1px solid #d8d8d8', color: '#111111' }}
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
                  className="flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium transition"
                  style={{ background: '#f7f7f7', border: '1px solid #d8d8d8', color: '#111111' }}
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
                  className="flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium transition"
                  style={{ background: '#f7f7f7', border: '1px solid #d8d8d8', color: '#111111' }}
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
