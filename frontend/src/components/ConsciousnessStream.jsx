/**
 * ConsciousnessStream — Real-time AI thought stream
 * 100% wired to real backend SSE events. ZERO simulation.
 * 
 * Event → Thought mapping:
 *   brain_guidance  → thinking (with real headline from brain)
 *   file_written    → discovery (specific file path)
 *   step_completed  → solution (specific agent name)
 *   step_failed     → problem (specific error)
 *   step_retrying   → thinking (repair in progress)
 *   job_completed   → breakthrough (with real quality score)
 *   security_scan   → security
 *   deploy_success  → deploy
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';

const TYPE_CONFIG = {
  thinking:    { bg:'rgba(39,39,42,0.5)',  border:'#3f3f46', color:'#a1a1aa', icon:'🧠' },
  discovery:   { bg:'rgba(8,145,178,0.1)', border:'rgba(8,145,178,0.35)', color:'#67e8f9', icon:'✨' },
  problem:     { bg:'rgba(161,98,7,0.12)', border:'rgba(161,98,7,0.35)',   color:'#fcd34d', icon:'⚠️' },
  solution:    { bg:'rgba(5,150,105,0.1)', border:'rgba(5,150,105,0.35)',  color:'#6ee7b7', icon:'✅' },
  breakthrough:{ bg:'rgba(109,40,217,0.2)',border:'rgba(109,40,217,0.5)',  color:'#c4b5fd', icon:'⚡' },
  security:    { bg:'rgba(30,58,138,0.15)',border:'rgba(30,58,138,0.4)',   color:'#93c5fd', icon:'🛡️' },
  deploy:      { bg:'rgba(5,150,105,0.15)',border:'rgba(5,150,105,0.4)',   color:'#34d399', icon:'🚀' },
  file:        { bg:'rgba(39,39,42,0.4)',  border:'#52525b',              color:'#d4d4d8', icon:'📄' },
  decision:    { bg:'rgba(124,58,237,0.1)',border:'rgba(124,58,237,0.3)', color:'#a78bfa', icon:'🧩' },
};

// Map real backend event → structured thought
function eventToThought(ev) {
  const t = (ev?.type || ev?.event_type || '').toLowerCase();
  const p = ev?.payload || {};
  const pp = p?.payload || p;
  const id = ev?.id || ev?.event_id || `${t}_${Date.now()}_${Math.random()}`;
  const ts = ev?.created_at ? new Date(ev.created_at).getTime() : Date.now();

  // Brain narration — the primary thought source
  if (t === 'brain_guidance') {
    const headline = pp?.headline || pp?.summary || p?.headline || '';
    const summary = pp?.summary || p?.summary || '';
    const agent = pp?.agent_name || p?.agent_name || 'CrucibAI Brain';
    if (!headline && !summary) return null;
    return { id, type: 'thinking', message: headline || summary,
      detail: summary !== headline ? summary : null, agent, ts };
  }

  // File written — specific path
  if (t.includes('file_written') || t.includes('workspace_write') || (p.path && t.includes('write'))) {
    const path = p.path || p.file_path || '';
    const agent = p.agent_name || '';
    if (!path) return null;
    const filename = path.split('/').pop();
    return { id, type: 'file',
      message: `Writing ${filename}`,
      detail: path !== filename ? path : null,
      agent, ts };
  }

  // Step/agent completed
  if (t === 'step_completed' || t === 'agent_completed' || t === 'phase_completed') {
    const name = p.agent_name || p.step_key || p.phase_name || '';
    if (!name) return null;
    return { id, type: 'solution', message: `${name} complete`, agent: name, ts };
  }

  // Step failed
  if (t === 'step_failed' || t === 'agent_failed') {
    const name = p.agent_name || p.step_key || 'agent';
    const err = (p.error_message || p.error || '').slice(0, 100);
    return { id, type: 'problem',
      message: `Issue in ${name}${err ? ': ' + err : ''}`,
      agent: name, ts };
  }

  // Retrying / repair
  if (t === 'step_retrying' || t === 'repair_started' || t === 'auto_fix') {
    const name = p.agent_name || p.step_key || 'step';
    return { id, type: 'thinking',
      message: `Applying automatic fix for ${name}…`,
      agent: 'Brain Repair', ts };
  }

  // Repair succeeded
  if (t === 'repair_success' || t === 'step_recovered') {
    return { id, type: 'solution',
      message: `Auto-fixed: ${p.agent_name || p.step_key || 'step'} recovered`,
      agent: 'Brain Repair', ts };
  }

  // Security
  if (t.includes('security') || t.includes('agentshield') || t.includes('shield')) {
    const score = p.security_score;
    return { id, type: 'security',
      message: score != null
        ? `Security scan: ${score}/100${p.critical?.length ? ` — ${p.critical.length} issues found` : ' — clean'}`
        : (p.message || 'Security scan running…'),
      agent: 'AgentShield', ts };
  }

  // Skill extracted
  if (t === 'skill_extracted' || t.includes('skill')) {
    return { id, type: 'discovery',
      message: `Learned: ${p.skill_name || p.name || 'new pattern from this build'}`,
      agent: 'Skill Extractor', ts };
  }

  // Architecture decision (from planner)
  if (t === 'architecture_decision' || t === 'stack_selected') {
    return { id, type: 'decision',
      message: p.decision || `Stack: ${p.stack || 'selected'}`,
      detail: p.reason || null,
      agent: 'Architect', ts };
  }

  // Deploy
  if (t === 'deploy_success' || t.includes('deployed')) {
    return { id, type: 'deploy',
      message: `App deployed${p.url ? ` → ${p.url}` : ''}`,
      agent: 'Deploy', ts };
  }

  // Job completed — the big one
  if (t === 'job_completed') {
    const score = p.quality_score;
    const msg = score >= 90 ? `🏆 Build complete — ${score}/100 — Production ready`
              : score >= 75 ? `🚀 Build shipped — ${score}/100 quality`
              : score > 0   ? `✨ Build complete — ${score}/100 quality`
              : '✨ Build complete';
    return { id, type: 'breakthrough', message: msg, agent: 'Orchestrator', ts };
  }

  return null;
}

export default function ConsciousnessStream({ events = [], steps = [], isRunning = false, proof = null }) {
  const [thoughts, setThoughts] = useState([]);
  const [paused, setPaused] = useState(false);
  const scrollRef = useRef(null);
  const seenIds = useRef(new Set());

  // Convert real events → thoughts
  useEffect(() => {
    if (paused) return;
    const newThoughts = [];
    (events || []).forEach(ev => {
      const thought = eventToThought(ev);
      if (!thought) return;
      if (seenIds.current.has(thought.id)) return;
      seenIds.current.add(thought.id);
      newThoughts.push(thought);
    });
    if (newThoughts.length > 0) {
      setThoughts(prev => [...prev, ...newThoughts].slice(-60));
    }
  }, [events, paused]);

  // Also derive thoughts from step status changes
  useEffect(() => {
    if (paused) return;
    (steps || []).forEach(s => {
      const sid = `step_${s.id}_${s.status}`;
      if (seenIds.current.has(sid)) return;
      let thought = null;
      if (s.status === 'running' || s.status === 'verifying') {
        thought = { id: sid, type: 'thinking',
          message: `${s.agent_name || s.step_key} working…`,
          agent: s.agent_name || '', ts: Date.now() };
      } else if (s.status === 'completed') {
        thought = { id: sid, type: 'solution',
          message: `${s.agent_name || s.step_key} complete`,
          agent: s.agent_name || '', ts: Date.now() };
      } else if (s.status === 'failed') {
        thought = { id: sid, type: 'problem',
          message: `${s.agent_name || s.step_key} failed${s.error_message ? ': ' + s.error_message.slice(0,80) : ''}`,
          agent: s.agent_name || '', ts: Date.now() };
      }
      if (thought) {
        seenIds.current.add(sid);
        setThoughts(prev => [...prev, thought].slice(-60));
      }
    });
  }, [steps, paused]);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      requestAnimationFrame(() => { scrollRef.current.scrollTop = scrollRef.current.scrollHeight; });
    }
  }, [thoughts]);

  const cfg = (type) => TYPE_CONFIG[type] || TYPE_CONFIG.thinking;

  const timeStr = (ts) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div style={{ height:'100%', display:'flex', flexDirection:'column', background:'#0a0a0a' }}>
      {/* Header */}
      <div style={{ padding:'10px 16px', borderBottom:'1px solid #27272a',
        display:'flex', alignItems:'center', justifyContent:'space-between', flexShrink:0 }}>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <div style={{ width:8, height:8, borderRadius:'50%',
            background: isRunning ? '#22d3ee' : '#52525b',
            boxShadow: isRunning ? '0 0 6px #22d3ee' : 'none',
            animation: isRunning ? 'pulse 1.4s ease-in-out infinite' : 'none' }} />
          <span style={{ fontSize:12, fontWeight:600, color:'#e4e4e7', letterSpacing:'0.05em' }}>
            SYSTEM CONSCIOUSNESS
          </span>
          {thoughts.length > 0 && (
            <span style={{ fontSize:10, color:'#52525b' }}>{thoughts.length} events</span>
          )}
        </div>
        <button onClick={() => setPaused(p => !p)}
          style={{ fontSize:11, padding:'3px 10px', background:'#27272a',
            border:'1px solid #3f3f46', borderRadius:6, color:'#71717a', cursor:'pointer' }}>
          {paused ? '▶ Resume' : '⏸ Pause'}
        </button>
      </div>

      {/* Stream */}
      <div ref={scrollRef}
        style={{ flex:1, overflowY:'auto', padding:'12px 16px', display:'flex', flexDirection:'column', gap:8 }}>
        {thoughts.length === 0 && (
          <div style={{ textAlign:'center', padding:'40px 0', color:'#3f3f46' }}>
            <div style={{ fontSize:32, marginBottom:8 }}>🧠</div>
            <div style={{ fontSize:13 }}>System initializing…</div>
            <div style={{ fontSize:11, marginTop:4, color:'#27272a' }}>Events will appear here as agents work</div>
          </div>
        )}

        {thoughts.map((thought, idx) => {
          const c = cfg(thought.type);
          const isLatest = idx === thoughts.length - 1;
          return (
            <div key={thought.id}
              style={{ padding:'10px 12px', borderRadius:8,
                background: c.bg, border:`1px solid ${c.border}`,
                opacity: isLatest ? 1 : 0.85,
                transform: isLatest ? 'none' : 'none',
                transition: 'all 0.2s ease' }}>
              <div style={{ display:'flex', alignItems:'flex-start', gap:8 }}>
                <span style={{ fontSize:13, flexShrink:0, marginTop:1 }}>{c.icon}</span>
                <div style={{ flex:1, minWidth:0 }}>
                  <p style={{ fontSize:13, color: c.color, margin:0, lineHeight:1.4 }}>
                    {thought.message}
                  </p>
                  {thought.detail && (
                    <p style={{ fontSize:11, color:'#71717a', margin:'4px 0 0', lineHeight:1.3 }}>
                      {thought.detail}
                    </p>
                  )}
                  <div style={{ display:'flex', alignItems:'center', gap:8, marginTop:6 }}>
                    <span style={{ fontSize:10, color:'#52525b' }}>{timeStr(thought.ts)}</span>
                    {thought.agent && (
                      <span style={{ fontSize:10, padding:'1px 6px',
                        background:'#18181b', border:'1px solid #27272a',
                        borderRadius:4, color:'#71717a' }}>
                        {thought.agent}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}

        {/* Live pulse when running */}
        {isRunning && thoughts.length > 0 && (
          <div style={{ display:'flex', alignItems:'center', gap:6, color:'#52525b', fontSize:11, padding:'4px 0' }}>
            <div style={{ width:6, height:6, borderRadius:'50%', background:'#22d3ee',
              animation:'pulse 1.2s infinite' }} />
            Processing…
          </div>
        )}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity:1; transform:scale(1); }
          50% { opacity:0.5; transform:scale(0.8); }
        }
      `}</style>
    </div>
  );
}
