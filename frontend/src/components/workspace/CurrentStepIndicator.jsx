import React from 'react';

/**
 * CurrentStepIndicator: Manus-style blue dot + step name + elapsed time + position.
 * Shows what's currently running.
 */
export default function CurrentStepIndicator({ currentStep }) {
  if (!currentStep) return null;

  const { name, elapsed, position, status } = currentStep;

  const statusColor = status === 'thinking' ? 'bg-blue-500' : 'bg-blue-500';
  const isThinking = status === 'thinking';

  return (
    <div className="border border-blue-200 bg-blue-50 rounded-lg p-3 my-4">
      <div className="flex items-center gap-3">
        {/* Blue dot */}
        <div className={`w-3 h-3 rounded-full ${statusColor} ${isThinking ? 'animate-pulse' : ''} flex-shrink-0`} />

        {/* Step name */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-blue-900 truncate">{name}</p>
          {isThinking && <p className="text-xs text-blue-700 mt-0.5">Thinking</p>}
        </div>

        {/* Time and position */}
        <div className="text-right flex-shrink-0">
          <div className="text-xs text-blue-700 font-medium">{position}</div>
          <div className="text-xs text-blue-600">{elapsed}</div>
        </div>
      </div>
    </div>
  );
}
