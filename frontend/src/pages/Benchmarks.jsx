import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Zap, Coins, BarChart3, GitCompare } from 'lucide-react';
import PublicNav from '../components/PublicNav';

const metrics = [
  { icon: Zap, value: '3.2x', label: 'Faster with parallel agents', sub: 'DAG phases vs sequential run' },
  { icon: Coins, value: '~30%', label: 'Token savings', sub: 'With USE_TOKEN_OPTIMIZED_PROMPTS' },
  { icon: BarChart3, value: '65–80', label: 'Typical quality score', sub: '0–100 overall + breakdown' },
  { icon: GitCompare, value: 'vs Manus/Cursor', label: 'Comparison', sub: 'Parallel DAG, output chaining, phase retry' },
];

export default function Benchmarks() {
  return (
    <div className="min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      <PublicNav />
      <div className="max-w-4xl mx-auto px-6 py-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-14">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Performance</span>
          <h1 className="text-kimi-section font-bold text-kimi-text mt-2 mb-4">CrucibAI Benchmark Report</h1>
          <p className="text-kimi-muted max-w-xl mx-auto">
            Speed, token usage, and quality metrics for our 120-agent swarm and DAG orchestration.
          </p>
        </motion.div>

        <div className="grid sm:grid-cols-2 gap-6 mb-12">
          {metrics.map((m, i) => (
            <motion.div
              key={m.label}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className="p-6 rounded-2xl border border-white/10 bg-kimi-bg-card"
            >
              <div className="p-2.5 rounded-xl bg-white/5 w-fit mb-4">
                <m.icon className="w-6 h-6 text-kimi-accent" />
              </div>
              <div className="text-2xl font-bold text-kimi-text mb-1">{m.value}</div>
              <div className="font-medium text-kimi-text mb-1">{m.label}</div>
              <div className="text-sm text-kimi-muted">{m.sub}</div>
            </motion.div>
          ))}
        </div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="rounded-2xl border border-white/10 bg-kimi-bg-card p-6">
          <h2 className="text-lg font-semibold text-kimi-text mb-4">Summary</h2>
          <ul className="space-y-2 text-kimi-muted text-sm">
            <li>• <strong className="text-kimi-text">Parallel DAG</strong> — Multiple agents run per phase for ~3.2x faster builds.</li>
            <li>• <strong className="text-kimi-text">Token-optimized prompts</strong> — Optional short prompts save ~30% tokens per build.</li>
            <li>• <strong className="text-kimi-text">Output chaining</strong> — Agents see previous outputs for coherent code and style.</li>
            <li>• <strong className="text-kimi-text">Phase retry</strong> — When Quality phase has many failures, we suggest retrying code generation.</li>
          </ul>
          <p className="mt-4 text-kimi-muted text-sm">
            Full report: <code className="bg-white/10 px-1.5 py-0.5 rounded">BENCHMARK_REPORT.md</code> in the repo.
          </p>
        </motion.div>

        <div className="mt-10 text-center">
          <Link to="/" className="text-kimi-accent hover:text-kimi-text font-medium">← Back to home</Link>
        </div>
      </div>
    </div>
  );
}
