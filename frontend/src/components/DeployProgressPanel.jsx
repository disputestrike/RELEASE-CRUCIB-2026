/**
 * DeployProgressPanel
 *
 * Shows live deploy logs via polling job status, then a branded URL card
 * with copy-button and social share links once the deploy completes.
 */
import { useState, useEffect, useRef } from 'react';
import { CheckCircle2, Copy, ExternalLink, Loader2, Share2, Twitter, Linkedin, X } from 'lucide-react';
import axios from 'axios';

export default function DeployProgressPanel({ jobId, deployUrl, apiBase, token, onClose }) {
  const [logs, setLogs] = useState([]);
  const [done, setDone] = useState(!!deployUrl);
  const [liveUrl, setLiveUrl] = useState(deployUrl || null);
  const [copied, setCopied] = useState(false);
  const logEndRef = useRef(null);
  const pollingRef = useRef(null);

  // Auto-scroll logs
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Auto-open URL when deploy finishes
  useEffect(() => {
    if (done && liveUrl) {
      window.open(liveUrl, '_blank', 'noopener,noreferrer');
    }
  }, [done, liveUrl]);

  // Poll job status until done when we have a jobId
  useEffect(() => {
    if (!jobId || done) return;

    const poll = async () => {
      try {
        const { data } = await axios.get(`${apiBase}/jobs/${jobId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const job = data?.job || data;
        const steps = job?.steps || [];
        const newLogs = steps
          .filter((s) => s.name || s.message)
          .map((s) => ({ text: s.name || s.message, status: s.status }));
        setLogs(newLogs);

        if (job?.status === 'completed' || job?.status === 'failed') {
          setDone(true);
          const url = job?.result?.deploy_url || job?.result?.url;
          if (url) setLiveUrl(url);
          clearInterval(pollingRef.current);
        }
      } catch (_) { /* ignore poll errors */ }
    };

    poll();
    pollingRef.current = setInterval(poll, 2000);
    return () => clearInterval(pollingRef.current);
  }, [jobId, done, apiBase, token]);

  const handleCopy = () => {
    if (!liveUrl) return;
    navigator.clipboard.writeText(liveUrl).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const twitterShare = liveUrl
    ? `https://twitter.com/intent/tweet?text=${encodeURIComponent(`Just deployed my app with @CrucibAI! 🚀 ${liveUrl}`)}`
    : null;
  const linkedinShare = liveUrl
    ? `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(liveUrl)}`
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center p-4 bg-black/50" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-2xl shadow-2xl overflow-hidden"
        style={{ background: 'var(--theme-surface, #1C1C1E)', border: '1px solid var(--theme-border, rgba(255,255,255,0.1))' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-4" style={{ borderBottom: '1px solid var(--theme-border, rgba(255,255,255,0.08))' }}>
          {done ? (
            <CheckCircle2 className="w-5 h-5 text-green-400 shrink-0" />
          ) : (
            <Loader2 className="w-5 h-5 animate-spin shrink-0" style={{ color: 'var(--theme-accent)' }} />
          )}
          <span className="text-sm font-semibold" style={{ color: 'var(--theme-text, #ffffff)' }}>
            {done ? 'Deploy complete!' : 'Deploying…'}
          </span>
          <button
            type="button"
            onClick={onClose}
            className="ml-auto p-1 rounded-lg hover:bg-white/10"
            style={{ color: 'var(--theme-muted)' }}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Logs stream */}
        {!done && (
          <div className="px-5 py-3 max-h-40 overflow-y-auto font-mono text-xs space-y-1" style={{ color: 'var(--theme-muted, #71717a)' }}>
            {logs.length === 0 && (
              <span className="animate-pulse">Starting deploy…</span>
            )}
            {logs.map((l, i) => (
              <div key={i} className="flex items-start gap-2">
                {l.status === 'done' || l.status === 'complete' ? (
                  <span className="text-green-400 shrink-0">✓</span>
                ) : l.status === 'running' ? (
                  <Loader2 className="w-3 h-3 animate-spin shrink-0 mt-0.5" style={{ color: 'var(--theme-accent)' }} />
                ) : (
                  <span className="opacity-40 shrink-0">·</span>
                )}
                <span>{l.text}</span>
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        )}

        {/* Success card */}
        {done && liveUrl && (
          <div className="px-5 py-4 space-y-4">
            {/* URL bar */}
            <div
              className="flex items-center gap-2 px-3 py-2.5 rounded-xl"
              style={{ background: 'rgba(74,222,128,0.07)', border: '1px solid rgba(74,222,128,0.2)' }}
            >
              <code className="flex-1 text-xs truncate" style={{ color: '#86efac' }}>{liveUrl}</code>
              <button
                type="button"
                onClick={handleCopy}
                title="Copy URL"
                className="shrink-0 p-1 rounded hover:bg-white/10"
                style={{ color: copied ? '#4ade80' : 'var(--theme-muted)' }}
              >
                <Copy className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Primary CTA */}
            <a
              href={liveUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl text-sm font-semibold transition hover:opacity-90"
              style={{ background: 'var(--theme-accent, #7c3aed)', color: '#fff' }}
            >
              Visit site <ExternalLink className="w-3.5 h-3.5" />
            </a>

            {/* Social share */}
            <div className="flex items-center gap-2">
              <span className="text-xs mr-1" style={{ color: 'var(--theme-muted)' }}>Share:</span>
              {twitterShare && (
                <a
                  href={twitterShare}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition hover:bg-white/10"
                  style={{ color: 'var(--theme-muted)', border: '1px solid var(--theme-border, rgba(255,255,255,0.1))' }}
                >
                  <Twitter className="w-3 h-3" /> Twitter / X
                </a>
              )}
              {linkedinShare && (
                <a
                  href={linkedinShare}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition hover:bg-white/10"
                  style={{ color: 'var(--theme-muted)', border: '1px solid var(--theme-border, rgba(255,255,255,0.1))' }}
                >
                  <Linkedin className="w-3 h-3" /> LinkedIn
                </a>
              )}
              <button
                type="button"
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition hover:bg-white/10"
                style={{ color: 'var(--theme-muted)', border: '1px solid var(--theme-border, rgba(255,255,255,0.1))' }}
              >
                <Share2 className="w-3 h-3" /> {copied ? 'Copied!' : 'Copy link'}
              </button>
            </div>
          </div>
        )}

        {/* Done but no URL */}
        {done && !liveUrl && (
          <div className="px-5 py-4 text-center text-sm" style={{ color: 'var(--theme-muted)' }}>
            Deploy finished. Check your deploy dashboard for the live URL.
          </div>
        )}
      </div>
    </div>
  );
}
