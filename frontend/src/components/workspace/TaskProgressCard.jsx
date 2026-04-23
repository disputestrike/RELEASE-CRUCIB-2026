import React from 'react';
import { Clock } from 'lucide-react';

/**
 * TaskProgressCard: Manus-style task progress display.
 * Shows "1/11" with all tasks and their status.
 */
export default function TaskProgressCard({ taskCards }) {
  if (!taskCards || !taskCards.tasks || taskCards.tasks.length === 0) {
    return null;
  }

  const { total, current, tasks } = taskCards;

  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-white my-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900">Task progress</h3>
        <span className="text-sm font-medium text-gray-600">{current} / {total}</span>
      </div>

      <div className="space-y-2">
        {tasks.map((task, idx) => {
          const isActive = idx === current - 1;
          const isCompleted = task.status === 'completed';

          const statusIcon = isCompleted ? (
            <span className="text-green-600">✓</span>
          ) : isActive ? (
            <div className="inline-block">
              <Clock className="w-4 h-4 text-blue-600 animate-spin" />
            </div>
          ) : (
            <span className="text-gray-400">◯</span>
          );

          return (
            <div
              key={idx}
              className={`flex items-center gap-2 text-sm px-2 py-1 rounded ${
                isActive ? 'bg-blue-50' : ''
              }`}
            >
              {statusIcon}
              <span
                className={`truncate ${
                  isCompleted
                    ? 'text-green-700 line-through'
                    : isActive
                    ? 'text-blue-900 font-medium'
                    : 'text-gray-600'
                }`}
              >
                {task.description}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
