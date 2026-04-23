import React from 'react';

export default function InlineDiff({ before = '', after = '', path = '' }) {
  if (!before && !after) return null;
  const beforeLines = before.split('\n');
  const afterLines = after.split('\n');
  const allLines = [];

  const maxLen = Math.max(beforeLines.length, afterLines.length);
  for (let i = 0; i < maxLen; i++) {
    const b = beforeLines[i];
    const a = afterLines[i];
    if (b === a) allLines.push({ type: 'same', text: a || '' });
    else {
      if (b !== undefined) allLines.push({ type: 'removed', text: b });
      if (a !== undefined) allLines.push({ type: 'added', text: a });
    }
  }

  return (
    <div className="rounded-lg border border-zinc-200 overflow-hidden text-[11px] font-mono my-1">
      {path && (
        <div className="px-3 py-1 bg-zinc-100 text-zinc-500 border-b border-zinc-200">{path}</div>
      )}
      <div className="max-h-48 overflow-y-auto">
        {allLines.map((line, i) => (
          <div key={i} className={`px-3 py-0.5 ${
            line.type === 'added' ? 'bg-emerald-50 text-emerald-800' :
            line.type === 'removed' ? 'bg-red-50 text-red-800 line-through opacity-60' :
            'text-zinc-600'
          }`}>
            <span className="select-none mr-2 text-zinc-400">
              {line.type === 'added' ? '+' : line.type === 'removed' ? '−' : ' '}
            </span>
            {line.text}
          </div>
        ))}
      </div>
    </div>
  );
}
