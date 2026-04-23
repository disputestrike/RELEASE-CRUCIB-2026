/** CF28 — VoiceRecorder: mic capture + POST to /api/voice/transcribe. */
import { useCallback, useEffect, useRef, useState } from 'react';
import { API_BASE as API } from '../../apiBase';

export default function VoiceRecorder({ onTranscript, sessionId }) {
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);

  const supported = typeof navigator !== 'undefined'
    && !!navigator.mediaDevices?.getUserMedia
    && typeof window !== 'undefined'
    && typeof window.MediaRecorder !== 'undefined';

  const start = useCallback(async () => {
    if (!supported) { setError('Browser does not support voice input.'); return; }
    setError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => { if (e.data?.size) chunksRef.current.push(e.data); };
      rec.onstop = async () => {
        setRecording(false);
        setBusy(true);
        try {
          const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
          const form = new FormData();
          form.append('audio', blob, 'clip.webm');
          if (sessionId) form.append('session_id', sessionId);
          const r = await fetch(`${API}/voice/transcribe`, { method: 'POST', body: form });
          const data = await r.json();
          if (data?.text && onTranscript) onTranscript(data.text);
        } catch (err) {
          setError(String(err?.message || err));
        } finally {
          setBusy(false);
          stream.getTracks().forEach((t) => t.stop());
        }
      };
      mediaRef.current = rec;
      rec.start();
      setRecording(true);
    } catch (err) {
      setError(String(err?.message || err));
    }
  }, [supported, sessionId, onTranscript]);

  const stop = useCallback(() => {
    mediaRef.current?.stop?.();
  }, []);

  useEffect(() => () => { mediaRef.current?.stop?.(); }, []);

  if (!supported) return null;
  return (
    <div data-testid="voice-recorder" style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
      <button
        type="button"
        onClick={recording ? stop : start}
        disabled={busy}
        title={recording ? 'Stop recording' : 'Record voice'}
        style={{
          padding: '8px 12px', borderRadius: 8,
          background: recording ? '#dc2626' : '#1a1a1a',
          color: '#fff', border: 0, fontSize: 13, fontWeight: 600, cursor: 'pointer',
        }}
      >{busy ? 'Transcribing…' : recording ? '■ Stop' : '🎙 Speak'}</button>
      {error && <span style={{ fontSize: 12, color: '#dc2626' }}>{error}</span>}
    </div>
  );
}
