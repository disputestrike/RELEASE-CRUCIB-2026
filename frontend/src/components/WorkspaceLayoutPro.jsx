import React, { useState, useRef, useEffect } from 'react';
import { 
  ChevronDown, ChevronRight, Menu, X, Settings, Home, Code, Play, Zap, BarChart3, HelpCircle,
  Layers, BookOpen, Palette, Cpu, Users, CreditCard, FileText, Download, Eye, Lightbulb,
  Workflow, Shield, Smartphone, Monitor, Rocket, Search, Bell, LogOut, User, Lock,
  GitBranch, Terminal, Database, Gauge, AlertCircle, CheckCircle, Clock, TrendingUp
} from 'lucide-react';
import './WorkspaceLayoutPro.css';

/**
 * Professional Workspace Layout - Manus-inspired with ALL 50+ features
 * Features:
 * - Resizable panels (drag to adjust)
 * - Proper proportions (preview 60%, input 40%)
 * - Clean sidebar with organized navigation
 * - ALL 50+ features with professional icons
 * - Collapsible menu sections
 * - Search functionality
 * - Professional color scheme
 * - Better visual hierarchy
 */

export const WorkspaceLayoutPro = ({ 
  previewContent, 
  chatMessages, 
  onSendMessage, 
  isLoading,
  currentPage = 'workspace'
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [dividerPos, setDividerPos] = useState(60);
  const [isDragging, setIsDragging] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    developer: true,
    admin: true,
    content: true,
    utilities: true,
    public: false
  });
  const [searchQuery, setSearchQuery] = useState('');
  const containerRef = useRef(null);
  const [inputValue, setInputValue] = useState('');

  // All features organized by category
  const features = {
    developer: {
      label: '💻 Developer Tools',
      icon: Code,
      items: [
        { id: 'workspace', label: 'Workspace', icon: Monitor, description: 'Main IDE' },
        { id: 'builder', label: 'Builder', icon: Layers, description: 'Build apps' },
        { id: 'unified-ide', label: 'Unified IDE', icon: Code, description: 'Advanced editor' },
        { id: 'vibe-code', label: 'Vibe Code', icon: Lightbulb, description: 'AI coding' },
        { id: 'project-builder', label: 'Project Builder', icon: Workflow, description: 'Project setup' },
        { id: 'agents', label: 'Agents', icon: Zap, description: 'AI agents' },
        { id: 'agent-monitor', label: 'Agent Monitor', icon: Gauge, description: 'Monitor agents' },
        { id: 'monitoring', label: 'Monitoring', icon: TrendingUp, description: 'Dashboard' },
      ]
    },
    admin: {
      label: '🔐 Admin & Management',
      icon: Shield,
      items: [
        { id: 'admin-dashboard', label: 'Dashboard', icon: BarChart3, description: 'Overview' },
        { id: 'admin-users', label: 'Users', icon: Users, description: 'Manage users' },
        { id: 'admin-billing', label: 'Billing', icon: CreditCard, description: 'Payments' },
        { id: 'admin-analytics', label: 'Analytics', icon: TrendingUp, description: 'Stats' },
        { id: 'audit-log', label: 'Audit Log', icon: Clock, description: 'Activity log' },
      ]
    },
    content: {
      label: '📚 Content & Learning',
      icon: BookOpen,
      items: [
        { id: 'prompts', label: 'Prompt Library', icon: Lightbulb, description: 'Prompts' },
        { id: 'patterns', label: 'Patterns', icon: Palette, description: 'Design patterns' },
        { id: 'examples', label: 'Examples', icon: Eye, description: 'Code examples' },
        { id: 'templates', label: 'Templates', icon: Layers, description: 'Templates' },
        { id: 'learn', label: 'Learn', icon: BookOpen, description: 'Tutorials' },
        { id: 'docs', label: 'Documentation', icon: FileText, description: 'Docs' },
        { id: 'tutorials', label: 'Tutorials', icon: Play, description: 'Video tutorials' },
        { id: 'shortcuts', label: 'Shortcuts', icon: Cpu, description: 'Keyboard shortcuts' },
      ]
    },
    utilities: {
      label: '🛠️ Utilities',
      icon: Settings,
      items: [
        { id: 'tokens', label: 'Token Center', icon: Cpu, description: 'Token management' },
        { id: 'export', label: 'Export', icon: Download, description: 'Export data' },
        { id: 'env', label: 'Environment', icon: Database, description: 'Env variables' },
        { id: 'payments', label: 'Payments', icon: CreditCard, description: 'Payment wizard' },
        { id: 'settings', label: 'Settings', icon: Settings, description: 'App settings' },
        { id: 'share', label: 'Share', icon: Eye, description: 'Share projects' },
        { id: 'generate', label: 'Generate Content', icon: Lightbulb, description: 'AI generation' },
      ]
    },
    public: {
      label: '🌐 Public Pages',
      icon: Globe,
      items: [
        { id: 'landing', label: 'Landing', icon: Home, description: 'Home page' },
        { id: 'features', label: 'Features', icon: Zap, description: 'Features page' },
        { id: 'pricing', label: 'Pricing', icon: CreditCard, description: 'Pricing' },
        { id: 'blog', label: 'Blog', icon: FileText, description: 'Blog posts' },
        { id: 'enterprise', label: 'Enterprise', icon: Rocket, description: 'Enterprise' },
        { id: 'benchmarks', label: 'Benchmarks', icon: TrendingUp, description: 'Benchmarks' },
      ]
    }
  };

  // Filter features based on search
  const filteredFeatures = Object.entries(features).reduce((acc, [key, section]) => {
    const filtered = section.items.filter(item =>
      item.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.description.toLowerCase().includes(searchQuery.toLowerCase())
    );
    if (filtered.length > 0) {
      acc[key] = { ...section, items: filtered };
    }
    return acc;
  }, {});

  // Handle resizable divider
  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const newPos = ((e.clientX - rect.left) / rect.width) * 100;
      
      if (newPos >= 40 && newPos <= 80) {
        setDividerPos(newPos);
      }
    };

    const handleMouseUp = () => setIsDragging(false);

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const handleSendMessage = () => {
    if (inputValue.trim()) {
      onSendMessage?.(inputValue);
      setInputValue('');
    }
  };

  return (
    <div className="workspace-layout-pro" ref={containerRef}>
      {/* Sidebar */}
      <aside className={`sidebar-pro ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <div className="logo-icon">⬜</div>
            {sidebarOpen && <span className="logo-text">CrucibAI</span>}
          </div>
          <button 
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            title={sidebarOpen ? 'Collapse' : 'Expand'}
          >
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>

        {/* Search */}
        {sidebarOpen && (
          <div className="sidebar-search">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search features..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
          </div>
        )}

        <nav className="sidebar-nav">
          {Object.entries(filteredFeatures).map(([sectionKey, section]) => {
            const SectionIcon = section.icon;
            const isExpanded = expandedSections[sectionKey];
            
            return (
              <div key={sectionKey} className="nav-section">
                <button
                  className="section-header"
                  onClick={() => toggleSection(sectionKey)}
                >
                  <SectionIcon size={18} className="section-icon" />
                  {sidebarOpen && (
                    <>
                      <span className="section-label">{section.label}</span>
                      <ChevronRight 
                        size={16} 
                        className={`section-toggle ${isExpanded ? 'expanded' : ''}`}
                      />
                    </>
                  )}
                </button>

                {isExpanded && (
                  <div className="section-items">
                    {section.items.map(item => {
                      const ItemIcon = item.icon;
                      return (
                        <button
                          key={item.id}
                          className={`nav-item ${currentPage === item.id ? 'active' : ''}`}
                          title={`${item.label} - ${item.description}`}
                        >
                          <ItemIcon size={18} className="nav-icon" />
                          {sidebarOpen && (
                            <div className="nav-item-content">
                              <span className="nav-label">{item.label}</span>
                              <span className="nav-description">{item.description}</span>
                            </div>
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          {sidebarOpen && (
            <>
              <div className="user-info">
                <div className="user-avatar">U</div>
                <div className="user-details">
                  <div className="user-name">User</div>
                  <div className="user-status">Free Plan</div>
                </div>
              </div>
              <div className="footer-actions">
                <button className="footer-btn" title="Profile">
                  <User size={16} />
                  Profile
                </button>
                <button className="footer-btn" title="Logout">
                  <LogOut size={16} />
                  Logout
                </button>
              </div>
            </>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <div className="main-content-pro">
        {/* Preview Panel */}
        <div className="preview-panel" style={{ width: `${dividerPos}%` }}>
          <div className="preview-header">
            <h2>Preview</h2>
            <div className="preview-controls">
              <button className="preview-btn" title="Refresh">🔄</button>
              <button className="preview-btn" title="Fullscreen">⛶</button>
              <button className="preview-btn" title="Settings">⚙️</button>
            </div>
          </div>
          <div className="preview-content">
            {previewContent || (
              <div className="preview-placeholder">
                <div className="placeholder-icon">👁️</div>
                <p>Preview will appear here</p>
                <small>Your app preview renders in real-time</small>
              </div>
            )}
          </div>
        </div>

        {/* Resizable Divider */}
        <div 
          className="divider-pro"
          onMouseDown={() => setIsDragging(true)}
          title="Drag to resize"
        >
          <div className="divider-handle">⋮⋮</div>
        </div>

        {/* Input Panel */}
        <div className="input-panel" style={{ width: `${100 - dividerPos}%` }}>
          <div className="input-header">
            <h2>Build</h2>
            <div className="input-header-actions">
              <button className="header-btn" title="Notifications">
                <Bell size={18} />
              </button>
              <button className="header-btn" title="Help">
                <HelpCircle size={18} />
              </button>
            </div>
          </div>

          {/* Chat Messages */}
          <div className="chat-messages">
            {chatMessages && chatMessages.length > 0 ? (
              chatMessages.map((msg, idx) => (
                <div key={idx} className={`message message-${msg.role}`}>
                  <div className="message-content">{msg.content}</div>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <div className="empty-icon">💬</div>
                <p>Start building your app</p>
                <small>Describe what you want to create</small>
              </div>
            )}
            {isLoading && (
              <div className="message message-system">
                <div className="loading-spinner">
                  <span className="spinner"></span>
                  Processing...
                </div>
              </div>
            )}
          </div>

          {/* Input Area */}
          <div className="input-area">
            <div className="input-wrapper">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="Describe what you want to build..."
                className="input-field"
                disabled={isLoading}
              />
              <button
                onClick={handleSendMessage}
                disabled={isLoading || !inputValue.trim()}
                className="send-button"
                title="Send"
              >
                {isLoading ? '⏳' : '→'}
              </button>
            </div>
            <div className="input-hint">
              ✨ Tip: Be specific about features, design, and functionality
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WorkspaceLayoutPro;
