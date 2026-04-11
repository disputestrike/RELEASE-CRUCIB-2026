import { Keyboard } from 'lucide-react';

const shortcuts = [
  { keys: 'Ctrl+K', desc: 'Command palette' },
  { keys: 'Ctrl+Shift+L', desc: 'New Agent / New chat' },
  { keys: 'Ctrl+Alt+E', desc: 'Maximize Chat' },
  { keys: 'Ctrl+J', desc: 'Show Terminal / Console' },
  { keys: 'Ctrl+P', desc: 'Search / Open file' },
  { keys: 'Ctrl+Shift+B', desc: 'Open preview in browser' },
  { keys: '?', desc: 'Show this shortcut cheat sheet' },
];

export default function ShortcutCheatsheet() {
  return (
    <div className="max-w-lg mx-auto" style={{ color: 'var(--theme-text)' }}>
      <div className="flex items-center gap-3 mb-8">
        <div
          className="p-3 rounded-xl"
          style={{ background: 'var(--theme-input)', color: 'var(--theme-text)' }}
        >
          <Keyboard className="w-8 h-8" strokeWidth={2} aria-hidden />
        </div>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--theme-text)' }}>Shortcuts</h1>
          <p className="text-sm" style={{ color: 'var(--theme-muted)' }}>Workspace and editor</p>
        </div>
      </div>
      <div className="space-y-0">
        {shortcuts.map(({ keys, desc }) => (
          <div
            key={keys}
            className="flex items-center justify-between py-3 border-b last:border-b-0 gap-4"
            style={{ borderColor: 'var(--theme-border)' }}
          >
            <span className="text-sm" style={{ color: 'var(--theme-muted)' }}>{desc}</span>
            <kbd
              className="px-2.5 py-1 rounded text-sm font-mono shrink-0 border"
              style={{
                background: 'var(--theme-surface2)',
                color: 'var(--theme-text)',
                borderColor: 'var(--theme-border)',
              }}
            >
              {keys}
            </kbd>
          </div>
        ))}
      </div>
    </div>
  );
}
