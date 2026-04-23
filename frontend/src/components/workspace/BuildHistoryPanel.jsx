import { Link } from 'react-router-dom';
import { Loader2, ExternalLink } from 'lucide-react';

/** Prior builds from API; link to Agent Monitor */
export default function BuildHistoryPanel({ buildHistory, projectId, loading }) {
  if (loading) {
    return (
      <div className="p-4 flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 animate-spin text-zinc-400" />
      </div>
    );
  }
  if (!buildHistory || buildHistory.length === 0) {
    return (
      <div className="p-4 text-sm text-zinc-500">
        No prior builds yet. Run a build from the dashboard to see history here.
      </div>
    );
  }
  return (
    <div className="p-3 space-y-2 overflow-y-auto h-full">
      <div className="text-xs text-zinc-500 uppercase tracking-wider mb-3">Build history</div>
      {buildHistory.map((entry, i) => (
        <div key={i} className="p-3 rounded-lg border border-zinc-700/50 bg-zinc-800/30 hover:bg-zinc-800/50 transition">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-zinc-400">
              {entry.completed_at ? new Date(entry.completed_at).toLocaleString() : '—'}
            </span>
            <span className={`text-xs font-medium ${entry.status === 'completed' ? 'text-green-400' : 'text-neutral-400'}`}>
              {entry.status === 'completed' ? 'Completed' : (entry.status || '—')}
            </span>
          </div>
          {entry.quality_score != null && <p className="text-xs text-zinc-500">Quality: {Number(entry.quality_score).toFixed(0)}</p>}
          {entry.tokens_used != null && <p className="text-xs text-zinc-500">{Number(entry.tokens_used).toLocaleString()} tokens</p>}
          {projectId && (
            <Link
              to={`/app/projects/${projectId}`}
              className="inline-flex items-center gap-1 mt-2 text-xs text-blue-400 hover:text-blue-300"
            >
              <ExternalLink className="w-3 h-3" /> View in Agent Monitor
            </Link>
          )}
        </div>
      ))}
    </div>
  );
}
