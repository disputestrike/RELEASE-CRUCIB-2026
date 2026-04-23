import React, { useEffect, useRef } from 'react';
import { Brain, Sparkles, AlertTriangle, CheckCircle, Zap, Loader2 } from 'lucide-react';
import SubagentProgress from './SubagentProgress';
import InlineDiff from './InlineDiff';
import SimulationBlock from './SimulationBlock';
import { contextManager } from '../lib/contextManager';

const ICONS = {
  thinking:    <Brain size={13} className="text-zinc-500" />,
  discovery:   <Sparkles size={13} className="text-emerald-600" />,
  problem:     <AlertTriangle size={13} className="text-amber-500" />,
  solution:    <CheckCircle size={13} className="text-emerald-600" />,
  breakthrough:<Zap size={13} className="text-purple-600" />,
};

export default function ChatStream({
  thoughts = [],
  events = [],
  jobId,
  isRunning,
  eventSource,
  onArtifactClick,
  simulation,
  simulationPersonas = [],
  simulationRecommendation,
  onSimulationContinue,
  onSimulationStop,
  onApplyRecommendation,
}) {
  const bottomRef = useRef(null);
  const processedCountRef = useRef(0);

  const feed = thoughts.length ? thoughts : (events || []).map((e) => ({
    id: e.id,
    timestamp: e.ts || Date.now(),
    type:
      e.type === 'step_failed' || e.type === 'job_failed'
        ? 'problem'
        : e.type === 'step_completed' || e.type === 'job_completed'
          ? 'solution'
          : e.type === 'brain_guidance'
            ? 'thinking'
            : 'discovery',
    message:
      (e.payload && (e.payload.summary || e.payload.message || e.payload.title))
      || e.type,
    detail:
      e.type === 'simulation.update'
        ? `Round ${e.round || e.payload?.round || '?'} update`
        : '',
  }));

  useEffect(() => {
    const start = processedCountRef.current;
    if (feed.length < start) {
      // Reset safety when feed is replaced.
      processedCountRef.current = 0;
    }
    for (let i = processedCountRef.current; i < feed.length; i++) {
      const t = feed[i];
      const message = (t?.message || '').trim();
      if (!message) continue;
      contextManager.addTurn('assistant', message, {
        source: 'chat_stream',
        thoughtType: t?.type || 'thinking',
      });
    }
    processedCountRef.current = feed.length;
  }, [feed]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [feed, simulation, simulationRecommendation]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
      {feed.length === 0 && (
        <div className="text-center text-zinc-400 text-sm py-16">
          <Brain size={32} className="mx-auto mb-3 opacity-30" />
          <p>Describe what you want to build.</p>
          <p className="text-xs mt-1">The system will think out loud here.</p>
        </div>
      )}
      {feed.map((t, i) => (
        <div key={t.id || i}
          className={`flex gap-2 p-2.5 rounded-lg border text-sm
            ${t.type === 'breakthrough' ? 'bg-purple-50 border-purple-200' :
              t.type === 'problem'      ? 'bg-amber-50 border-amber-200' :
              t.type === 'solution'     ? 'bg-emerald-50 border-emerald-200' :
              'bg-white border-zinc-200'}`}>
          <div className="mt-0.5 shrink-0">{ICONS[t.type] || ICONS.thinking}</div>
          <div className="flex-1 min-w-0">
            <p className="text-zinc-800 leading-relaxed">{t.message}</p>
            {t.detail && <p className="text-xs text-zinc-500 mt-0.5">{t.detail}</p>}
            {t.diff && <InlineDiff path={t.artifact} after={t.diff} />}
            {t.artifact && (
              <button onClick={() => onArtifactClick?.(t.artifact)}
                className="text-xs text-blue-600 hover:text-blue-700 mt-1 font-medium">
                View {t.artifact.split('/').pop()}
              </button>
            )}
            {t.subagents && (
              <SubagentProgress jobId={jobId} eventSource={eventSource} />
            )}
            <span className="text-[10px] text-zinc-400 mt-1 block">
              {new Date(t.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </div>
      ))}
      {(simulation || simulationRecommendation) && (
        <SimulationBlock
          simulation={simulation}
          personas={simulationPersonas}
          recommendation={simulationRecommendation}
          onContinue={onSimulationContinue}
          onStop={onSimulationStop}
          onApplyRecommendation={onApplyRecommendation}
        />
      )}
      {isRunning && (
        <div className="flex items-center gap-2 text-zinc-400 text-xs">
          <Loader2 size={12} className="animate-spin" />
          <span>Building…</span>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
