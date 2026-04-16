/**
 * Thin wrapper around real POST /api/terminal/create + /api/terminal/{id}/execute.
 */
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API_BASE as API } from '../apiBase';

export default function JobTerminalStrip({ projectId, token }) {
  const [sessionId, setSessionId] = useState(null);
  const [lines, setLines] = useState([]);
  const [cmd, setCmd] = useState('');
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [lines]);

  useEffect(() => {
    setSessionId(null);
    setLines([]);
  }, [projectId]);

  const run = async () => {
    const trimmed = cmd.trim();
    if (!trimmed || !projectId || !token) return;
    setBusy(true);
    setLines((prev) => [...prev, `$ ${trimmed}`]);
    setCmd('');
    let sid = sessionId;
    try {
      if (!sid) {
        const cr = await axios.post(
          `${API}/terminal/create`,
          null,
          { params: { project_id: projectId }, headers: { Authorization: `Bearer ${token}` } },
        );
        sid = cr.data?.session_id || null;
        if (sid) setSessionId(sid);
      }
      if (!sid) {
        setLines((prev) => [
          ...prev,
          '[terminal] No session — enable terminal policy (see CRUCIBAI_TERMINAL_* env) or admin dev.',
        ]);
        return;
      }
      const res = await axios.post(
        `${API}/terminal/${encodeURIComponent(sid)}/execute`,
        { command: trimmed, timeout: 60 },
        { headers: { Authorization: `Bearer ${token}` } },
      );
      const out = res.data?.stdout || res.data?.output || '';
      const err = res.data?.stderr;
      setLines((prev) => [...prev, out, err].filter(Boolean));
    } catch (e) {
      const d = e.response?.data?.detail;
      const msg = typeof d === 'string' ? d : JSON.stringify(d || e.message);
      setLines((prev) => [...prev, msg]);
    } finally {
      setBusy(false);
    }
  };

  if (!projectId) {
    return (
      <div className="c10-terminal c10-terminal--muted">
        Terminal unlocks when this job is linked to a project workspace.
      </div>
    );
  }

  return (
    <div className="c10-terminal">
      <div className="c10-terminal-head">Terminal</div>
      <div className="c10-terminal-body">
        {lines.map((line, i) => (
          <pre key={i} className="c10-terminal-line">{line}</pre>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="c10-terminal-input-row">
        <input
          value={cmd}
          onChange={(e) => setCmd(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !busy && run()}
          placeholder="Shell command…"
          disabled={busy}
          className="c10-terminal-input"
        />
        <button type="button" className="c10-terminal-run" onClick={run} disabled={busy || !cmd.trim()}>
          Run
        </button>
      </div>
    </div>
  );
}
