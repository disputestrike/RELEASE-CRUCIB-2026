/**
 * GoalComposer — Auto-Runner goal input (spec §5.1).
 * Voice (Web Speech API), text file attachments, continuation block for multi-phase goals.
 */
import React, { useMemo, useRef, useState, useCallback, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import JSZip from 'jszip';
import { Mic, MicOff, Paperclip, Plus, ArrowUp, Loader2, Globe, Monitor } from 'lucide-react';
import CostEstimator from './CostEstimator';
import './GoalComposer.css';

const QUICK_CHIPS = ['Build an app', 'Automate workflow', 'Fix project', 'Add a feature'];

const MAX_ATTACH_CHARS = 120000;
const MAX_IMAGE_DATA_CHARS = 48000;

const IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'];
const BINARY_EXTS = ['.pdf', '.docx', '.doc', ...IMAGE_EXTS];

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

export function truncateAttachmentText(text, limit = MAX_ATTACH_CHARS) {
  if (!text) return '';
  if (text.length <= limit) return text;
  return `${text.slice(0, limit)}\n… [truncated]\n`;
}

function decodeXmlEntities(text) {
  if (typeof window === 'undefined' || typeof DOMParser === 'undefined') {
    return text;
  }
  const doc = new DOMParser().parseFromString(`<body>${text}</body>`, 'text/html');
  return doc.documentElement.textContent || '';
}

export function extractPdfTextFromBuffer(buffer) {
  try {
    const bytes = new Uint8Array(buffer);
    let raw = '';
    for (let i = 0; i < bytes.length; i += 1) {
      raw += String.fromCharCode(bytes[i]);
    }
    const matches = raw.match(/\((?:\\.|[^()])+\)/g) || [];
    const chunks = matches
      .map((match) =>
        match
          .slice(1, -1)
          .replace(/\\n/g, ' ')
          .replace(/\\r/g, ' ')
          .replace(/\\t/g, ' ')
          .replace(/\\\(/g, '(')
          .replace(/\\\)/g, ')')
          .replace(/\\\\/g, '\\')
      )
      .map((chunk) => chunk.replace(/[^\x20-\x7E]/g, ' ').replace(/\s+/g, ' ').trim())
      .filter((chunk) => chunk.length >= 3);
    return truncateAttachmentText(chunks.join('\n'));
  } catch {
    return '';
  }
}

export async function extractDocxTextFromBuffer(buffer) {
  try {
    const zip = await JSZip.loadAsync(buffer);
    const docXml = await zip.file('word/document.xml')?.async('string');
    if (!docXml) return '';
    const paragraphs = docXml
      .split(/<\/w:p>/i)
      .map((para) => decodeXmlEntities(para.replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ').trim())
      .filter(Boolean);
    return truncateAttachmentText(paragraphs.join('\n'));
  } catch {
    return '';
  }
}

export function buildExtractedAttachmentBlock({ fileName, label, text, sizeKb }) {
  const trimmed = (text || '').trim();
  if (trimmed) {
    return `\n\n--- Attached ${label}: ${fileName} (${sizeKb}KB) ---\n${trimmed}\n`;
  }
  return `\n\n--- Attached ${label}: ${fileName} (${sizeKb}KB) ---\n[Attached ${label.toLowerCase()} could not be fully extracted. Use any available metadata and ask follow-up questions if needed.]\n`;
}

export function buildImageAttachmentBlock({ fileName, mimeType, sizeKb, dataUrl }) {
  const trimmedDataUrl = truncateAttachmentText(dataUrl || '', MAX_IMAGE_DATA_CHARS);
  return `\n\n--- Attached Image: ${fileName} (${sizeKb}KB) ---\n[Image attached. Use this image as requirement context.]\nMIME: ${mimeType}\nDATA_URL:\n${trimmedDataUrl}\n`;
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
  buildTarget = 'vite_react',
  onBuildTargetChange,
  buildTargets = [],
  continuationNotes = '',
  onContinuationChange,
  /** Unified workspace: hide execution-target grid (backend infers target). */
  showExecutionTargets = true,
  /** Hide continuation textarea (follow-ups use the same composer). */
  showContinuation = true,
  /** Hide quick-start chip row. */
  showQuickChips = true,
  /** `workspace` — lighter shell when embedded under UnifiedWorkspace. */
  composerVariant: _composerVariant = 'default',
  /** Raw API / server message for expandable “Technical details” (friendly string in `error`). */
  errorRaw = null,
  /** Hide title + subtitle block (unified workspace: composer sits under activity feed). */
  showComposerHeader = true,
  composerTitle = 'Auto-Runner',
  /** undefined = default copy; null = hide subtitle entirely */
  composerSubtitle,
}) {
  const navigate = useNavigate();
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

  const appendToGoal = useCallback((block) => {
    const base = goalRef.current;
    const next = `${base}${block}`;
    goalRef.current = next;
    onGoalChange(next);
  }, [onGoalChange]);

  const onPickFiles = useCallback(
    (e) => {
      const fl = e.target.files;
      if (!fl?.length) return;
      Array.from(fl).forEach((file) => {
        const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
        const isBinary = BINARY_EXTS.includes(ext);
        const isImage = IMAGE_EXTS.includes(ext);
        const sizeKb = Math.round(file.size / 1024);

        if (file.size > MAX_ATTACH_CHARS * 2 && !isBinary) {
          appendToGoal(`\n\n--- Attached (skipped, file too large): ${file.name} ---\n`);
          return;
        }

        if (isImage) {
          const reader = new FileReader();
          reader.onload = () => {
            const dataUrl = typeof reader.result === 'string' ? reader.result : '';
            appendToGoal(
              buildImageAttachmentBlock({
                fileName: file.name,
                mimeType: file.type || 'application/octet-stream',
                sizeKb,
                dataUrl,
              }),
            );
          };
          reader.readAsDataURL(file);
          return;
        }

        if (ext === '.pdf') {
          const reader = new FileReader();
          reader.onload = async () => {
            const buffer = reader.result;
            const extractedText = buffer instanceof ArrayBuffer ? extractPdfTextFromBuffer(buffer) : '';
            appendToGoal(
              buildExtractedAttachmentBlock({
                fileName: file.name,
                label: 'PDF',
                text: extractedText,
                sizeKb,
              }),
            );
          };
          reader.readAsArrayBuffer(file);
          return;
        }

        if (ext === '.docx' || ext === '.doc') {
          const reader = new FileReader();
          reader.onload = async () => {
            const buffer = reader.result;
            const extractedText = buffer instanceof ArrayBuffer ? await extractDocxTextFromBuffer(buffer) : '';
            appendToGoal(
              buildExtractedAttachmentBlock({
                fileName: file.name,
                label: 'Document',
                text: extractedText,
                sizeKb,
              }),
            );
          };
          reader.readAsArrayBuffer(file);
          return;
        }

        // Text-based files: read as text
        const reader = new FileReader();
        reader.onload = () => {
          let text = typeof reader.result === 'string' ? reader.result : '';
          text = truncateAttachmentText(text);
          const block = `\n\n--- Attached: ${file.name} ---\n${text}\n`;
          appendToGoal(block);
        };
        reader.onerror = () => {
          appendToGoal(`\n\n--- Attached (read error): ${file.name} ---\n`);
        };
        reader.readAsText(file, 'UTF-8');
      });
      e.target.value = '';
    },
    [appendToGoal],
  );

  const hasContinuation = showContinuation && typeof onContinuationChange === 'function';

  const defaultSubtitle = (
    <>
      Describe what to build. Use voice or attach files (text, PDF, DOCX, images). Press <strong>Send</strong> to plan and
      start the run in one step.
    </>
  );

  return (
    <div className="goal-composer">
      {showComposerHeader && (
        <div className="gc-header">
          <h2 className="gc-title">{composerTitle}</h2>
          {composerSubtitle !== null && (
            <p className="gc-subtitle">{composerSubtitle === undefined ? defaultSubtitle : composerSubtitle}</p>
          )}
        </div>
      )}

      {showExecutionTargets && buildTargets.length > 0 && typeof onBuildTargetChange === 'function' && (
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

      {voiceError && <div className="gc-hint gc-hint-warn">{voiceError}</div>}

      <div className="gc-composer-shell">
        <textarea
          className="gc-input"
          placeholder="e.g. Build a proof-validation microservice with REST API, database persistence, tests, and deploy to Railway."
          value={goal}
          onChange={(e) => onGoalChange(e.target.value)}
          rows={5}
        />
        <div className="gc-composer-footer">
          <div className="gc-composer-footer-left" aria-label="Add context">
            <input
              ref={fileRef}
              type="file"
              className="gc-file-input"
              multiple
              accept=".txt,.md,.json,.csv,.yml,.yaml,.ts,.tsx,.js,.jsx,.py,.sql,.env,.html,.css,.pdf,.docx,.doc,.png,.jpg,.jpeg,.gif,.webp,.svg"
              onChange={onPickFiles}
              aria-hidden
              tabIndex={-1}
            />
            <button
              type="button"
              className="gc-icon-btn"
              onClick={() => fileRef.current?.click()}
              disabled={loading}
              title="Add files"
            >
              <Plus size={20} strokeWidth={2} />
            </button>
            <button
              type="button"
              className="gc-icon-btn"
              onClick={() => fileRef.current?.click()}
              disabled={loading}
              title="Attach files (appended to goal)"
            >
              <Paperclip size={20} strokeWidth={2} />
            </button>
            <button
              type="button"
              className="gc-icon-btn"
              disabled={loading}
              title="Open workspace"
              onClick={() => navigate({ pathname: '/app/workspace' })}
            >
              <Monitor size={20} strokeWidth={2} />
            </button>
          </div>
          <div className="gc-composer-footer-right" aria-label="Send options">
            <Link to="/app/templates" className="gc-icon-btn gc-icon-btn--link" title="Templates & gallery">
              <Globe size={20} strokeWidth={2} />
            </Link>
            <button
              type="button"
              className={`gc-icon-btn ${listening ? 'gc-icon-btn-active' : ''}`}
              onClick={toggleVoice}
              disabled={loading}
              title={listening ? 'Stop voice' : 'Voice input (Chrome / Edge)'}
            >
              {listening ? <MicOff size={20} strokeWidth={2} /> : <Mic size={20} strokeWidth={2} />}
            </button>
            <button
              type="button"
              className={`gc-submit-send ${!loading && goal.trim() && token && !authLoading ? 'gc-submit-send--ready' : ''}`}
              onClick={onSubmit}
              disabled={loading || !goal.trim() || authLoading || !token}
              title="Generate plan"
              aria-label="Generate plan"
            >
              {loading ? <Loader2 size={22} strokeWidth={2} className="gc-submit-spin" /> : <ArrowUp size={22} strokeWidth={2.25} />}
            </button>
          </div>
        </div>
      </div>

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

      {showQuickChips && (
        <div className="gc-chips">
          {QUICK_CHIPS.map((chip) => (
            <button key={chip} type="button" className="gc-chip" onClick={() => onGoalChange(chip)}>
              {chip}
            </button>
          ))}
        </div>
      )}

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
          hasContinuation && (continuationNotes || '').trim()
            ? `${goal}\n\n--- Continuation ---\n${(continuationNotes || '').trim()}`
            : goal
        }
        token={token}
        buildTarget={buildTarget}
        onEstimateReady={onEstimateReady}
      />

      {authLoading && <div className="gc-hint">Starting your session…</div>}

      {error && (
        <div className="gc-error-wrap">
          <div className="gc-error gc-error-friendly">{error}</div>
          {errorRaw ? (
            <details className="gc-error-details">
              <summary className="gc-error-details-summary">Technical details</summary>
              <pre className="gc-error-details-pre">{errorRaw}</pre>
            </details>
          ) : null}
        </div>
      )}
    </div>
  );
}
