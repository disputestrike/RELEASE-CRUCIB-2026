import React from 'react';

/**
 * ActionChip: Manus-style small gray box showing an action with status.
 * Used to show what tasks are running/queued.
 */
export default function ActionChip({ action, status, icon = 'file' }) {
  const statusStyles = {
    running: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      dot: 'bg-blue-500',
      text: 'text-blue-900',
    },
    completed: {
      bg: 'bg-green-50',
      border: 'border-green-200',
      dot: 'bg-green-500',
      text: 'text-green-900',
    },
    pending: {
      bg: 'bg-gray-50',
      border: 'border-gray-200',
      dot: 'bg-gray-400',
      text: 'text-gray-900',
    },
    failed: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      dot: 'bg-red-500',
      text: 'text-red-900',
    },
  };

  const style = statusStyles[status] || statusStyles.pending;

  const iconEl = status === 'completed' ? (
    <div className="w-4 h-4 flex items-center justify-center text-green-600">✓</div>
  ) : status === 'running' ? (
    <div className="w-4 h-4 flex items-center justify-center">
      <div className={`w-2 h-2 rounded-full ${style.dot} animate-pulse`} />
    </div>
  ) : (
    <div className={`w-2 h-2 rounded-full ${style.dot}`} />
  );

  return (
    <div className={`${style.bg} border ${style.border} rounded-lg px-3 py-2 flex items-center gap-2 text-sm ${style.text}`}>
      {iconEl}
      <span className="truncate">{action}</span>
    </div>
  );
}
