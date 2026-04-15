import React, { useState, useEffect } from 'react';
import { Shield, CheckCircle, AlertTriangle, XCircle, Zap, Brain } from 'lucide-react';
import { trustPanelState } from '../lib/trustPanel';
import { memoryGraph } from '../lib/memoryGraph';
import { permissionEngine } from '../lib/permissionEngine';

export default function TrustPanel({ jobId, token }) {
  const [state, setState] = useState({
    quality: 0, security: null, errors: 0, deployReady: false,
  });
  const [memStats, setMemStats] = useState({ total: 0 });
  const [permStats, setPermStats] = useState({ safe: 0, total: 0 });

  useEffect(() => {
    const unsub = trustPanelState.subscribe(s => setState({ ...s }));
    if (jobId && token) trustPanelState.loadFromJob(jobId, token);
    const interval = setInterval(() => {
      setMemStats(memoryGraph.getStats());
      setPermStats(permissionEngine.getStats());
    }, 3000);
    return () => { unsub(); clearInterval(interval); };
  }, [jobId, token]);

  const label = trustPanelState.getLabel();
  const qualityColor = state.quality >= 75 ? '#10b981' : state.quality >= 60 ? '#f59e0b' : '#ef4444';

  return (
    <div className="flex items-center gap-3 text-xs px-3 py-1 bg-zinc-50 border-t border-zinc-200">
      {/* Quality score */}
      <div className="flex items-center gap-1">
        <Zap size={11} style={{ color: qualityColor }} />
        <span className="text-zinc-500">Quality:</span>
        <span className="font-semibold" style={{ color: qualityColor }}>
          {state.quality > 0 ? `${state.quality}/100` : '—'}
        </span>
      </div>
      <div className="w-px h-3 bg-zinc-300" />
      {/* Security */}
      <div className="flex items-center gap-1">
        {state.security === 'passed' && <CheckCircle size={11} className="text-emerald-600" />}
        {state.security === 'failed' && <XCircle size={11} className="text-red-500" />}
        {state.security === 'scanning' && <Shield size={11} className="text-amber-500 animate-pulse" />}
        {!state.security && <Shield size={11} className="text-zinc-400" />}
        <span className="text-zinc-500">Security:</span>
        <span className={`font-medium ${
          state.security === 'passed' ? 'text-emerald-600' :
          state.security === 'failed' ? 'text-red-500' : 'text-zinc-400'
        }`}>{state.security || '—'}</span>
      </div>
      <div className="w-px h-3 bg-zinc-300" />
      {/* Errors */}
      <div className="flex items-center gap-1">
        {state.errors > 0
          ? <AlertTriangle size={11} className="text-amber-500" />
          : <CheckCircle size={11} className="text-emerald-500" />}
        <span className="text-zinc-500">Errors:</span>
        <span className={`font-medium ${state.errors > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
          {state.errors}
        </span>
      </div>
      <div className="w-px h-3 bg-zinc-300" />
      {/* Memory */}
      <div className="flex items-center gap-1">
        <Brain size={11} className="text-purple-500" />
        <span className="text-zinc-500">Memory:</span>
        <span className="font-medium text-purple-600">{memStats.total}</span>
      </div>
      <div className="w-px h-3 bg-zinc-300" />
      {/* Permissions */}
      <div className="flex items-center gap-1">
        <Shield size={11} className="text-blue-500" />
        <span className="text-zinc-500">Trusted:</span>
        <span className="font-medium text-blue-600">{permStats.safe}</span>
      </div>
      {state.deployReady && (
        <>
          <div className="w-px h-3 bg-zinc-300" />
          <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded font-medium">
            Deploy Ready
          </span>
        </>
      )}
    </div>
  );
}
