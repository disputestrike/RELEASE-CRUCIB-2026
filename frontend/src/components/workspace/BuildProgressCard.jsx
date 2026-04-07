import { motion } from 'framer-motion';
import { ChevronDown, ChevronRight } from 'lucide-react';

/** Compact collapsible build progress — Manus-style step bar */
export default function BuildProgressCard({
  expanded,
  onToggle,
  buildProgress,
  currentPhase,
  lastTokensUsed,
  projectBuildProgress,
  qualityScore,
  agentsActivityLength,
  children,
}) {
  const tokens = lastTokensUsed || projectBuildProgress?.tokens_used || 0;
  return (
    <div className="border-b border-stone-200 bg-white flex-shrink-0">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-50 transition"
      >
        <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: '#1A1A1A' }} />
        <span className="text-sm font-medium text-gray-900 flex-1 truncate">
          {currentPhase || 'Building...'} — {Math.round(buildProgress)}%
        </span>
        <span className="text-xs text-gray-500 shrink-0">{agentsActivityLength || 0} agents · {(tokens / 1000).toFixed(0)}k tokens</span>
        {qualityScore != null && <span className="text-xs text-gray-600 shrink-0">Quality: {qualityScore}%</span>}
        {expanded ? <ChevronDown className="w-4 h-4 text-gray-500 shrink-0" /> : <ChevronRight className="w-4 h-4 text-gray-500 shrink-0" />}
      </button>
      <div className="border-t border-stone-100 bg-gray-50/50">
        <div className="h-1 bg-gray-200 rounded-full overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{ background: '#1A1A1A' }}
            initial={{ width: 0 }}
            animate={{ width: `${buildProgress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>
      {expanded && (
        <div className="max-h-64 overflow-y-auto border-t border-stone-200">
          {children}
        </div>
      )}
    </div>
  );
}
