import React, { useState, useEffect } from 'react';
import { Check, X, Shield, AlertTriangle, ChevronRight } from 'lucide-react';
import { permissionEngine } from '../lib/permissionEngine';

const RISK = {
  'exec': 0.85, 'delete': 0.8, 'deploy': 0.75, 'write': 0.5,
  'read': 0.2, 'search': 0.15, 'lint': 0.1,
};

function getRisk(toolName) {
  const lower = (toolName || '').toLowerCase();
  for (const [k, v] of Object.entries(RISK)) {
    if (lower.includes(k)) return v;
  }
  return 0.3;
}

export default function ToolCarousel({ tools = [], onApprove, onDeny, onApproveAll }) {
  const [statuses, setStatuses] = useState({});

  useEffect(() => {
    if (!tools.length) return;
    Promise.all(tools.map(async t => {
      const risk = getRisk(t.name);
      const check = await permissionEngine.check(t.name, risk);
      return [t.id || t.name, { ...check, risk }];
    })).then(entries => setStatuses(Object.fromEntries(entries)));
  }, [tools]);

  if (!tools.length) return null;

  return (
    <div className="border border-zinc-200 rounded-xl bg-white shadow-sm p-3 my-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-zinc-700">Tools requested</span>
        <div className="flex gap-2">
          <button onClick={() => onApproveAll?.()}
            className="text-xs px-2 py-1 bg-emerald-600 text-white rounded hover:bg-emerald-700">
            Allow all
          </button>
          <button onClick={() => onDeny?.()}
            className="text-xs px-2 py-1 bg-zinc-200 text-zinc-700 rounded hover:bg-zinc-300">
            Deny all
          </button>
        </div>
      </div>
      <div className="space-y-1.5">
        {tools.map(t => {
          const s = statuses[t.id || t.name];
          const tier = s?.trustTier || 'untrusted';
          const isBlocked = s?.mode === 'block';
          const reason = s?.reason || 'Permission status pending';
          return (
            <div key={t.id || t.name}
              title={reason}
              className={`flex items-center gap-2 px-2 py-1.5 rounded-lg border ${
                isBlocked ? 'bg-red-50 border-red-100' : 'bg-zinc-50 border-zinc-100'
              }`}>
              <span className={`w-2 h-2 rounded-full ${
                tier === 'safe' ? 'bg-emerald-500' :
                tier === 'verified' ? 'bg-blue-400' :
                tier === 'dangerous' ? 'bg-red-500' : 'bg-amber-400'
              }`} />
              <span className="text-xs font-medium text-zinc-800 flex-1">{t.name}</span>
              {t.description && (
                <span className="text-[10px] text-zinc-500 truncate max-w-[200px]">{t.description}</span>
              )}
              {isBlocked ? (
                <span className="text-[10px] text-red-500 flex items-center gap-1">
                  <AlertTriangle size={10} /> Blocked
                </span>
              ) : s?.autoApproved ? (
                <span className="text-[10px] text-emerald-600 flex items-center gap-1">
                  <Shield size={10} /> Auto-approved
                </span>
              ) : (
                <div className="flex gap-1">
                  <button onClick={() => {
                    permissionEngine.record(t.name, 'allow', getRisk(t.name));
                    onApprove?.(t);
                  }} className="p-1 rounded hover:bg-emerald-100 text-emerald-600" disabled={isBlocked}>
                    <Check size={12} />
                  </button>
                  <button onClick={() => {
                    permissionEngine.record(t.name, 'deny', getRisk(t.name));
                    onDeny?.(t);
                  }} className="p-1 rounded hover:bg-red-100 text-red-500" disabled={isBlocked}>
                    <X size={12} />
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
