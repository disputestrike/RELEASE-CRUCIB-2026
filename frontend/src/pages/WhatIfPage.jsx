import React, { useState } from 'react';
import SimulationBlock from '../components/SimulationBlock';

// What-If Analysis page: runs scenario simulations against the multi-agent
// deliberation engine and renders the clustered recommendation. Replaces the
// old "Agent Audit" left-pane entry.
export default function WhatIfPage() {
  const [scenario, setScenario] = useState(
    'What if we replace Stripe with LemonSqueezy in the billing flow?'
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const runWhatIf = async () => {
    const s = String(scenario || '').trim();
    if (!s) {
      setError('Describe a scenario to simulate.');
      return;
    }
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await fetch('/api/runtime/what-if', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario: s,
          prompt: s,
          goal: s,
          population_size: 48,
          rounds: 4,
          priors: {
            cost_sensitive: 0.3,
            security_first: 0.35,
            speed_first: 0.35,
          },
        }),
      });
      if (!res.ok) {
        setError(`What-if simulation failed (HTTP ${res.status}).`);
        return;
      }
      const payload = await res.json();
      setResult(payload);
    } catch (e) {
      setError('What-if simulation failed.');
    } finally {
      setLoading(false);
    }
  };

  const simulation = result && result.simulation ? result.simulation : result;
  const personas = (result && (result.personas || result.population)) || [];
  const recommendation = result && (result.recommendation || result.recommended);

  return (
    <div style={{ padding: 24, maxWidth: 960, margin: '0 auto' }}>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#111827', margin: 0 }}>
          What-If Analysis
        </h1>
        <p style={{ fontSize: 13, color: '#6b7280', marginTop: 6 }}>
          Simulate a scenario across a population of agents and inspect how they
          cluster. Useful for vendor swaps, architecture changes, pricing moves.
        </p>
      </div>

      <div
        style={{
          border: '1px solid #e5e7eb',
          borderRadius: 10,
          background: '#fff',
          padding: 16,
          marginBottom: 16,
        }}
      >
        <label
          htmlFor="whatif-scenario"
          style={{ display: 'block', fontSize: 12, color: '#374151', fontWeight: 600, marginBottom: 6 }}
        >
          Scenario
        </label>
        <textarea
          id="whatif-scenario"
          value={scenario}
          onChange={(e) => setScenario(e.target.value)}
          rows={4}
          style={{
            width: '100%',
            border: '1px solid #d1d5db',
            borderRadius: 8,
            padding: 10,
            fontSize: 13,
            fontFamily: 'inherit',
            resize: 'vertical',
          }}
        />
        <div style={{ display: 'flex', gap: 8, marginTop: 10, alignItems: 'center' }}>
          <button
            type="button"
            onClick={runWhatIf}
            disabled={loading}
            style={{
              background: loading ? '#9ca3af' : '#111827',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              padding: '8px 14px',
              fontSize: 13,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Running simulation…' : 'Run Simulation'}
          </button>
          {error && (
            <span style={{ color: '#b91c1c', fontSize: 12 }}>{error}</span>
          )}
        </div>
      </div>

      {simulation ? (
        <SimulationBlock
          simulation={simulation}
          personas={personas}
          recommendation={recommendation}
          onContinue={runWhatIf}
          onStop={() => {}}
          onApplyRecommendation={() => {}}
        />
      ) : (
        !loading && (
          <div
            style={{
              border: '1px dashed #d1d5db',
              borderRadius: 10,
              padding: 24,
              textAlign: 'center',
              color: '#6b7280',
              fontSize: 13,
            }}
          >
            Run a simulation to see clustered agent responses and a
            recommendation.
          </div>
        )
      )}
    </div>
  );
}
