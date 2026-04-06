/**
 * GoalComposer — Auto-Runner goal input (spec §5.1).
 * Voice (Web Speech API), text file attachments, continuation block for multi-phase goals.
 */
import React, { useMemo, useRef, useState, useCallback, useEffect } from 'react';
import { Mic, MicOff, Paperclip } from 'lucide-react';
import CostEstimator from './CostEstimator';
import './GoalComposer.css';

const QUICK_CHIPS = ['Build an app', 'Automate workflow', 'Fix project', 'Add a feature'];

const MAX_ATTACH_CHARS = 120000;

function smartTags(goal) {
  const g = goal.toLowerCase();
  const tags = [];
  if (/microservice|service api|small service/.test(g)) tags.push('microservice');
  if (/rest|graphql|api route|endpoint/.test(g)) tags.push('REST API');
  if (/postgres|postgresql|sql|prisma|typeorm|database/.test(g)) tags.push('PostgreSQL');
  if (/railway|deploy|docker|kubernetes|ci\/cd/.test(g)) tags.push('Railway deploy');
  if (/test|jest|vitest|pytest/.test(g)) tags.push('Tests');
  return [...new Set(tags)];
}

export default function GoalComposer({
  goal,
  onGoalChange,
  onSubmit,
  loading,
  error,
  token,
  onEstimateReady,
  authLoading = false,
  onRetrySession,
  buildTarget = 'vite_react',
  onBuildTargetChange,
  buildTargets = [],
  continuationNotes = '',
  onContinuationChange,
}) {
  const tags = useMemo(() => (goal.length >= 12 ? smartTags(goal) : []), [goal]);
  const fileRef = useRef(null);
  const goalRef = useRef(goal);
  useEffect(() => {
    goalRef.current = goal;
  }, [goal]);
  const [listening, setListening] = useState(false);
  const [voiceError, setVoiceError] = useState(null);
  const recogRef = useRef(null);

  const stopVoice = useCallback(() => {
    try {
      recogRef.current?.stop?.();
    } catch {
      /* ignore */
    }
    recogRef.current = null;
    setListening(false);
  }, []);

  useEffect(() => () => stopVoice(), [stopVoice]);

  const toggleVoice = useCallback(() => {
    setVoiceError(null);
    if (listening) {
      stopVoice();
      return;
    }
    const SR = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition);
    if (!SR) {
      setVoiceError('Voice input needs Chrome or Edge (Web Speech API).');
      return;
    }
    const r = new SR();
    r.lang = 'en-US';
    r.continuous = true;
    r.interimResults = false;
    r.onerror = () => {
      setVoiceError('Voice recognition error — try again or type.');
      stopVoice();
    };
    r.onend = () => {
      setListening(false);
      recogRef.current = null;
    };
    r.onresult = (ev) => {
      let chunk = '';
      for (let i = ev.resultIndex; i < ev.results.length; i += 1) {
        if (ev.results[i].isFinal) chunk += ev.results[i][0].transcript;
      }
      if (chunk.trim()) {
        const g = goalRef.current;
        const sep = g && !/\s$/.test(g) ? ' ' : '';
        const next = `${g}${sep}${chunk.trim()}`;
        goalRef.current = next;
        onGoalChange(next);
      }
    };
    recogRef.current = r;
    try {
      r.start();
      setListening(true);
    } catch {
      setVoiceError('Could not start microphone — check permissions.');
    }
  }, [listening, onGoalChange, stopVoice]);

  const onPickFiles = useCallback(
    (e) => {
      const fl = e.target.files;
      if (!fl?.length) return;
      Array.from(fl).forEach((file) => {
        if (file.size > MAX_ATTACH_CHARS * 2) {
          const base = goalRef.current;
          const next = `${base}\n\n--- Attached (skipped, file too large): ${file.name} ---\n`;
          goalRef.current = next;
          onGoalChange(next);
          return;
        }
        const reader = new FileReader();
        reader.onload = () => {
          let text = typeof reader.result === 'string' ? reader.result : '';
          if (text.length > MAX_ATTACH_CHARS) {
            text = `${text.slice(0, MAX_ATTACH_CHARS)}\n… [truncated]\n`;
          }
          const block = `\n\n--- Attached: ${file.name} ---\n${text}\n`;
          const base = goalRef.current;
          const next = `${base}${block}`;
          goalRef.current = next;
          onGoalChange(next);
        };
        reader.onerror = () => {
          const base = goalRef.current;
          const next = `${base}\n\n--- Attached (read error): ${file.name} ---\n`;
          goalRef.current = next;
          onGoalChange(next);
        };
        reader.readAsText(file, 'UTF-8');
      });
      e.target.value = '';
    },
    [onGoalChange],
  );

  const hasContinuation = typeof onContinuationChange === 'function';

  return (
    <div className="goal-composer">
      <div className="gc-header">
        <h2 className="gc-title">Auto-Runner</h2>
        <p className="gc-subtitle">
          Describe your goal… Pick an execution target (apps, sites, APIs, automation, agents). Use voice or attach text
          files. After a run, use <strong>Continuation</strong> so the next plan includes what to build next — no separate
          comment thread required.
        </p>
      </div>

      {buildTargets.length > 0 && typeof onBuildTargetChange === 'function' && (
        <div className="gc-build-targets" role="group" aria-label="Execution target">
          <div className="gc-bt-label">Execution target</div>
          <div className="gc-bt-grid">
            {buildTargets.map((t) => (
              <button
                key={t.id}
                type="button"
                className={`gc-bt-card ${buildTarget === t.id ? 'active' : ''}`}
                onClick={() => onBuildTargetChange(t.id)}
              >
                <span className="gc-bt-title">{t.label}</span>
                <span className="gc-bt-tagline">{t.tagline}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="gc-input-toolbar">
        <input
          ref={fileRef}
          type="file"
          className="gc-file-input"
          multiple
          accept=".txt,.md,.json,.csv,.yml,.yaml,.ts,.tsx,.js,.jsx,.py,.sql,.env,.html,.css"
          onChange={onPickFiles}
          aria-hidden
          tabIndex={-1}
        />
        <button
          type="button"
          className="gc-tool-btn"
          onClick={() => fileRef.current?.click()}
          disabled={loading}
          title="Attach text-based files (content appended to goal)"
        >
          <Paperclip size={18} strokeWidth={2} />
          <span>Attach</span>
        </button>
        <button
          type="button"
          className={`gc-tool-btn ${listening ? 'gc-tool-btn-active' : ''}`}
          onClick={toggleVoice}
          disabled={loading}
          title={listening ? 'Stop voice' : 'Speak your goal (Chrome / Edge)'}
        >
          {listening ? <MicOff size={18} strokeWidth={2} /> : <Mic size={18} strokeWidth={2} />}
          <span>{listening ? 'Stop' : 'Voice'}</span>
        </button>
      </div>
      {voiceError && <div className="gc-hint gc-hint-warn">{voiceError}</div>}

      <textarea
        className="gc-input"
        placeholder="e.g. Build a proof-validation microservice with REST API, database persistence, tests, and deploy to Railway."
        value={goal}
        onChange={(e) => onGoalChange(e.target.value)}
        rows={5}
      />

      {hasContinuation && (
        <div className="gc-continuation">
          <label className="gc-continuation-label" htmlFor="gc-continuation-field">
            Continuation / next phase
          </label>
          <p className="gc-continuation-hint">
            Appended automatically when you click <strong>Generate Plan</strong> (e.g. “add Stripe webhooks”, “harden
            tenancy on quotes table”). Keeps multi-step work in one flow.
          </p>
          <textarea
            id="gc-continuation-field"
            className="gc-continuation-input"
            placeholder="Optional — what to do after the last run, or extra constraints for this plan…"
            value={continuationNotes}
            onChange={(e) => onContinuationChange(e.target.value)}
            rows={3}
          />
        </div>
      )}

      <div className="gc-chips">
        {QUICK_CHIPS.map((chip) => (
          <button key={chip} type="button" className="gc-chip" onClick={() => onGoalChange(chip)}>
            {chip}
          </button>
        ))}
      </div>

      {tags.length > 0 && (
        <div className="gc-detect-row">
          <span className="gc-detect-label">Detected</span>
          <div className="gc-detect-tags">
            {tags.map((t) => (
              <span key={t} className="gc-detect-pill">
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      <CostEstimator
        goal={
          (continuationNotes || '').trim()
            ? `${goal}\n\n--- Continuation ---\n${(continuationNotes || '').trim()}`
            : goal
        }
        token={token}
        buildTarget={buildTarget}
        onEstimateReady={onEstimateReady}
      />

      {authLoading && <div className="gc-hint">Starting your session…</div>}
      {!authLoading && !token && (
        <div className="gc-hint gc-hint-warn">
          No API session yet — plans and jobs need a signed-in or guest token.{' '}
          {onRetrySession && (
            <button type="button" className="gc-linkish" onClick={onRetrySession}>
              Start guest session
            </button>
          )}
        </div>
      )}

      {error && <div className="gc-error">{error}</div>}

      <button
        type="button"
        className="gc-submit"
        onClick={onSubmit}
        disabled={loading || !goal.trim() || authLoading || !token}
      >
        {loading ? 'Generating plan...' : 'Generate Plan'}
      </button>
    </div>
  );
}
