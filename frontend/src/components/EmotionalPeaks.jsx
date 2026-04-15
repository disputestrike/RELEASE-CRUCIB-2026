/**
 * EmotionalPeaks — Premium build milestone celebrations.
 * NOT gamey. NOT fullscreen popup. Clean toast, top-right.
 * Wired to real quality scores and deploy URLs from backend.
 */
import React, { useState, useEffect, useRef } from 'react';

export default function EmotionalPeaks({ job, steps, proof, stage }) {
  const [peak, setPeak] = useState(null); // { message, sub, url, score, icon }
  const timerRef = useRef(null);
  const celebratedPhases = useRef(new Set());
  const finalShown = useRef(false);

  const showPeak = (data, duration = 5000) => {
    setPeak(data);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setPeak(null), duration);
  };

  // Phase completions
  useEffect(() => {
    if (!steps?.length) return;
    const completedPhases = {};
    steps.forEach(s => {
      if (s.status === 'completed' && s.phase) {
        if (!completedPhases[s.phase]) completedPhases[s.phase] = 0;
        completedPhases[s.phase]++;
      }
    });
    const total = steps.length;
    Object.entries(completedPhases).forEach(([phase, count]) => {
      const phaseKey = `phase_${phase}_${count}`;
      if (celebratedPhases.current.has(phaseKey)) return;
      const phaseSteps = steps.filter(s => s.phase === phase);
      const allDone = phaseSteps.length > 0 && phaseSteps.every(s => s.status === 'completed');
      if (allDone) {
        celebratedPhases.current.add(phaseKey);
        const phaseLabels = { understand:'Analysis complete', foundation:'Foundation ready',
          build:'Core build done', verify:'All checks passed', deliver:'Ready to ship' };
        showPeak({
          icon: '✓',
          message: phaseLabels[phase] || `${phase} complete`,
          sub: `${phaseSteps.length} step${phaseSteps.length>1?'s':''} finished`,
          accent: '#10b981',
        }, 3500);
      }
    });
  }, [steps]);

  // Final build completion — the big moment
  useEffect(() => {
    if (stage !== 'completed' || finalShown.current) return;
    if (!proof) return;
    finalShown.current = true;

    const score = proof.quality_score;
    const url = job?.preview_url || job?.published_url || job?.deploy_url || job?.dev_server_url;

    const icon = score >= 90 ? '🏆' : score >= 75 ? '🚀' : '✨';
    const message = score >= 90 ? `Exceptional — ${score}/100`
                  : score >= 75 ? `Build ready — ${score}/100`
                  : score > 0   ? `Complete — ${score}/100`
                  : 'Build complete';
    const sub = url ? 'App is live' : 'Code ready to deploy';

    showPeak({ icon, message, sub, url, score, accent: score >= 90 ? '#a855f7' : '#10b981' }, 8000);
  }, [stage, proof, job]);

  // Reset on new job
  useEffect(() => {
    celebratedPhases.current = new Set();
    finalShown.current = false;
    setPeak(null);
  }, [job?.id]);

  if (!peak) return null;

  return (
    <div style={{
      position:'fixed', top:56, right:16, zIndex:1000,
      background:'#18181b', border:`1px solid ${peak.accent || '#3f3f46'}`,
      borderRadius:12, padding:'14px 18px', minWidth:260, maxWidth:340,
      boxShadow:`0 8px 32px rgba(0,0,0,0.6), 0 0 0 1px ${peak.accent || '#3f3f46'}20`,
      animation:'slideIn 0.3s cubic-bezier(0.175,0.885,0.32,1.275)',
      display:'flex', flexDirection:'column', gap:6,
    }}>
      <div style={{ display:'flex', alignItems:'center', gap:10, justifyContent:'space-between' }}>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ fontSize:18 }}>{peak.icon}</span>
          <span style={{ fontSize:14, fontWeight:600, color:'#f4f4f5' }}>{peak.message}</span>
        </div>
        <button onClick={() => setPeak(null)}
          style={{ background:'none', border:'none', color:'#52525b', cursor:'pointer', fontSize:14, padding:0 }}>✕</button>
      </div>
      {peak.sub && (
        <div style={{ fontSize:12, color:'#71717a', paddingLeft:26 }}>{peak.sub}</div>
      )}
      {peak.url && (
        <a href={peak.url} target="_blank" rel="noopener noreferrer"
          style={{ marginTop:4, display:'inline-flex', alignItems:'center', gap:6,
            fontSize:12, color: peak.accent || '#22d3ee', textDecoration:'none',
            padding:'5px 10px', background:'rgba(255,255,255,0.05)',
            borderRadius:6, border:`1px solid ${peak.accent}30`, width:'fit-content' }}>
          ↗ Open live app
        </a>
      )}
      {/* Progress bar that drains */}
      <div style={{ height:2, background:'#27272a', borderRadius:2, marginTop:4, overflow:'hidden' }}>
        <div style={{ height:'100%', background: peak.accent || '#22d3ee', borderRadius:2,
          animation:'drain 5s linear forwards' }} />
      </div>

      <style>{`
        @keyframes slideIn {
          from { opacity:0; transform:translateX(20px) scale(0.95); }
          to   { opacity:1; transform:translateX(0) scale(1); }
        }
        @keyframes drain {
          from { width:100%; }
          to   { width:0%; }
        }
      `}</style>
    </div>
  );
}
