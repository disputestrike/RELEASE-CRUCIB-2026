import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { CheckCircle2, ShieldCheck, BarChart3, TerminalSquare } from 'lucide-react';
import PublicNav from '../components/PublicNav';
import { API_BASE } from '../apiBase';

const API = API_BASE;

export default function PublicProofPage() {
  const [summary, setSummary] = useState(null);
  const [indexPayload, setIndexPayload] = useState(null);

  useEffect(() => {
    let cancelled = false;

    fetch(`${API}/trust/product-dominance-summary`)
      .then((res) => res.json())
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch(() => {
        if (!cancelled) setSummary({ status: 'not_available' });
      });

    fetch(`${API}/trust/product-dominance-index`)
      .then((res) => res.json())
      .then((data) => {
        if (!cancelled) setIndexPayload(data);
      })
      .catch(() => {
        if (!cancelled) setIndexPayload({ status: 'not_available' });
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const canonical = summary?.canonical_run || {};
  const canonicalMetrics = canonical?.summary || {};

  const stats = useMemo(
    () => [
      {
        icon: CheckCircle2,
        label: 'Canonical pack',
        value: canonical?.run || 'Pending',
        sub: 'Best signed live run selected by generator',
      },
      {
        icon: BarChart3,
        label: 'Average score',
        value:
          typeof canonicalMetrics.average_score === 'number'
            ? canonicalMetrics.average_score.toFixed(2)
            : 'n/a',
        sub: 'Scorecard output from canonical summary.json',
      },
      {
        icon: ShieldCheck,
        label: 'Success rate',
        value:
          typeof canonicalMetrics.success_rate === 'number'
            ? `${Math.round(canonicalMetrics.success_rate * 100)}%`
            : 'n/a',
        sub: 'Run-level success from signed benchmark report',
      },
      {
        icon: TerminalSquare,
        label: 'Signed runs',
        value: typeof summary?.signed_runs === 'number' ? `${summary.signed_runs}` : '0',
        sub: 'Proof packs with valid HMAC manifest signatures',
      },
    ],
    [canonical, canonicalMetrics, summary],
  );

  return (
    <div className="min-h-screen bg-kimi-bg text-kimi-text grid-pattern-kimi">
      <PublicNav />
      <div className="max-w-5xl mx-auto px-6 py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <span className="text-xs uppercase tracking-wider text-kimi-muted">Public Proof</span>
          <h1 className="text-kimi-section font-bold text-kimi-text mt-2 mb-4">
            Product Dominance Evidence
          </h1>
          <p className="text-kimi-muted max-w-2xl mx-auto">
            One page for results, signed manifests, and deterministic verification. Build in chat,
            then verify what shipped.
          </p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          {stats.map((item, i) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              className="rounded-lg border border-white/10 bg-kimi-bg-card p-5"
            >
              <div className="p-2 rounded-md bg-white/5 w-fit mb-3">
                <item.icon className="w-5 h-5 text-kimi-accent" />
              </div>
              <div className="text-lg font-semibold text-kimi-text mb-1 break-all">{item.value}</div>
              <div className="text-sm text-kimi-text mb-1">{item.label}</div>
              <div className="text-xs text-kimi-muted">{item.sub}</div>
            </motion.div>
          ))}
        </div>

        <div className="rounded-lg border border-white/10 bg-kimi-bg-card p-6 mb-8">
          <h2 className="text-lg font-semibold text-kimi-text mb-3">Verify Locally</h2>
          <p className="text-sm text-kimi-muted mb-3">
            Recompute signature checks with the same secret used during proof generation.
          </p>
          <div className="text-sm text-kimi-text/90 mb-2">Set environment variable:</div>
          <pre className="bg-black/30 text-kimi-text rounded-md p-3 overflow-x-auto text-xs mb-3">
{summary?.verification?.env_example || "$env:CRUCIB_PROOF_HMAC_SECRET = 'local-proof-test-secret'"}
          </pre>
          <div className="text-sm text-kimi-text/90 mb-2">Run verifier:</div>
          <pre className="bg-black/30 text-kimi-text rounded-md p-3 overflow-x-auto text-xs">
{summary?.verification?.command || 'Verification command unavailable in this deployment.'}
          </pre>
        </div>

        <div className="rounded-lg border border-white/10 bg-kimi-bg-card p-6 mb-8">
          <h2 className="text-lg font-semibold text-kimi-text mb-3">Published Artifacts</h2>
          <ul className="space-y-2 text-sm text-kimi-muted">
            <li>
              Index (markdown):
              <code className="ml-2 bg-white/10 px-1.5 py-0.5 rounded">{summary?.artifacts?.index_markdown || 'n/a'}</code>
            </li>
            <li>
              Index (json):
              <code className="ml-2 bg-white/10 px-1.5 py-0.5 rounded">{summary?.artifacts?.index_json || 'n/a'}</code>
            </li>
            <li>
              Landing (html):
              <code className="ml-2 bg-white/10 px-1.5 py-0.5 rounded">{summary?.artifacts?.landing_html || 'n/a'}</code>
            </li>
            <li>
              Indexed runs:
              <code className="ml-2 bg-white/10 px-1.5 py-0.5 rounded">{summary?.runs_indexed ?? 0}</code>
            </li>
          </ul>
        </div>

        <div className="rounded-lg border border-white/10 bg-kimi-bg-card p-6 mb-8">
          <h2 className="text-lg font-semibold text-kimi-text mb-3">Index Snapshot</h2>
          {indexPayload?.index ? (
            <pre className="bg-black/30 text-kimi-text rounded-md p-3 overflow-auto text-xs max-h-[360px]">
{JSON.stringify(indexPayload.index, null, 2)}
            </pre>
          ) : (
            <p className="text-sm text-kimi-muted">
              Public proof index is not available yet in this deployment.
            </p>
          )}
        </div>

        <div className="flex flex-wrap gap-3 justify-center">
          <Link
            to="/app/workspace"
            className="px-5 py-2.5 rounded-lg bg-white text-gray-900 font-medium hover:bg-gray-100 transition"
          >
            Start in Chat Workspace
          </Link>
          <Link
            to="/benchmarks"
            className="px-5 py-2.5 rounded-lg border border-white/20 text-kimi-text hover:bg-white/5 transition"
          >
            Back to Benchmarks
          </Link>
        </div>
      </div>
    </div>
  );
}
