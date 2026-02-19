import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Keyboard, ArrowRight } from 'lucide-react';
import { useAuth } from '../App';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';

const shortcuts = [
  { keys: 'Ctrl+K', desc: 'Command palette' },
  { keys: 'Ctrl+Shift+L', desc: 'New Agent / New chat' },
  { keys: 'Ctrl+Alt+E', desc: 'Maximize Chat' },
  { keys: 'Ctrl+J', desc: 'Show Terminal / Console' },
  { keys: 'Ctrl+P', desc: 'Search / Open file' },
  { keys: 'Ctrl+Shift+B', desc: 'Open preview in browser' },
  { keys: '?', desc: 'Show shortcut cheat sheet' },
];

export default function ShortcutsPublic() {
  const navigate = useNavigate();
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      <PublicNav />
      <div className="max-w-lg mx-auto px-6 py-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-4 mb-10">
          <div className="p-3 rounded-xl bg-zinc-800">
            <Keyboard className="w-8 h-8 text-blue-400" />
          </div>
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Shortcuts</h1>
            <p className="text-zinc-500">Workspace and editor shortcuts. Sign up to use them in the app.</p>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="space-y-0 rounded-2xl border border-zinc-800 bg-zinc-900/30 overflow-hidden"
        >
          {shortcuts.map(({ keys, desc }) => (
            <div key={keys} className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 last:border-0">
              <span className="text-zinc-300">{desc}</span>
              <kbd className="px-2.5 py-1 rounded bg-zinc-800 text-sm font-mono text-zinc-200">{keys}</kbd>
            </div>
          ))}
        </motion.div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} className="mt-10 text-center">
          <button
            onClick={() => navigate(user ? '/app/shortcuts' : '/auth?mode=register')}
            className="inline-flex items-center gap-2 px-6 py-3 bg-white text-zinc-900 font-medium rounded-lg hover:bg-zinc-200 transition"
          >
            {user ? 'Open in app' : 'Get started free'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </motion.div>
      </div>
      <PublicFooter />
    </div>
  );
}
