/**
 * User-submitted prompts shown as bubbles above the composer (Unified workspace only).
 */
import React from 'react';
import './WorkspaceUserChat.css';

function shortJobRef(id) {
  if (!id || typeof id !== 'string') return '';
  if (id.length <= 14) return id;
  return `${id.slice(0, 8)}…${id.slice(-4)}`;
}

function shortProjectRef(id) {
  if (!id || typeof id !== 'string') return '';
  if (id.length <= 12) return id;
  return `${id.slice(0, 6)}…${id.slice(-4)}`;
}

export default function WorkspaceUserChat({ messages = [], projectId = null }) {
  if (!messages.length) return null;
  return (
    <section className="uw-user-chat" aria-label="Your messages">
      {messages.map((m) => {
        const isAssistant = m.role === 'assistant';
        return (
          <div key={m.id} className={`uw-chat-row${isAssistant ? ' uw-chat-row--assistant' : ''}`}>
            <div className="uw-chat-turn-label" aria-hidden>
              {isAssistant ? 'Build' : 'You'}
            </div>
            <div className={`uw-chat-bubble${isAssistant ? ' uw-chat-bubble--assistant' : ''}`}>{m.body}</div>
            {!isAssistant && (m.jobId || projectId) ? (
              <div className="uw-chat-meta">
                {m.jobId ? <span>Job {shortJobRef(m.jobId)}</span> : null}
                {m.jobId && projectId ? <span className="uw-chat-meta-sep">·</span> : null}
                {projectId ? <span>Project {shortProjectRef(projectId)}</span> : null}
              </div>
            ) : null}
          </div>
        );
      })}
    </section>
  );
}
