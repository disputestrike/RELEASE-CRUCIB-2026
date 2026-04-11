import {
  X,
  Rocket,
  RotateCcw,
  GitBranch,
  Cpu,
  Check,
  ChevronRight,
  ShieldCheck,
  Search,
  Activity,
  Layers,
} from 'lucide-react';

/** Maps backend `emit_build_event` types to timeline row chrome (same store as SSE). */
export function getBuildEventPresentation(ev) {
  const t = ev?.type || '';
  const failed = ev?.status === 'failed';
  const table = {
    build_started: { Icon: Layers, color: 'var(--theme-accent)', title: 'Build started' },
    build_completed: { Icon: failed ? X : Rocket, color: failed ? '#f87171' : '#4ade80', title: failed ? 'Build failed' : 'Build completed' },
    checkpoint_restored: { Icon: RotateCcw, color: '#a78bfa', title: 'Checkpoint restored' },
    phase_started: { Icon: GitBranch, color: '#38bdf8', title: 'Phase' },
    agent_started: { Icon: Cpu, color: '#a3a3a3', title: 'Agent started' },
    agent_completed: { Icon: Check, color: '#86efac', title: 'Agent completed' },
    agent_skipped: { Icon: ChevronRight, color: 'var(--theme-muted)', title: 'Agent skipped' },
    quality_check_started: { Icon: ShieldCheck, color: '#c084fc', title: 'Quality check' },
    critic_started: { Icon: Search, color: '#c084fc', title: 'Critic review' },
    truth_started: { Icon: Activity, color: '#c084fc', title: 'Truth verification' },
  };
  const row = table[t];
  if (row) return row;
  const human = t.replace(/_/g, ' ') || 'Event';
  return { Icon: Activity, color: 'var(--theme-muted)', title: human.charAt(0).toUpperCase() + human.slice(1) };
}
