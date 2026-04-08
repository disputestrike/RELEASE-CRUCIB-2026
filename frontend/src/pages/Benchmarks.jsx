import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, BarChart3, ShieldCheck, ExternalLink } from 'lucide-react';
import PublicNav from '../components/PublicNav';
import { API_BASE } from '../apiBase';

const API = API_BASE;

export default function Benchmarks() {
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/trust/benchmark-summary`)
      .then((res) => res.json())
      .then((data) => { if (!cancelled) setSummary(data); })
      .catch(() => {
        if (!cancelled) {
          setSummary({ status: 'not_available', prompt_count: 0, passed_count: 0, pass_rate: 0, average_score: 0, cases: [] });
        }
      });
    return () => { cancelled = true; };
  }, []);

  const promptCount = summary?.prompt_count ?? '...';
  const passedCount = summary?.passed_count ?? '...';
  const passRate = typeof summary?.pass_rate === 'number' ? `${Math.round(summary.pass_rate * 100)}%` : '...';
  const averageScore = typeof summary?.average_score === 'number' ? summary.average_score.toFixed(0) : '...';

  const metrics = [
    { icon: CheckCircle2, value: `${passedCount}/${promptCount}`, label: 'Prompt categories passed', sub: 'Deterministic repeatability suite' },
    { icon: BarChart3, value: passRate, label: 'Pass rate', sub: 'Release gate threshold is 90%' },
    { icon: ShieldCheck, value: averageScore, label: 'Average score', sub: 'Preview, proof, deploy readiness' },
    { icon: ExternalLink, value: 'Live URL', label: 'Generated app publish', sub: '/published/{job_id}/ after build proof' },
  ];

  return (
    <div className="min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      <PublicNav />
      <div className="max-w-4xl mx-auto px-6 py-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-14">
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Proof</span>
          <h1 className="text-kimi-section font-bold text-kimi-text mt-2 mb-4">CrucibAI Benchmark Report</h1>
          <p className="text-kimi-muted max-w-xl mx-auto">
            Public proof for the prompt-to-app golden path: generated files, preview, elite proof, deploy readiness, and publish URL wiring.
          </p>
        </motion.div>

        <div className="grid sm:grid-cols-2 gap-6 mb-12">
          {metrics.map((m, i) => (
            <motion.div
              key={m.label}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className="p-6 rounded-lg border border-white/10 bg-kimi-bg-card"
            >
              <div className="p-2.5 rounded-lg bg-white/5 w-fit mb-4">
                <m.icon className="w-6 h-6 text-kimi-accent" />
              </div>
              <div className="text-2xl font-bold text-kimi-text mb-1">{m.value}</div>
              <div className="font-medium text-kimi-text mb-1">{m.label}</div>
              <div className="text-sm text-kimi-muted">{m.sub}</div>
            </motion.div>
          ))}
        </div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.35 }} className="rounded-lg border border-white/10 bg-kimi-bg-card p-6 mb-8">
          <h2 className="text-lg font-semibold text-kimi-text mb-4">Methodology</h2>
          <p className="text-kimi-muted text-sm mb-4">
            The repeatability suite runs across 50 app categories. Each case checks generated file structure,
            prompt coverage, preview gate, elite proof gate, deploy build readiness, and publish readiness.
            The default release-gate mode is deterministic and does not spend live model credits.
          </p>
          <p className="text-kimi-muted text-sm">
            Latest proof: <code className="bg-white/10 px-1.5 py-0.5 rounded">proof/benchmarks/repeatability_v1/</code>
          </p>
        </motion.div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="rounded-lg border border-white/10 bg-kimi-bg-card p-6">
          <h2 className="text-lg font-semibold text-kimi-text mb-4">Summary</h2>
          <ul className="space-y-2 text-kimi-muted text-sm">
            <li>- <strong className="text-kimi-text">Repeatability</strong>: 50 categories are checked by the release gate.</li>
            <li>- <strong className="text-kimi-text">Preview</strong>: static preview checks run by default; browser preview is available in the heavier gate.</li>
            <li>- <strong className="text-kimi-text">Proof</strong>: every case emits a case report and workspace manifest.</li>
            <li>- <strong className="text-kimi-text">Publish</strong>: generated apps can be served at a public in-platform URL after build proof.</li>
          </ul>
        </motion.div>

        <div className="mt-10 text-center">
          <Link to="/" className="text-kimi-accent hover:text-kimi-text font-medium">Back to home</Link>
        </div>
      </div>
    </div>
  );
}
