import React, { useState, useEffect } from 'react';
import { Cpu, CheckCircle, XCircle, Loader2 } from 'lucide-react';

export default function SubagentProgress({ jobId, eventSource }) {
  const [agents, setAgents] = useState([]);

  useEffect(() => {
    if (!eventSource) return;
    const handler = (event) => {
      const e = typeof event === 'string' ? JSON.parse(event) : event;
      if (e.jobId && e.jobId !== jobId) return;
      if (e.type === 'subagent.started') {
        setAgents(prev => [...prev.filter(a => a.id !== e.payload.subagentId), {
          id: e.payload.subagentId, role: e.payload.role, status: 'running',
        }]);
      } else if (e.type === 'subagent.complete') {
        setAgents(prev => prev.map(a =>
          a.id === e.payload.subagentId ? { ...a, status: 'complete' } : a));
      } else if (e.type === 'subagent.failed') {
        setAgents(prev => prev.map(a =>
          a.id === e.payload.subagentId ? { ...a, status: 'failed' } : a));
      }
    };
    const unsub = eventSource.on?.('*', handler);
    return () => unsub?.();
  }, [jobId, eventSource]);

  if (!agents.length) return null;

  const done = agents.filter(a => a.status === 'complete').length;
  const failed = agents.filter(a => a.status === 'failed').length;
  const running = agents.filter(a => a.status === 'running').length;

  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 my-2">
      <div className="flex items-center gap-2 mb-2">
        <Cpu size={13} className="text-zinc-500" />
        <span className="text-xs font-semibold text-zinc-700">
          Parallel agents: {done}/{agents.length} done
          {failed > 0 && ` · ${failed} failed`}
          {running > 0 && ` · ${running} running`}
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {agents.map(a => (
          <div key={a.id} className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border
            ${a.status === 'complete' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' :
              a.status === 'failed' ? 'border-red-200 bg-red-50 text-red-700' :
              'border-zinc-300 bg-white text-zinc-600'}`}>
            {a.status === 'complete' && <CheckCircle size={9} />}
            {a.status === 'failed' && <XCircle size={9} />}
            {a.status === 'running' && <Loader2 size={9} className="animate-spin" />}
            {a.role}
          </div>
        ))}
      </div>
    </div>
  );
}
