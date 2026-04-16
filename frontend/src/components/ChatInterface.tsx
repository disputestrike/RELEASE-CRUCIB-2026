import React, { useState, useRef, useEffect, useCallback } from 'react';
import './ChatInterface.css';
import { contextManager } from '../lib/contextManager';

interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system' | 'suggestion';
  content: string;
  timestamp: Date;
  metadata?: Record<string, any>;
  suggestions?: string[];
}

interface ChatSession {
  sessionId: string;
  messages: Message[];
  isLoading: boolean;
  error?: string;
}

export const ChatInterface: React.FC<{ sessionId?: string }> = ({ sessionId: initialSessionId }) => {
  const [session, setSession] = useState<ChatSession>({
    sessionId: initialSessionId || generateSessionId(),
    messages: [],
    isLoading: false,
  });

  const [inputValue, setInputValue] = useState('');
  const [ws, setWs] = useState<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [session.messages, scrollToBottom]);

  // Initialize WebSocket connection
  useEffect(() => {
    if (!session.sessionId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/chat/ws/${session.sessionId}`;

    try {
      const websocket = new WebSocket(wsUrl);

      websocket.onopen = () => {
        console.log('WebSocket connected');
        addSystemMessage('Connected to CrucibAI Copilot');
      };

      websocket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          handleStreamMessage(message);
        } catch (e) {
          console.error('Error parsing message:', e);
        }
      };

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setSession((prev) => ({ ...prev, error: 'Connection error' }));
      };

      websocket.onclose = () => {
        console.log('WebSocket disconnected');
        addSystemMessage('Disconnected from CrucibAI');
      };

      setWs(websocket);

      return () => {
        websocket.close();
      };
    } catch (e) {
      console.error('Error creating WebSocket:', e);
    }
  }, [session.sessionId]);

  const addSystemMessage = (content: string) => {
    setSession((prev) => ({
      ...prev,
      messages: [
        ...prev.messages,
        {
          id: `system_${Date.now()}`,
          type: 'system',
          content,
          timestamp: new Date(),
        },
      ],
    }));
  };

  const handleStreamMessage = (message: any) => {
    const { type, content, metadata } = message;

    setSession((prev) => {
      let newMessages = [...prev.messages];

      // Check if we need to append to last assistant message or create new one
      if (type === 'agent_progress' || type === 'tool_result' || type === 'reasoning') {
        const lastMessage = newMessages[newMessages.length - 1];
        if (lastMessage?.type === 'assistant') {
          lastMessage.content += '\n' + content;
          contextManager.addTurn('assistant', content || '');
        } else {
          newMessages.push({
            id: `msg_${Date.now()}_${Math.random()}`,
            type: 'assistant',
            content,
            timestamp: new Date(),
            metadata,
          });
          contextManager.addTurn('assistant', content || '');
        }
      } else if (type === 'agent_complete') {
        setSession((s) => ({ ...s, isLoading: false }));
        newMessages.push({
          id: `msg_${Date.now()}`,
          type: 'system',
          content: '✓ Completed',
          timestamp: new Date(),
          metadata,
        });
      } else if (type === 'error') {
        newMessages.push({
          id: `msg_${Date.now()}`,
          type: 'system',
          content: `⚠️ Error: ${content}`,
          timestamp: new Date(),
          metadata,
        });
        setSession((s) => ({ ...s, isLoading: false }));
      } else if (type === 'suggestion') {
        newMessages.push({
          id: `msg_${Date.now()}`,
          type: 'suggestion',
          content,
          timestamp: new Date(),
          metadata,
        });
      } else if (type === 'clarification_needed') {
        newMessages.push({
          id: `msg_${Date.now()}`,
          type: 'assistant',
          content,
          timestamp: new Date(),
          metadata,
          suggestions: metadata?.questions || [],
        });
      }

      return { ...prev, messages: newMessages };
    });
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || session.isLoading) return;

    const userMessage: Message = {
      id: `user_${Date.now()}`,
      type: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setSession((prev) => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isLoading: true,
    }));
    contextManager.addTurn('user', inputValue);

    setInputValue('');

    try {
      const response = await fetch('/api/chat/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: session.sessionId,
          message: inputValue,
          context: {
            optimized_turns: contextManager.getOptimized(),
          },
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setSession((prev) => ({
        ...prev,
        isLoading: false,
        error: 'Failed to send message',
      }));
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
    inputRef.current?.focus();
  };

  const expandTextarea = () => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 200) + 'px';
    }
  };

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <h1>🧠 CrucibAI Copilot</h1>
        <span className="session-id">Session: {session.sessionId.substring(0, 8)}</span>
      </div>

      <div className="chat-messages">
        {session.messages.length === 0 && (
          <div className="welcome-message">
            <h2>Welcome to CrucibAI Copilot</h2>
            <p>I can help you with:</p>
            <ul>
              <li>📝 Analyze and review code</li>
              <li>🔍 Search and explore your workspace</li>
              <li>🧪 Run tests and debugging</li>
              <li>🚀 Build and deploy projects</li>
              <li>💡 Generate code and suggestions</li>
            </ul>
            <p>Start by asking me anything!</p>
          </div>
        )}

        {session.messages.map((message) => (
          <div key={message.id} className={`message message-${message.type}`}>
            <div className="message-avatar">
              {message.type === 'user' && <span>👤</span>}
              {message.type === 'assistant' && <span>🤖</span>}
              {message.type === 'system' && <span>ℹ️</span>}
              {message.type === 'suggestion' && <span>💡</span>}
            </div>
            <div className="message-content">
              <p>{message.content}</p>

              {message.suggestions && message.suggestions.length > 0 && (
                <div className="suggestions">
                  {message.suggestions.map((suggestion, idx) => (
                    <button
                      key={idx}
                      className="suggestion-btn"
                      onClick={() => handleSuggestionClick(suggestion)}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}

              {message.metadata && Object.keys(message.metadata).length > 0 && (
                <details className="message-metadata">
                  <summary>Details</summary>
                  <pre>{JSON.stringify(message.metadata, null, 2)}</pre>
                </details>
              )}
            </div>
            <span className="message-time">
              {message.timestamp.toLocaleTimeString()}
            </span>
          </div>
        ))}

        {session.isLoading && (
          <div className="message message-system">
            <div className="message-avatar">🤖</div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {session.error && (
        <div className="error-alert">
          {session.error}
          <button onClick={() => setSession((prev) => ({ ...prev, error: undefined }))}>×</button>
        </div>
      )}

      <div className="chat-input-area">
        <form onSubmit={handleSendMessage}>
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              expandTextarea();
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && e.ctrlKey) {
                handleSendMessage(e);
              }
            }}
            placeholder="Ask me anything... (Ctrl+Enter to send)"
            disabled={session.isLoading}
            rows={1}
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || session.isLoading}
            className="send-button"
          >
            {session.isLoading ? '⏳' : '📤 Send'}
          </button>
        </form>
      </div>
    </div>
  );
};

function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}
