import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send, Code, Eye, Settings, Download, Share2, Menu,
  X, ChevronDown, Copy, Check, Play, Terminal, Maximize2,
  MessageSquare, FileText, Database, Zap, Bot
} from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';
import Layout3Column from '../components/Layout3Column';
import Sidebar from '../components/Sidebar';
import RightPanel from '../components/RightPanel';
import './WorkspaceRedesigned.css';

/**
 * Redesigned Workspace Component
 * 
 * Features:
 * - Chat-first interface (primary)
 * - Code viewer (optional, hidden by default)
 * - Live preview (right panel)
 * - Agent selection and execution
 * - Message history
 * - Responsive design
 * - High-quality aesthetic
 */

const WorkspaceRedesigned = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { user, token } = useAuth();
  
  // State
  const [project, setProject] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [showCode, setShowCode] = useState(false);
  const [showPreview, setShowPreview] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [agents, setAgents] = useState([]);
  const [generatedCode, setGeneratedCode] = useState('');
  const [preview, setPreview] = useState('');
  const messagesEndRef = useRef(null);

  // Fetch project and agents
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [projectRes, agentsRes] = await Promise.all([
          axios.get(`${API}/projects/${projectId}`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/agents`, { headers: { Authorization: `Bearer ${token}` } }),
        ]);
        setProject(projectRes.data);
        setAgents(agentsRes.data.agents || []);
        setMessages([
          {
            id: 1,
            type: 'system',
            content: `Welcome to ${projectRes.data.name}! I'm your AI assistant. Tell me what you want to build.`,
            timestamp: new Date(),
          },
        ]);
      } catch (err) {
        console.error('Failed to fetch data:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [projectId, token]);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle send message
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || sending) return;

    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      content: inputValue,
      timestamp: new Date(),
      agent: selectedAgent?.name,
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setSending(true);

    try {
      // Simulate AI response
      await new Promise(resolve => setTimeout(resolve, 1000));

      const aiMessage = {
        id: messages.length + 2,
        type: 'assistant',
        content: `I'll help you build that. Let me use the ${selectedAgent?.name || 'default'} agent to generate the code.`,
        timestamp: new Date(),
        agent: selectedAgent?.name,
      };

      setMessages(prev => [...prev, aiMessage]);

      // Simulate code generation
      const code = `// Generated code from ${selectedAgent?.name || 'AI'}
import React from 'react';

export default function App() {
  return (
    <div className="app">
      <h1>Your AI-Generated Component</h1>
      <p>Built with CrucibAI</p>
    </div>
  );
}`;

      setGeneratedCode(code);
      setPreview(`<div style="padding: 20px; text-align: center;">
        <h1>Your AI-Generated Component</h1>
        <p>Built with CrucibAI</p>
      </div>`);
    } catch (err) {
      console.error('Failed to send message:', err);
      const errorMessage = {
        id: messages.length + 2,
        type: 'error',
        content: 'Sorry, something went wrong. Please try again.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setSending(false);
    }
  };

  // Sidebar content
  const sidebarContent = (
    <Sidebar
      user={user}
      onLogout={() => {
        localStorage.removeItem('token');
        navigate('/login');
      }}
      projects={[project]}
      tasks={[]}
    />
  );

  // Main content
  const mainContent = (
    <div className="workspace-main">
      {/* Header */}
      <div className="workspace-header">
        <div className="workspace-title">
          <h1>{project?.name || 'Workspace'}</h1>
          <p className="workspace-subtitle">{project?.description || 'Build with AI'}</p>
        </div>
        <div className="workspace-actions">
          <button
            className={`workspace-btn ${showCode ? 'active' : ''}`}
            onClick={() => setShowCode(!showCode)}
            title="Toggle Code"
          >
            <Code size={18} />
            <span>Code</span>
          </button>
          <button
            className={`workspace-btn ${showPreview ? 'active' : ''}`}
            onClick={() => setShowPreview(!showPreview)}
            title="Toggle Preview"
          >
            <Eye size={18} />
            <span>Preview</span>
          </button>
          <button className="workspace-btn" title="Settings">
            <Settings size={18} />
          </button>
        </div>
      </div>

      {/* Agent Selector */}
      <div className="agent-selector">
        <label>Select Agent:</label>
        <select
          value={selectedAgent?.id || ''}
          onChange={(e) => {
            const agent = agents.find(a => a.id === e.target.value);
            setSelectedAgent(agent);
          }}
          className="agent-select"
        >
          <option value="">Choose an agent...</option>
          {agents.map(agent => (
            <option key={agent.id} value={agent.id}>
              {agent.name}
            </option>
          ))}
        </select>
      </div>

      {/* Chat Area */}
      <div className="chat-container">
        <div className="messages-list">
          <AnimatePresence>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                className={`message message-${msg.type}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
              >
                <div className="message-content">
                  {msg.agent && (
                    <span className="message-agent">
                      <Bot size={12} />
                      {msg.agent}
                    </span>
                  )}
                  <p>{msg.content}</p>
                </div>
                <span className="message-time">
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </motion.div>
            ))}
          </AnimatePresence>
          {sending && (
            <div className="message message-assistant">
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

        {/* Input Area */}
        <form className="chat-input-area" onSubmit={handleSendMessage}>
          <div className="input-wrapper">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Describe what you want to build..."
              className="chat-input"
              disabled={sending}
            />
            <button
              type="submit"
              className="send-btn"
              disabled={!inputValue.trim() || sending}
              title="Send message"
            >
              <Send size={18} />
            </button>
          </div>
          <p className="input-hint">
            💡 Tip: Be specific about what you want. The AI will generate code and show you a preview.
          </p>
        </form>
      </div>
    </div>
  );

  // Right panel content
  const rightPanelContent = (
    <RightPanel
      preview={
        showPreview ? (
          <div className="preview-area">
            <div className="preview-header">
              <h3>Preview</h3>
              <button className="preview-fullscreen" title="Fullscreen">
                <Maximize2 size={16} />
              </button>
            </div>
            <div
              className="preview-content"
              dangerouslySetInnerHTML={{ __html: preview || '<p>Your preview will appear here</p>' }}
            />
          </div>
        ) : null
      }
      code={
        showCode ? (
          <div className="code-area">
            <div className="code-header">
              <h3>Generated Code</h3>
              <button
                className="code-copy-btn"
                onClick={() => {
                  navigator.clipboard.writeText(generatedCode);
                }}
                title="Copy code"
              >
                <Copy size={16} />
              </button>
            </div>
            <pre className="code-content">
              <code>{generatedCode || '// Your generated code will appear here'}</code>
            </pre>
          </div>
        ) : null
      }
      onShare={() => console.log('Share')}
      onDownload={() => console.log('Download')}
      onClose={() => console.log('Close')}
    />
  );

  if (loading) {
    return (
      <div className="workspace-loading">
        <div className="loading-spinner"></div>
        <p>Loading workspace...</p>
      </div>
    );
  }

  return (
    <>
      <Layout3Column
        sidebar={sidebarContent}
        main={mainContent}
        rightPanel={rightPanelContent}
      />
    </>
  );
};

export default WorkspaceRedesigned;
