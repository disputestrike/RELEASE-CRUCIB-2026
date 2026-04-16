import React, { useState, useEffect } from 'react';
import { X, Search, Download } from 'lucide-react';
import { getSessions, getSessionEvents } from './agentLogs';

export default function AgentDebugPanel({ onClose }) {
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [events, setEvents] = useState([]);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    getSessions().then(setSessions).catch(() => setSessions([]));
  }, []);

  const loadSession = async (sid) => {
    const evts = await getSessionEvents(sid);
    setEvents(evts);
    setSelectedSession(sid);
  };

  const filtered = events.filter(
    (e) =>
      (e.type || '').toLowerCase().includes(filter.toLowerCase()) ||
      JSON.stringify(e.payload || {}).toLowerCase().includes(filter.toLowerCase()),
  );

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(events, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `crucibai-logs-${selectedSession || 'session'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="c10-debug-overlay" role="dialog" aria-modal="true">
      <div className="c10-debug-modal">
        <div className="c10-debug-header">
          <h2>Agent debug logs</h2>
          <button type="button" className="c10-debug-close" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="c10-debug-body">
          <aside className="c10-debug-sessions">
            <div className="c10-debug-sessions-title">Sessions</div>
            {sessions.map((s) => (
              <button
                key={s.id}
                type="button"
                className={`c10-debug-session ${selectedSession === s.id ? 'active' : ''}`}
                onClick={() => loadSession(s.id)}
              >
                <span className="c10-mono">{s.id.slice(0, 10)}…</span>
                <span className="c10-muted">{new Date(s.lastEvent).toLocaleString()}</span>
              </button>
            ))}
          </aside>
          <div className="c10-debug-main">
            <div className="c10-debug-toolbar">
              <div className="c10-debug-search">
                <Search size={14} aria-hidden />
                <input
                  type="search"
                  placeholder="Filter events…"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                />
              </div>
              <button type="button" className="c10-debug-export" onClick={exportJson}>
                <Download size={14} /> Export
              </button>
            </div>
            <div className="c10-debug-events">
              {filtered.map((e, idx) => (
                <div key={e.id || idx} className="c10-debug-event">
                  <div className="c10-debug-event-meta">
                    <span className="c10-tag">{e.type}</span>
                    <span className="c10-muted">{new Date(e.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <pre className="c10-pre">{JSON.stringify(e.payload ?? {}, null, 2)}</pre>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
