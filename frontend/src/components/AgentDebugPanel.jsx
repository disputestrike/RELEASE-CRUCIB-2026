import React, { useState, useEffect } from 'react';
import { X, Search, Download, ChevronDown, ChevronRight } from 'lucide-react';
import { getSessions, getSessionEvents, exportSessionAsJSON } from '../lib/agentLogs';

export default function AgentDebugPanel({ onClose }) {
  const [sessions, setSessions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [events, setEvents] = useState([]);
  const [filter, setFilter] = useState('');
  const [expanded, setExpanded] = useState(new Set());

  useEffect(() => { getSessions().then(setSessions); }, []);

  const loadSession = async (id) => {
    setSelected(id);
    setEvents(await getSessionEvents(id));
  };

  const filtered = events.filter(e =>
    !filter ||
    e.type?.includes(filter) ||
    JSON.stringify(e.payload || {}).toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-[860px] max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200">
          <h2 className="font-semibold text-sm text-zinc-900">Agent Debug Logs</h2>
          <button onClick={onClose} className="p-1 hover:bg-zinc-100 rounded">
            <X size={16} />
          </button>
        </div>
        <div className="flex flex-1 overflow-hidden">
          <div className="w-52 border-r border-zinc-200 overflow-y-auto bg-zinc-50 p-2">
            <p className="text-[10px] font-semibold text-zinc-500 uppercase mb-2">Sessions</p>
            {sessions.map(s => (
              <button key={s.id} onClick={() => loadSession(s.id)}
                className={`w-full text-left px-2 py-1.5 rounded text-xs mb-1 transition
                  ${selected === s.id ? 'bg-emerald-100 text-emerald-800' : 'hover:bg-zinc-200 text-zinc-700'}`}>
                <div className="font-mono truncate">{s.id.slice(0, 16)}</div>
                <div className="text-zinc-400 text-[10px]">{new Date(s.lastEvent).toLocaleTimeString()}</div>
              </button>
            ))}
          </div>
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="flex items-center gap-2 px-3 py-2 border-b border-zinc-200">
              <Search size={13} className="text-zinc-400" />
              <input value={filter} onChange={e => setFilter(e.target.value)}
                placeholder="Filter events…"
                className="flex-1 text-xs outline-none" />
              {selected && (
                <button onClick={() => exportSessionAsJSON(events, selected)}
                  className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-800">
                  <Download size={12} /> Export
                </button>
              )}
            </div>
            <div className="flex-1 overflow-y-auto p-3 space-y-1 font-mono text-[11px]">
              {filtered.map((e, i) => {
                const open = expanded.has(i);
                return (
                  <div key={i} className="border border-zinc-200 rounded">
                    <button className="w-full flex items-center gap-2 px-2 py-1 hover:bg-zinc-50 text-left"
                      onClick={() => setExpanded(prev => {
                        const s = new Set(prev);
                        s.has(i) ? s.delete(i) : s.add(i);
                        return s;
                      })}>
                      {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                      <span className="text-emerald-700 font-semibold">{e.type}</span>
                      <span className="text-zinc-400 ml-auto">{new Date(e.timestamp).toLocaleTimeString()}</span>
                    </button>
                    {open && (
                      <pre className="px-3 pb-2 text-zinc-600 whitespace-pre-wrap border-t border-zinc-100">
                        {JSON.stringify(e.payload || {}, null, 2)}
                      </pre>
                    )}
                  </div>
                );
              })}
              {!filtered.length && (
                <p className="text-zinc-400 text-center py-8">
                  {selected ? 'No events match filter' : 'Select a session'}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
