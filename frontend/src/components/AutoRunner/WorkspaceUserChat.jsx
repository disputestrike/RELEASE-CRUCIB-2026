/**
 * User-submitted prompts and assistant notes — plain strip above the composer.
 * No role labels, no job/project chips (those stay in sidebar / debug surfaces).
 */
import React from 'react';
import './WorkspaceUserChat.css';

export default function WorkspaceUserChat({ messages = [] }) {
  if (!messages.length) return null;
  return (
    <section className="uw-user-chat" aria-label="Conversation">
      {messages.map((m) => {
        const isAssistant = m.role === 'assistant';
        return (
          <div key={m.id} className={`uw-chat-row${isAssistant ? ' uw-chat-row--assistant' : ' uw-chat-row--user'}`}>
            <div className={`uw-chat-bubble${isAssistant ? ' uw-chat-bubble--assistant' : ' uw-chat-bubble--user'}`}>{m.body}</div>
          </div>
        );
      })}
    </section>
  );
}
