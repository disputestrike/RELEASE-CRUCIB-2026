import React, { useState, useEffect } from 'react';
import { Plus, FolderOpen, Play, Layers, Settings, Zap, ChevronRight } from 'lucide-react';
import { getWorkflows } from '../lib/backendIntegration';

const NAV = [
  { id: 'workspace', icon: FolderOpen, label: 'Workspace' },
  { id: 'runs',      icon: Play,       label: 'Runs' },
  { id: 'workflows', icon: Zap,        label: 'Workflows' },
  { id: 'templates', icon: Layers,     label: 'Templates' },
  { id: 'settings',  icon: Settings,   label: 'Settings' },
];

const TEMPLATES = [
  { id: 'saas',   label: 'SaaS Starter',   desc: 'Auth + DB + Stripe' },
  { id: 'store',  label: 'Store Starter',  desc: 'Cart + Checkout' },
  { id: 'mobile', label: 'Mobile Starter', desc: 'Expo + React Native' },
  { id: 'api',    label: 'API Backend',    desc: 'REST + Auth' },
];

export default function NavigationPane({ tasks = [], activeJobId, onNewTask, onSelectTask, token }) {
  const [active, setActive] = useState('workspace');
  const [workflows, setWorkflows] = useState({});
  const [wfOpen, setWfOpen] = useState(null);

  useEffect(() => {
    if (active === 'workflows' && token) {
      getWorkflows(token).then(data => setWorkflows(data.workflows || {}));
    }
  }, [active, token]);

  return (
    <div className="flex flex-col h-full bg-zinc-50 border-r border-zinc-200">
      {/* Brand */}
      <div className="px-4 py-3 border-b border-zinc-200">
        <div className="font-bold text-zinc-900 text-sm tracking-tight">CRUCIBLE</div>
        <div className="text-[10px] text-zinc-400">Inevitable AI</div>
      </div>

      {/* New task */}
      <div className="p-3">
        <button onClick={() => onNewTask?.()}
          className="w-full flex items-center gap-2 px-3 py-2 bg-emerald-600 hover:bg-emerald-700
            text-white rounded-lg text-xs font-medium transition">
          <Plus size={13} /> New Project
        </button>
      </div>

      {/* Nav */}
      <div className="px-2 space-y-0.5">
        {NAV.map(n => (
          <button key={n.id} onClick={() => setActive(n.id)}
            className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition
              ${active === n.id ? 'bg-emerald-50 text-emerald-700 font-medium' : 'text-zinc-600 hover:bg-zinc-200'}`}>
            <n.icon size={13} /> {n.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-2 pt-2">
        {active === 'workspace' && (
          <div className="space-y-1">
            <p className="text-[10px] font-semibold text-zinc-400 uppercase px-2 mb-1">Recent</p>
            {tasks.length === 0 && (
              <p className="text-xs text-zinc-400 px-2 py-4 text-center">No builds yet</p>
            )}
            {tasks.map(t => (
              <button key={t.id} onClick={() => onSelectTask?.(t)}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs transition
                  ${activeJobId === t.id ? 'bg-emerald-50 text-emerald-800' : 'hover:bg-zinc-200 text-zinc-700'}`}>
                <div className="font-medium truncate">{t.goal?.slice(0, 40) || 'Untitled'}</div>
                <div className="text-zinc-400 text-[10px] flex items-center gap-1 mt-0.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    t.status === 'completed' ? 'bg-emerald-500' :
                    t.status === 'running' ? 'bg-blue-500 animate-pulse' :
                    t.status === 'failed' ? 'bg-red-500' : 'bg-zinc-400'}`} />
                  {t.status}
                </div>
              </button>
            ))}
          </div>
        )}

        {active === 'workflows' && (
          <div className="space-y-1">
            <p className="text-[10px] font-semibold text-zinc-400 uppercase px-2 mb-1">37 Workflows</p>
            {Object.entries(workflows).map(([category, wfs]) => (
              <div key={category}>
                <button onClick={() => setWfOpen(wfOpen === category ? null : category)}
                  className="w-full flex items-center justify-between px-2 py-1 text-[10px] font-semibold
                    text-zinc-500 uppercase hover:text-zinc-700">
                  {category}
                  <ChevronRight size={10} className={`transition ${wfOpen === category ? 'rotate-90' : ''}`} />
                </button>
                {wfOpen === category && Object.keys(wfs).map(key => (
                  <button key={key}
                    className="w-full text-left px-4 py-1.5 text-xs text-zinc-600 hover:bg-zinc-200 rounded">
                    {wfs[key]?.name || key}
                  </button>
                ))}
              </div>
            ))}
          </div>
        )}

        {active === 'templates' && (
          <div className="space-y-2 p-1">
            {TEMPLATES.map(t => (
              <button key={t.id} onClick={() => onNewTask?.(t.label)}
                className="w-full text-left px-3 py-2 border border-zinc-200 rounded-lg
                  hover:border-emerald-300 hover:bg-emerald-50/50 transition">
                <div className="text-xs font-medium text-zinc-800">{t.label}</div>
                <div className="text-[10px] text-zinc-500">{t.desc}</div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
