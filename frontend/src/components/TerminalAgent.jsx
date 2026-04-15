import React, { useState, useRef, useEffect } from 'react';
import { Terminal, Send, X } from 'lucide-react';

const BASE = (typeof process !== 'undefined' && process.env?.REACT_APP_API_URL) || '';

export default function TerminalAgent({ projectId, token }) {
  const [lines, setLines] = useState([{ type: 'system', text: 'Terminal ready. Type a command.' }]);
  const [input, setInput] = useState('');
  const [running, setRunning] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [lines]);

  const append = (type, text) => setLines(prev => [...prev, { type, text }]);

  const run = async () => {
    const cmd = input.trim();
    if (!cmd) return;
    setInput('');
    append('input', `$ ${cmd}`);
    setRunning(true);
    try {
      const res = await fetch(`${BASE}/api/terminal/exec`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ command: cmd, project_id: projectId }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.stdout) append('output', data.stdout);
        if (data.stderr) append('error', data.stderr);
        if (data.exit_code !== undefined && data.exit_code !== 0) {
          append('error', `Exit code: ${data.exit_code}`);
        }
      } else {
        append('error', `HTTP ${res.status}`);
      }
    } catch (err) {
      append('error', String(err));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 font-mono text-xs">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-zinc-800">
        <Terminal size={12} className="text-emerald-500" />
        <span className="text-zinc-400">Terminal</span>
        {projectId && <span className="text-zinc-600">· {projectId.slice(0, 8)}</span>}
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-0.5">
        {lines.map((line, i) => (
          <div key={i} className={
            line.type === 'input' ? 'text-zinc-200' :
            line.type === 'error' ? 'text-red-400' :
            line.type === 'system' ? 'text-zinc-500 italic' :
            'text-emerald-400'}>
            {line.text}
          </div>
        ))}
        {running && <div className="text-zinc-500 animate-pulse">Running…</div>}
        <div ref={bottomRef} />
      </div>
      <div className="flex items-center gap-2 border-t border-zinc-800 px-3 py-2">
        <span className="text-emerald-500">$</span>
        <input value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !running) run(); }}
          placeholder="Type a command…"
          className="flex-1 bg-transparent text-zinc-200 outline-none placeholder-zinc-600" />
        <button onClick={run} disabled={running || !input.trim()}
          className="text-emerald-500 disabled:opacity-40 hover:text-emerald-400">
          <Send size={13} />
        </button>
      </div>
    </div>
  );
}
