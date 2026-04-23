import { useRef, useEffect } from 'react';

export default function ConsolePanel({ logs, placeholder = 'Terminal output will appear here. Run a build to see logs.' }) {
  const consoleRef = useRef(null);

  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div ref={consoleRef} className="workspace-console-panel h-full overflow-auto font-mono text-xs p-3 space-y-1">
      {logs.length === 0 ? (
        <div className="workspace-console-placeholder">{placeholder}</div>
      ) : (
        logs.map((log, i) => (
          <div
            key={i}
            className={`workspace-console-line flex items-start gap-2 workspace-console-line--${log.type || 'info'}`}
          >
            <span className="workspace-console-time">[{log.time}]</span>
            <span className="workspace-console-agent">{log.agent || 'system'}:</span>
            <span className="flex-1 workspace-console-message">{log.message}</span>
          </div>
        ))
      )}
    </div>
  );
}
