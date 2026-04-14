import React, { useState } from 'react';

/**
 * EXACT MANUS UI REPLICATION
 * 
 * Manus shows:
 * 1. Plain text message from AI
 * 2. Below: "Task progress X/Y" section with collapsible list
 * 3. Each task has a ⏱️ clock icon
 * 4. Blue dot + "Thinking" indicator for ongoing work
 * 5. NO fancy cards, NO colored chips - just clean, simple text
 */

export default function ChatMessageManus({ msg }) {
  const [expandedSteps, setExpandedSteps] = useState({});
  
  const user = msg.role === 'user';
  
  // User messages - simple right-aligned bubble
  if (user) {
    return (
      <div className="flex w-full justify-end mb-6">
        <div className="max-w-[80%] px-4 py-3 rounded-lg" style={{ backgroundColor: '#f5f5f5', color: '#1a1a1a' }}>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
        </div>
      </div>
    );
  }
  
  // Assistant messages - show text + task list below
  return (
    <div className="flex w-full justify-start mb-6">
      <div className="max-w-[85%]">
        {/* Main message text */}
        {msg.content && (
          <div className="mb-4 text-sm leading-relaxed whitespace-pre-wrap" style={{ color: '#1a1a1a' }}>
            {msg.content}
          </div>
        )}
        
        {/* Task progress section - EXACT Manus layout */}
        {msg.task_cards && (
          <div className="mt-6">
            {/* Header: "Task progress X/Y" */}
            <div className="text-sm font-medium mb-3" style={{ color: '#666' }}>
              Task progress {msg.task_cards.current || 0}/{msg.task_cards.total || 0}
            </div>
            
            {/* Task list */}
            <div className="space-y-2">
              {msg.task_cards.tasks && msg.task_cards.tasks.map((task, idx) => {
                const isExpanded = expandedSteps[idx];
                const taskText = typeof task === 'string' ? task : task.description || task.name || 'Task';
                const hasDetails = task.details || task.description;
                
                return (
                  <div key={idx} className="flex items-start gap-3">
                    {/* Clock icon ⏱️ */}
                    <div className="flex-shrink-0 pt-0.5" style={{ color: '#999' }}>
                      ⏱️
                    </div>
                    
                    {/* Task text - clickable if has details */}
                    <div className="flex-1">
                      <button
                        onClick={() => hasDetails && setExpandedSteps(prev => ({ ...prev, [idx]: !isExpanded }))}
                        className="text-left text-sm hover:underline" 
                        style={{ color: '#1a1a1a', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                      >
                        {taskText}
                      </button>
                      
                      {/* Expanded details */}
                      {isExpanded && hasDetails && (
                        <div className="mt-2 pl-4 text-xs" style={{ color: '#666' }}>
                          {task.details || task.description}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
        
        {/* "Thinking" indicator - blue dot + text */}
        {msg.thinking && (
          <div className="flex items-center gap-2 mt-4" style={{ color: '#2563eb' }}>
            <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: '#2563eb' }}></div>
            <span className="text-xs font-medium">Thinking</span>
          </div>
        )}
      </div>
    </div>
  );
}
