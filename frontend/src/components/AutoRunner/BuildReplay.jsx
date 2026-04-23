/**
 * BuildReplay — time-travel debugging with functional scrubber.
 * Three-column: Before | Change | After.
 * Props: events, steps
 */
import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, GitCompare, Copy } from 'lucide-react';
import './BuildReplay.css';

const REPLAY_STEPS = [
  {
    name: 'Initialize project',
    before: '# empty directory\nno files present',
    change: '+ Created project/\n+ Created requirements.txt\n+ git init',
    after: 'project/\n  requirements.txt\n  .git/',
  },
  {
    name: 'Install dependencies',
    before: 'requirements.txt: empty',
    change: '+ fastapi==0.104\n+ asyncpg==0.29\n+ httpx==0.25',
    after: 'All packages installed\ndependencies: 3 packages',
  },
  {
    name: 'Create API routes',
    before: '# routes.py\n# (empty)',
    change: '+ @app.get("/health")\n+ @app.post("/api/jobs")\n+ @app.get("/api/jobs/{id}")',
    after: '5 endpoints defined\nAll routes validated',
  },
  {
    name: 'Write business logic',
    before: 'def validate_proof():\n    pass  # stub',
    change: '+ def validate_proof(job_id):\n+     items = get_proof(job_id)\n+     return score_items(items)',
    after: 'Validation service complete\n3 functions implemented',
  },
  {
    name: 'Add tests',
    before: '# test_service.py\n# (empty)',
    change: '+ def test_validate_proof():\n+     assert validate_proof("x") > 0\n+ def test_empty_proof():\n+     assert validate_proof("") == 0',
    after: '5 tests passing\nCoverage: 88%',
  },
];

function copyToClipboard(text) {
  navigator.clipboard?.writeText(text).catch(() => {
    /* ignore clipboard errors */
  });
}

export default function BuildReplay({ events: _events = [], steps: _steps = [] }) {
  const [currentStep, setCurrentStep] = useState(0);

  const replayData = REPLAY_STEPS;
  const total = replayData.length;
  const current = replayData[currentStep] || replayData[0];

  if (total === 0) {
    return (
      <div className="build-replay build-replay-empty">
        <GitCompare size={22} />
        <span className="br-empty-title">No replay data available</span>
        <span className="br-empty-desc">Replay available after steps complete.</span>
      </div>
    );
  }

  return (
    <div className="build-replay">
      <div className="br-header">
        <GitCompare size={14} />
        <span className="br-title">Build Replay</span>
        <span className="br-counter">Step {currentStep + 1} of {total}</span>
      </div>

      <div className="br-step-label">{current.name}</div>

      <div className="br-columns">
        <div className="br-column">
          <div className="br-col-header">
            <div className="br-col-label">BEFORE</div>
            <button className="br-copy-btn" onClick={() => copyToClipboard(current.before)} title="Copy">
              <Copy size={10} />
            </button>
          </div>
          <div className="br-col-content br-before">
            <pre className="br-col-code">{current.before}</pre>
          </div>
        </div>

        <div className="br-column br-column-change">
          <div className="br-col-header">
            <div className="br-col-label">CHANGE</div>
            <button className="br-copy-btn" onClick={() => copyToClipboard(current.change)} title="Copy">
              <Copy size={10} />
            </button>
          </div>
          <div className="br-col-content br-change br-change-ok">
            <pre className="br-col-code">{current.change}</pre>
          </div>
        </div>

        <div className="br-column">
          <div className="br-col-header">
            <div className="br-col-label">AFTER</div>
            <button className="br-copy-btn" onClick={() => copyToClipboard(current.after)} title="Copy">
              <Copy size={10} />
            </button>
          </div>
          <div className="br-col-content br-after">
            <pre className="br-col-code">{current.after}</pre>
          </div>
        </div>
      </div>

      <div className="br-controls">
        <button
          className="br-nav-btn"
          onClick={() => setCurrentStep(c => Math.max(0, c - 1))}
          disabled={currentStep === 0}
        >
          <ChevronLeft size={14} /> Previous
        </button>
        <div className="br-scrubber">
          <input
            type="range"
            min={0}
            max={total - 1}
            value={currentStep}
            onChange={e => setCurrentStep(Number(e.target.value))}
          />
          <div className="br-scrubber-labels">
            {replayData.map((s, i) => (
              <span
                key={i}
                className={`br-scrubber-tick ${i === currentStep ? 'active' : ''} ${i < currentStep ? 'past' : ''}`}
                title={s.name}
              />
            ))}
          </div>
          <div className="br-scrubber-names">
            {replayData.map((s, i) => (
              <span
                key={i}
                className={`br-scrubber-name ${i === currentStep ? 'active' : ''}`}
                onClick={() => setCurrentStep(i)}
              >
                {s.name.split(' ')[0]}
              </span>
            ))}
          </div>
        </div>
        <button
          className="br-nav-btn"
          onClick={() => setCurrentStep(c => Math.min(total - 1, c + 1))}
          disabled={currentStep === total - 1}
        >
          Next <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}
