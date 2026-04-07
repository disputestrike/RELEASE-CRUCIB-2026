import { useState } from 'react';
import { formatMsgContent } from './formatMsgContent';

export default function ChatMessage({ msg }) {
  const [expanded, setExpanded] = useState(false);
  const content = formatMsgContent(msg.content);
  const isLong = content.length > 300 || (content.match(/\n/g) || []).length > 4;
  const showContent = expanded || !isLong ? content : `${content.slice(0, 300)}${content.length > 300 ? '...' : ''}`;
  return (
    <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[80%] rounded-xl px-4 py-3 text-sm ${
        msg.role === 'user'
          ? 'bg-gray-100 text-gray-900'
          : 'bg-white border border-gray-200 text-gray-800'
      }`}
      >
        <pre className="whitespace-pre-wrap font-sans">{showContent}</pre>
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
    </div>
  );
}
