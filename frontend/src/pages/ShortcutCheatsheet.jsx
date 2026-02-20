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
    <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A] p-6">
      <div className="max-w-lg mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-3 rounded-xl bg-zinc-800">
            <Keyboard className="w-8 h-8 text-orange-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Shortcuts</h1>
            <p className="text-zinc-400">Workspace and editor</p>
          </div>
        </div>
        <div className="space-y-3">
          {shortcuts.map(({ keys, desc }) => (
            <div key={keys} className="flex items-center justify-between py-3 border-b border-zinc-800">
              <span className="text-zinc-300">{desc}</span>
              <kbd className="px-2.5 py-1 rounded bg-zinc-800 text-sm font-mono text-zinc-200">{keys}</kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
