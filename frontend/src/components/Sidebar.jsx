import React, { useState, useEffect, useMemo } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Plus, Search, Library, FolderOpen, CheckCircle, Clock,
  AlertCircle, Settings, LogOut, ChevronDown, ChevronRight,
  FileOutput, FileText, LayoutGrid, BookOpen, Key, Keyboard,
  CreditCard, ScrollText, BarChart3, Wrench, HelpCircle, Coins,
  X, Bell, Home
} from 'lucide-react';
import './Sidebar.css';

/**
 * Sidebar Component (Left Navigation) — Redesigned
 * 
 * SPEC: Reduce from 18 items to 4 pinned:
 *   1. Home (→ prompt-first dashboard)
 *   2. New Task (→ /app/workspace)
 *   3. Agents (→ /app/agents)
 *   4. Settings (→ /app/settings)
 * 
 * Below pinned: All Tasks list with status icons
 * Engine Room: collapsed by default, power-user tools
 * Footer: Token balance + user avatar + logout
 */

export const Sidebar = ({ user, onLogout, projects = [], tasks = [] }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [engineRoomOpen, setEngineRoomOpen] = useState(false);
  const [searchFocused, setSearchFocused] = useState(false);

  const isActive = (path) => location.pathname === path;
  const isActivePrefix = (path) => location.pathname.startsWith(path);

  // 4 pinned navigation items — spec requirement
  const pinnedNav = [
    { label: 'Home', icon: Home, href: '/app', exact: true },
    { label: 'New Task', icon: Plus, href: '/app/workspace' },
    { label: 'Agents', icon: FolderOpen, href: '/app/agents' },
    { label: 'Settings', icon: Settings, href: '/app/settings' },
  ];

  // Engine Room — collapsed by default, for power users
  const engineRoomItems = [
    { label: 'Credit Center', icon: Coins, href: '/app/tokens' },
    { label: 'Exports', icon: FileOutput, href: '/app/exports' },
    { label: 'Docs / Slides / Sheets', icon: FileText, href: '/app/generate' },
    { label: 'Patterns', icon: Library, href: '/app/patterns' },
    { label: 'Templates', icon: LayoutGrid, href: '/app/templates' },
    { label: 'Prompt Library', icon: BookOpen, href: '/app/prompts' },
    { label: 'Learn', icon: HelpCircle, href: '/app/learn' },
    { label: 'Env', icon: Key, href: '/app/env' },
    { label: 'Shortcuts', icon: Keyboard, href: '/app/shortcuts' },
    { label: 'Benchmarks', icon: BarChart3, href: '/benchmarks' },
    { label: 'Add Payments', icon: CreditCard, href: '/app/payments-wizard' },
    { label: 'Audit Log', icon: ScrollText, href: '/app/audit-log' },
  ];

  // Filter tasks by search
  const filteredTasks = useMemo(() => {
    if (!searchQuery) return tasks.slice(0, 20);
    const q = searchQuery.toLowerCase();
    return tasks.filter(t => t.name?.toLowerCase().includes(q)).slice(0, 20);
  }, [tasks, searchQuery]);

  const filteredEngineItems = useMemo(() => {
    if (!searchQuery) return engineRoomItems;
    const q = searchQuery.toLowerCase();
    return engineRoomItems.filter(item => item.label.toLowerCase().includes(q));
  }, [searchQuery]);

  // Keyboard shortcut: Ctrl+K for search
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('sidebar-search')?.focus();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const TaskStatusIcon = ({ status }) => {
    if (status === 'completed') return <CheckCircle size={14} className="sidebar-item-icon status-completed" />;
    if (status === 'running') return <Clock size={14} className="sidebar-item-icon status-running" />;
    if (status === 'failed') return <AlertCircle size={14} className="sidebar-item-icon status-failed" />;
    return <Clock size={14} className="sidebar-item-icon status-pending" />;
  };

  return (
    <div className="sidebar">
      {/* Header */}
      <div className="sidebar-header">
        <Link to="/app" className="sidebar-logo">
          <div className="sidebar-logo-icon">
            <LayoutGrid size={18} />
          </div>
          <div className="sidebar-logo-text">CrucibAI</div>
        </Link>
      </div>

      {/* Search Bar */}
      <div className="sidebar-search-container">
        <div className={`sidebar-search ${searchFocused ? 'focused' : ''}`}>
          <Search size={16} className="sidebar-search-icon" />
          <input
            id="sidebar-search"
            type="text"
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
            className="sidebar-search-input"
          />
          {searchQuery && (
            <button className="sidebar-search-clear" onClick={() => setSearchQuery('')}>
              <X size={14} />
            </button>
          )}
          {!searchQuery && <kbd className="sidebar-search-kbd">⌘K</kbd>}
        </div>
      </div>

      {/* 4 Pinned Navigation Items */}
      <nav className="sidebar-nav">
        <div className="sidebar-nav-section">
          {pinnedNav.map((item) => {
            const active = item.exact ? isActive(item.href) : isActivePrefix(item.href);
            return (
              <Link
                key={item.href}
                to={item.href}
                className={`sidebar-nav-item ${active ? 'active' : ''}`}
              >
                <item.icon size={18} className="sidebar-nav-icon" />
                <span className="sidebar-nav-label">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* All Tasks Section */}
      <div className="sidebar-section">
        <div className="sidebar-section-header">
          <h3 className="sidebar-section-title">All Tasks</h3>
        </div>
        <div className="sidebar-section-items">
          {filteredTasks.length > 0 ? (
            filteredTasks.map((task) => (
              <Link
                key={task.id}
                to={`/app/tasks/${task.id}`}
                className={`sidebar-item ${isActive(`/app/tasks/${task.id}`) ? 'active' : ''}`}
                title={task.name}
              >
                <TaskStatusIcon status={task.status} />
                <span className="sidebar-item-label">{task.name}</span>
              </Link>
            ))
          ) : (
            <div className="sidebar-empty">{searchQuery ? 'No matches' : 'No tasks yet'}</div>
          )}
        </div>
      </div>

      {/* Spacer */}
      <div className="sidebar-spacer" />

      {/* Engine Room Toggle */}
      <div className="sidebar-engine-room">
        <button
          className={`sidebar-engine-toggle ${engineRoomOpen ? 'open' : ''}`}
          onClick={() => setEngineRoomOpen(!engineRoomOpen)}
        >
          <Wrench size={16} />
          <span>Engine Room</span>
          <ChevronRight size={16} className={`sidebar-engine-chevron ${engineRoomOpen ? 'rotated' : ''}`} />
        </button>
        {engineRoomOpen && (
          <div className="sidebar-engine-items">
            {filteredEngineItems.map((item) => (
              <Link
                key={item.href}
                to={item.href}
                className={`sidebar-engine-item ${isActive(item.href) ? 'active' : ''}`}
              >
                <item.icon size={14} />
                <span>{item.label}</span>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Token Balance */}
      <Link to="/app/tokens" className="sidebar-token-balance" title="Credit Center">
        <Coins size={16} className="sidebar-token-icon" />
        <span className="sidebar-token-amount">{(user?.token_balance ?? 0).toLocaleString()}</span>
        <span className="sidebar-token-label">credits</span>
      </Link>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-user-avatar">
            {user?.name?.charAt(0)?.toUpperCase() || 'U'}
          </div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{user?.name || 'User'}</div>
            <div className="sidebar-user-plan">{user?.plan ? String(user.plan).charAt(0).toUpperCase() + String(user.plan).slice(1) : 'Free'}</div>
          </div>
        </div>

        <button className="sidebar-logout" onClick={onLogout} title="Logout">
          <LogOut size={18} />
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
