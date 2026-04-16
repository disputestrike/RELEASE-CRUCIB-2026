import React from 'react';

export default function SimulationBlock({
  simulation,
  personas = [],
  recommendation,
  onContinue,
  onStop,
  onApplyRecommendation,
}) {
  if (!simulation) return null;
  const clusters = Array.isArray(simulation.clusters) ? simulation.clusters : [];
  const shift = simulation.sentiment_shift || {};
  const totalPopulation = Array.isArray(personas) ? personas.length : 0;
  const dominantCluster = clusters.length
    ? clusters.reduce((best, c) => ((c.size || 0) > (best.size || 0) ? c : best), clusters[0])
    : null;
  const consensusRatio = totalPopulation > 0 && dominantCluster
    ? Math.min(1, Math.max(0, Number(dominantCluster.size || 0) / totalPopulation))
    : 0;

  return (
    <div style={{ marginTop: 8, border: '1px solid #d1d5db', borderRadius: 10, background: '#fafafa' }}>
      <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb', fontSize: 12, color: '#374151', fontWeight: 600 }}>
        Scenario Simulation
      </div>
      <div style={{ padding: 12, fontSize: 12, color: '#4b5563' }}>
        <div style={{ marginBottom: 8 }}>
          Round {simulation.round} {simulation.consensus_emerging ? '• Consensus emerging' : '• Debate still open'}
        </div>
        {totalPopulation > 0 && (
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 4 }}>
              Persona population: {totalPopulation} • dominant support {Math.round(consensusRatio * 100)}%
            </div>
            <div style={{ height: 6, background: '#e5e7eb', borderRadius: 999, overflow: 'hidden' }}>
              <div style={{ width: `${Math.round(consensusRatio * 100)}%`, height: '100%', background: '#10b981' }} />
            </div>
            <div style={{ marginTop: 6, color: '#6b7280', fontSize: 11 }}>
              {personas.slice(0, 6).map((p, i) => (
                <span key={`persona-${i}`} style={{ marginRight: 8 }}>
                  {p.role}:{p.prior}
                </span>
              ))}
            </div>
          </div>
        )}
        {clusters.map((c) => (
          <div key={c.id} style={{ marginBottom: 10, border: '1px solid #e5e7eb', borderRadius: 8, background: '#fff', padding: 10 }}>
            <div style={{ fontWeight: 600, color: '#1f2937' }}>
              {c.id} ({c.size} agents)
            </div>
            <div style={{ marginTop: 4 }}>{c.position}</div>
            {Array.isArray(c.key_arguments) && c.key_arguments.length > 0 && (
              <div style={{ marginTop: 6, color: '#6b7280' }}>
                {c.key_arguments.slice(0, 3).map((a, i) => (
                  <div key={`${c.id}-${i}`}>• {a}</div>
                ))}
              </div>
            )}
          </div>
        ))}

        <div style={{ marginBottom: 8 }}>
          Sentiment shift: current {Number(shift.pro_current || 0) >= 0 ? '+' : ''}{shift.pro_current || 0} • change {Number(shift.pro_change || 0) >= 0 ? '+' : ''}{shift.pro_change || 0}
        </div>

        {recommendation && (
          <div style={{ border: '1px solid #bbf7d0', background: '#ecfdf5', borderRadius: 8, padding: 10, marginBottom: 8 }}>
            <div style={{ fontWeight: 600, color: '#065f46' }}>Recommended action ({Math.round((recommendation.confidence || 0) * 100)}%)</div>
            <div style={{ marginTop: 4 }}>{recommendation.recommended_action}</div>
            {Array.isArray(recommendation.tradeoffs) && recommendation.tradeoffs.length > 0 && (
              <div style={{ marginTop: 6, color: '#047857' }}>
                {recommendation.tradeoffs.slice(0, 3).map((t, i) => (
                  <div key={`t-${i}`}>• {t}</div>
                ))}
              </div>
            )}
            <div style={{ marginTop: 8 }}>
              <button type="button" onClick={onApplyRecommendation} style={{ border: '1px solid #059669', color: '#fff', background: '#059669', borderRadius: 6, padding: '5px 10px', fontSize: 12, cursor: 'pointer' }}>
                Apply Recommendation
              </button>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" onClick={onContinue} style={{ border: '1px solid #d1d5db', background: '#fff', borderRadius: 6, padding: '5px 10px', fontSize: 12, cursor: 'pointer' }}>
            Continue
          </button>
          <button type="button" onClick={onStop} style={{ border: '1px solid #d1d5db', background: '#fff', borderRadius: 6, padding: '5px 10px', fontSize: 12, cursor: 'pointer' }}>
            Stop & Recommend
          </button>
        </div>
      </div>
    </div>
  );
}
