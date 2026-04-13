/**
 * Shows the latest brain_guidance event (failure coach or resume coach) as readable next steps.
 */
import React from 'react';
import { Lightbulb, ListOrdered } from 'lucide-react';
import './BrainGuidancePanel.css';

function pickLatestGuidance(events) {
  if (!Array.isArray(events) || !events.length) return null;
  const hits = events.filter((e) => {
    const t = e?.type || e?.event_type;
    return t === 'brain_guidance';
  });
  if (!hits.length) return null;
  const last = hits[hits.length - 1];
  const p =
    last.payload && typeof last.payload === 'object'
      ? last.payload
      : typeof last.payload_json === 'string'
        ? (() => {
            try {
              return JSON.parse(last.payload_json);
            } catch {
              return {};
            }
          })()
        : last;
  if (!p || typeof p !== 'object') return null;
  return {
    headline: p.headline || p.summary?.slice(0, 200) || 'Guidance',
    summary: p.summary || '',
    next_steps: Array.isArray(p.next_steps) ? p.next_steps : [],
    kind: p.kind || '',
    step_key: p.step_key || '',
  };
}

export default function BrainGuidancePanel({ events, jobStatus }) {
  const g = pickLatestGuidance(events);
  if (!g && jobStatus !== 'failed') return null;
  if (!g) {
    return (
      <aside className="bgp-root" aria-label="Build coach">
        <div className="bgp-header">
          <Lightbulb size={14} className="bgp-icon" />
          <span>Build coach</span>
        </div>
        <p className="bgp-muted">
          When a step fails, a short summary and suggested next actions will appear here. You can also type in the
          composer to steer the build and resume.
        </p>
      </aside>
    );
  }

  return (
    <aside className="bgp-root" aria-label="Build coach">
      <div className="bgp-header">
        <Lightbulb size={14} className="bgp-icon" />
        <span>Build coach</span>
        {g.step_key ? (
          <span className="bgp-step" title={g.step_key}>
            {g.step_key}
          </span>
        ) : null}
      </div>
      <p className="bgp-headline">{g.headline}</p>
      {g.summary && g.summary !== g.headline ? <p className="bgp-summary">{g.summary}</p> : null}
      {g.next_steps.length > 0 ? (
        <div className="bgp-steps">
          <div className="bgp-steps-label">
            <ListOrdered size={12} /> Next steps
          </div>
          <ol className="bgp-ol">
            {g.next_steps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
        </div>
      ) : null}
    </aside>
  );
}
