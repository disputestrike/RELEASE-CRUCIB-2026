import React, { useState, useRef } from 'react';
import {
  Menu, X, Settings, Bell, LogOut,
  ChevronRight, Lightbulb, BookOpen, Download, Share2, HelpCircle,
} from 'lucide-react';
import './WorkspaceLayoutSimple.css';

/**
 * Simplified Workspace Layout - For Non-Developers
 * Features:
 * - Large, easy-to-use preview
 * - Simple chat interface
 * - Minimal sidebar with essential features only
 * - Beginner-friendly design
 * - Clear visual feedback
 */

export const WorkspaceLayoutSimple = ({ 
  previewContent, 
  chatMessages, 
  onSendMessage, 
  isLoading,
  currentPage = 'workspace'
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [inputValue, setInputValue] = useState('');
  const containerRef = useRef(null);

  // Simplified features for non-developers
  const quickFeatures = [
    { id: 'templates', label: 'Templates', icon: BookOpen, description: 'Start from template' },
    { id: 'examples', label: 'Examples', icon: Lightbulb, description: 'See examples' },
    { id: 'share', label: 'Share', icon: Share2, description: 'Share your app' },
    { id: 'export', label: 'Export', icon: Download, description: 'Download app' },
    { id: 'help', label: 'Help', icon: HelpCircle, description: 'Get help' },
  ];

  const handleSendMessage = () => {
    if (inputValue.trim()) {
      onSendMessage?.(inputValue);
      setInputValue('');
    }
  };

  return (
    <div className="workspace-layout-simple" ref={containerRef}>
      {/* Header */}
      <header className="header-simple">
        <div className="header-left">
          <button 
            className="menu-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            title={sidebarOpen ? 'Hide menu' : 'Show menu'}
          >
            {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
          <div className="header-logo">
            <div className="logo-icon">⬜</div>
            <span className="logo-text">CrucibAI</span>
          </div>
        </div>

        <div className="header-right">
          <button className="header-icon-btn" title="Notifications">
            <Bell size={20} />
          </button>
          <button className="header-icon-btn" title="Settings">
            <Settings size={20} />
          </button>
          <div className="user-menu">
            <div className="user-avatar-small">U</div>
            <button className="header-icon-btn" title="Logout">
              <LogOut size={20} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="main-content-simple">
        {/* Sidebar */}
        {sidebarOpen && (
          <aside className="sidebar-simple">
            <nav className="nav-simple">
              <div className="nav-section-simple">
                <h3 className="nav-title">Quick Actions</h3>
                <div className="quick-actions">
                  {quickFeatures.map(feature => {
                    const Icon = feature.icon;
                    return (
                      <button
                        key={feature.id}
                        className={`quick-action ${currentPage === feature.id ? 'active' : ''}`}
                        title={feature.description}
                      >
                        <Icon size={24} />
                        <span>{feature.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="nav-section-simple">
                <h3 className="nav-title">Resources</h3>
                <button className="nav-link-simple">
                  <BookOpen size={18} />
                  <span>Documentation</span>
                  <ChevronRight size={16} />
                </button>
                <button className="nav-link-simple">
                  <Lightbulb size={18} />
                  <span>Tips & Tricks</span>
                  <ChevronRight size={16} />
                </button>
                <button className="nav-link-simple">
                  <HelpCircle size={18} />
                  <span>Support</span>
                  <ChevronRight size={16} />
                </button>
              </div>
            </nav>
          </aside>
        )}

        {/* Content Area */}
        <div className="content-area-simple">
          {/* Preview Section */}
          <section className="preview-section-simple">
            <div className="section-header-simple">
              <h2>Your App Preview</h2>
              <div className="preview-actions">
                <button className="action-btn" title="Refresh">
                  🔄
                </button>
                <button className="action-btn" title="Fullscreen">
                  ⛶
                </button>
              </div>
            </div>
            <div className="preview-box-simple">
              {previewContent || (
                <div className="preview-placeholder-simple">
                  <div className="placeholder-icon-large">📱</div>
                  <h3>Your app will appear here</h3>
                  <p>Describe what you want to build in the chat below</p>
                </div>
              )}
            </div>
          </section>

          {/* Chat Section */}
          <section className="chat-section-simple">
            <div className="section-header-simple">
              <h2>Build Your App</h2>
            </div>

            {/* Messages */}
            <div className="chat-box-simple">
              {chatMessages && chatMessages.length > 0 ? (
                chatMessages.map((msg, idx) => (
                  <div key={idx} className={`chat-message-simple message-${msg.role}`}>
                    <div className="message-bubble">{msg.content}</div>
                  </div>
                ))
              ) : (
                <div className="welcome-message">
                  <h3>👋 Welcome to CrucibAI!</h3>
                  <p>Tell me what kind of app you want to build, and I'll create it for you.</p>
                  <div className="suggestion-chips">
                    <button className="chip">Todo App</button>
                    <button className="chip">Weather App</button>
                    <button className="chip">Chat App</button>
                  </div>
                </div>
              )}

              {isLoading && (
                <div className="chat-message-simple message-system">
                  <div className="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              )}
            </div>

            {/* Input */}
            <div className="input-section-simple">
              <div className="input-wrapper-simple">
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Describe your app idea..."
                  className="input-field-simple"
                  disabled={isLoading}
                />
                <button
                  onClick={handleSendMessage}
                  disabled={isLoading || !inputValue.trim()}
                  className="send-btn-simple"
                  title="Send"
                >
                  {isLoading ? '⏳' : '✈️'}
                </button>
              </div>
              <div className="input-helper">
                💡 Example: "Create a todo list app with add, delete, and mark complete features"
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default WorkspaceLayoutSimple;
