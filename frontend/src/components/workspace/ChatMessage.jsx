import { useState } from 'react';
import { formatMsgContent } from './formatMsgContent';
import ActionChip from './ActionChip';
import TaskProgressCard from './TaskProgressCard';
import CurrentStepIndicator from './CurrentStepIndicator';

export default function ChatMessage({ msg }) {
  const [expanded, setExpanded] = useState(false);
  const content = formatMsgContent(msg.content);
  const isLong = content.length > 300 || (content.match(/\n/g) || []).length > 4;
  const showContent = expanded || !isLong ? content : `${content.slice(0, 300)}${content.length > 300 ? '...' : ''}`;

  const role = msg.role || 'user';
  const isAssistant = role === 'assistant';

  return (
    <div className={`flex w-full mb-4 ${isAssistant ? 'justify-start' : 'justify-end'}`}>
      <div className={`max-w-2xl w-full ${isAssistant ? '' : ''}`}>
        {/* Main message bubble */}
        <div
          className={`rounded-xl px-4 py-3 text-sm ${
            isAssistant
              ? 'bg-white border border-gray-200 text-gray-800'
              : 'bg-gray-100 text-gray-900'
          }`}
        >
          <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">{showContent}</pre>
          {isLong && (
            <button
              type="button"
              onClick={() => setExpanded((e) => !e)}
              className="mt-2 text-xs font-medium text-gray-600 hover:text-gray-900 underline"
            >
              {expanded ? 'Show less' : 'Show more'}
            </button>
          )}
        </div>

        {/* Action chips (below message if assistant) */}
        {isAssistant && msg.action_chips && msg.action_chips.length > 0 && (
          <div className="mt-3 space-y-2 pl-2">
            {msg.action_chips.map((chip, idx) => (
              <ActionChip
                key={idx}
                action={chip.action}
                status={chip.status}
                icon={chip.icon}
              />
            ))}
          </div>
        )}

        {/* Task progress card (embedded in chat) */}
        {isAssistant && msg.task_cards && (
          <TaskProgressCard taskCards={msg.task_cards} />
        )}

        {/* Current step indicator */}
        {isAssistant && msg.current_step && (
          <CurrentStepIndicator currentStep={msg.current_step} />
        )}
      </div>
    </div>
  );
}
