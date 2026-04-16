/**
 * InterruptibleFlow — Mid-build steering with typed interrupt commands.
 * Wired to real /api/jobs/{id}/steer endpoint.
 * Shows before→after when user redirects.
 */
import React, { useState, useCallback } from 'react';
import axios from 'axios';
import { API_BASE as API } from '../apiBase';

const QUICK_ACTIONS = [
  { label: '⏭ Skip phase',     kind: 'skip_phase',       command: 'skip current phase and move to next' },
  { label: '↻ Retry with fix', kind: 'retry_with_fix',   command: 'retry with automatic fixes applied' },
  { label: '⏸ Pause',          kind: 'pause_build',      command: 'pause the build' },
  { label: '🧪 Simulate scenario', kind: 'open_simulation_modal', command: '' },
  { label: '+ Add feature',    kind: 'add_requirement',  command: '' },
];

export default function InterruptibleFlow({ jobId, steps, isRunning, token, onSimulateScenario }) {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null); // { accepted, summary, before, after }
  const [error, setError] = useState(null);
  const [addFeatureMode, setAddFeatureMode] = useState(false);

  const activeStep = steps?.find(s => s.status === 'running' || s.status === 'verifying');
  const activePhase = activeStep?.phase || '';
  const runningCount = steps?.filter(s => s.status === 'running' || s.status === 'verifying').length || 0;

  const sendInterrupt = useCallback(async (kind, command) => {
    if (!jobId || !command.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await axios.post(`${API}/jobs/${jobId}/steer`, {
        action: 'interrupt',
        kind,
        instruction: command,
        phase_id: activeStep?.id || null,
        phase_name: activePhase,
        timestamp: Date.now(),
        resume: kind !== 'pause_build',
      }, { headers, timeout: 15000 });

      const data = res.data || {};
      setResult({
        accepted: data.accepted !== false,
        summary: data.summary || data.message || 'Redirect accepted',
        before: data.before_phase || activePhase,
        after: data.after_phase || data.updated_phase || null,
        affected: data.affected_agents || [],
      });
      setInput('');
      setAddFeatureMode(false);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Redirect failed');
    } finally {
      setLoading(false);
    }
  }, [jobId, activeStep, activePhase, token]);

  const handleQuickAction = (action) => {
    if (action.kind === 'open_simulation_modal') {
      if (typeof onSimulateScenario === 'function') onSimulateScenario();
      return;
    }
    if (action.kind === 'add_requirement') {
      setAddFeatureMode(true);
      return;
    }
    sendInterrupt(action.kind, action.command);
  };

  const handleCustom = () => {
    if (!input.trim()) return;
    sendInterrupt('custom_instruction', input.trim());
  };

  if (!isRunning && !result) return null;

  return (
    <div style={{ borderTop:'1px solid #27272a', padding:16, background:'rgba(9,9,11,0.8)', flexShrink:0 }}>

      {/* Active status bar */}
      {isRunning && (
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:12 }}>
          <div style={{ display:'flex', alignItems:'center', gap:8 }}>
            <div style={{ width:7, height:7, borderRadius:'50%', background:'#22d3ee',
              animation:'pulse 1.2s ease-in-out infinite' }} />
            <span style={{ fontSize:12, color:'#71717a' }}>
              {activePhase ? `${activePhase} in progress` : 'Building'}
              {runningCount > 0 && ` · ${runningCount} agent${runningCount > 1 ? 's' : ''} working`}
            </span>
          </div>
          <span style={{ fontSize:10, color:'#3f3f46', fontWeight:600, letterSpacing:'0.08em' }}>
            INTERRUPTIBLE
          </span>
        </div>
      )}

      {/* Result: before → after */}
      {result && (
        <div style={{ marginBottom:12, padding:'8px 12px', borderRadius:8,
          background: result.accepted ? 'rgba(5,150,105,0.1)' : 'rgba(161,98,7,0.1)',
          border: `1px solid ${result.accepted ? 'rgba(5,150,105,0.3)' : 'rgba(161,98,7,0.3)'}` }}>
          <div style={{ fontSize:12, color: result.accepted ? '#6ee7b7' : '#fcd34d', fontWeight:500, marginBottom:4 }}>
            {result.accepted ? '✓ Build redirected' : '⚠ Redirect noted'}
          </div>
          <div style={{ fontSize:12, color:'#a1a1aa' }}>{result.summary}</div>
          {result.before && result.after && result.before !== result.after && (
            <div style={{ fontSize:11, color:'#71717a', marginTop:6, display:'flex', gap:8, alignItems:'center' }}>
              <span style={{ textDecoration:'line-through' }}>{result.before}</span>
              <span>→</span>
              <span style={{ color:'#67e8f9' }}>{result.after}</span>
            </div>
          )}
          {result.affected?.length > 0 && (
            <div style={{ fontSize:11, color:'#52525b', marginTop:4 }}>
              Affected: {result.affected.slice(0,3).join(', ')}{result.affected.length > 3 ? ` +${result.affected.length-3}` : ''}
            </div>
          )}
          <button onClick={() => setResult(null)}
            style={{ fontSize:10, color:'#52525b', background:'none', border:'none', cursor:'pointer', marginTop:4 }}>
            dismiss
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ marginBottom:12, padding:'6px 10px', borderRadius:6,
          background:'rgba(127,29,29,0.2)', border:'1px solid rgba(127,29,29,0.4)',
          fontSize:12, color:'#fca5a5', display:'flex', justifyContent:'space-between' }}>
          <span>⚠ {error}</span>
          <button onClick={() => setError(null)} style={{ background:'none', border:'none', color:'#f87171', cursor:'pointer', fontSize:12 }}>✕</button>
        </div>
      )}

      {/* Quick actions */}
      {isRunning && !addFeatureMode && (
        <div style={{ display:'flex', gap:8, marginBottom:12, flexWrap:'wrap' }}>
          {QUICK_ACTIONS.map(action => (
            <button key={action.kind} onClick={() => handleQuickAction(action)}
              disabled={loading}
              style={{ padding:'5px 12px', background:'#18181b', border:'1px solid #3f3f46',
                borderRadius:6, fontSize:12, color: loading ? '#52525b' : '#a1a1aa',
                cursor: loading ? 'not-allowed' : 'pointer', transition:'all 0.15s',
                display:'flex', alignItems:'center', gap:4 }}>
              {loading && action.kind !== 'add_requirement' ? '…' : action.label}
            </button>
          ))}
        </div>
      )}

      {/* Custom input / add feature mode */}
      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleCustom()}
          placeholder={addFeatureMode
            ? "Describe the feature to add… (e.g., 'add dark mode toggle')"
            : "Redirect agents… (e.g., 'skip Stripe, add auth first')"}
          disabled={loading || !isRunning}
          style={{ flex:1, background:'transparent', border:'none', outline:'none',
            fontSize:13, color:'#e4e4e7', placeholder:'#3f3f46' }} />
        <button onClick={handleCustom}
          disabled={!input.trim() || loading || !isRunning}
          style={{ padding:'6px 14px', background: input.trim() && isRunning ? '#0891b2' : '#27272a',
            border:'none', borderRadius:6, fontSize:12, fontWeight:500,
            color: input.trim() && isRunning ? '#fff' : '#52525b',
            cursor: input.trim() && isRunning ? 'pointer' : 'not-allowed',
            transition:'all 0.15s' }}>
          {loading ? '…' : 'Redirect'}
        </button>
      </div>

      {/* Suggestions when user starts typing */}
      {input.length > 2 && isRunning && (
        <div style={{ marginTop:8, display:'flex', gap:6, flexWrap:'wrap' }}>
          {[
            'make it dark mode',
            'add Stripe billing',
            'use Supabase instead',
            'skip tests for now',
            'add admin panel',
          ].filter(s => s.includes(input.toLowerCase())).slice(0,3).map(s => (
            <button key={s} onClick={() => setInput(s)}
              style={{ fontSize:11, padding:'3px 8px', background:'#18181b',
                border:'1px solid #27272a', borderRadius:4, color:'#71717a', cursor:'pointer' }}>
              {s}
            </button>
          ))}
        </div>
      )}

      <style>{`@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(0.8)} }`}</style>
    </div>
  );
}
