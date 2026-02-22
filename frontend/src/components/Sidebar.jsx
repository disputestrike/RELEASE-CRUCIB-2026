import React, { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useTaskStore } from '../stores/useTaskStore';
import {
  Plus, Search, Library, FolderOpen, CheckCircle, Clock,
  MessageCircle, Zap, AlertCircle, LogOut, ChevronRight,
  FileOutput, FileText, LayoutGrid, BookOpen, Key, Keyboard,
  CreditCard, ScrollText, BarChart3, Wrench, HelpCircle, Coins,
  X, Bell, MoreHorizontal, ExternalLink, Pencil, Share2,
  Trash2, FolderPlus, FolderInput, Star
} from 'lucide-react';
import Logo from './Logo';
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

export const Sidebar = ({ user, onLogout, projects = [], tasks: propTasks = [] }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [searchQuery, setSearchQuery] = useState('');
  const [engineRoomOpen, setEngineRoomOpen] = useState(false);
  const [searchFocused, setSearchFocused] = useState(false);
  const [menuTaskId, setMenuTaskId] = useState(null);
  const [renameTaskId, setRenameTaskId] = useState(null);
  const [renameValue, setRenameValue] = useState('');
  const [deleteConfirmTask, setDeleteConfirmTask] = useState(null);
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
  const { tasks: storeTasks, removeTask, updateTask } = useTaskStore();

  const isActive = (path) => location.pathname === path;
  const isActivePrefix = (path) => location.pathname.startsWith(path);
  const currentTaskId = location.pathname === '/app/workspace' ? searchParams.get('taskId') : null;

  // 4 pinned navigation items — spec requirement
  const pinnedNav = [
    { label: 'New Task', icon: Plus, href: '/app', exact: true },
    { label: 'Agents', icon: FolderOpen, href: '/app/agents' },
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

  // Show BOTH projects and store tasks — chat tasks must always be visible
  const listItems = useMemo(() => {
    const fromProjects = (projects || []).map(p => ({
      id: p.id,
      name: p.name || p.requirements?.prompt?.slice(0, 80) || 'Project',
      status: p.status || 'pending',
      prompt: null,
      type: 'build',
      isProject: true,
    }));
    const fromStore = (storeTasks.length > 0 ? storeTasks : propTasks || []).slice(0, 200).map(t => ({
      id: t.id,
      name: t.name || 'Task',
      status: t.status || 'pending',
      prompt: t.prompt || null,
      type: t.type || 'build',
      isProject: false,
    }));
    return [...fromProjects, ...fromStore];
  }, [projects, storeTasks, propTasks]);

  const filteredListItems = useMemo(() => {
    if (!searchQuery) return listItems.slice(0, 50);
    const q = searchQuery.toLowerCase();
    return listItems.filter(item => item.name?.toLowerCase().includes(q)).slice(0, 50);
  }, [listItems, searchQuery]);

  const openTask = (item) => {
    if (item.isProject) navigate(`/app/projects/${item.id}`);
    else if (item.type === 'chat' || item.type === 'query') {
      navigate(`/app?chatTaskId=${encodeURIComponent(item.id)}`, { state: { chatTaskId: item.id } });
    } else {
      navigate(`/app/workspace?taskId=${encodeURIComponent(item.id)}`);
    }
  };

  const openInNewTab = (item) => {
    if (item.isProject) window.open(`${window.location.origin}/app/projects/${item.id}`, '_blank');
    else if (item.type === 'chat' || item.type === 'query') {
      window.open(`${window.location.origin}/app?chatTaskId=${encodeURIComponent(item.id)}`, '_blank');
    } else {
      window.open(`${window.location.origin}/app/workspace?taskId=${encodeURIComponent(item.id)}`, '_blank');
    }
  };

  const handleRename = () => {
    if (renameTaskId && renameValue.trim()) {
      updateTask(renameTaskId, { name: renameValue.trim() });
      setRenameTaskId(null);
      setRenameValue('');
      setMenuTaskId(null);
    }
  };

  const handleDeleteClick = (item) => {
    if (item.isProject) return;
    setMenuTaskId(null);
    setDeleteConfirmTask(item);
  };

  const handleDeleteConfirm = () => {
    if (!deleteConfirmTask) return;
    const wasViewing = currentTaskId === deleteConfirmTask.id;
    const wasLastTask = storeTasks.length === 1;
    removeTask(deleteConfirmTask.id);
    setDeleteConfirmTask(null);
    if (wasViewing || wasLastTask) {
      navigate('/app', { replace: true, state: { newAgent: true } });
    }
  };

  const handleShare = (item) => {
    const url = item.isProject
      ? `${window.location.origin}/app/projects/${item.id}`
      : (item.type === 'chat' || item.type === 'query')
        ? `${window.location.origin}/app?chatTaskId=${encodeURIComponent(item.id)}`
        : `${window.location.origin}/app/workspace?taskId=${encodeURIComponent(item.id)}`;
    navigator.clipboard?.writeText(url).then(() => {});
    setMenuTaskId(null);
  };

  useEffect(() => {
    const close = (e) => {
      if (e?.target?.closest?.('.sidebar-task-dropdown') || e?.target?.closest?.('.sidebar-task-menu-btn')) return;
      setMenuTaskId(null);
    };
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, []);

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

  const TaskStatusIcon = ({ status, type }) => {
    if (type === 'chat' || type === 'query') return <MessageCircle size={14} className="sidebar-item-icon status-chat" />;
    if (type === 'agent') return <Zap size={14} className="sidebar-item-icon status-agent" />;
    if (type === 'build') {
      if (status === 'completed') return <CheckCircle size={14} className="sidebar-item-icon status-completed" />;
      if (status === 'running') return <Clock size={14} className="sidebar-item-icon status-running" />;
      if (status === 'failed') return <AlertCircle size={14} className="sidebar-item-icon status-failed" />;
      return <Clock size={14} className="sidebar-item-icon status-pending" />;
    }
    if (status === 'completed') return <CheckCircle size={14} className="sidebar-item-icon status-completed" />;
    if (status === 'running') return <Clock size={14} className="sidebar-item-icon status-running" />;
    if (status === 'failed') return <AlertCircle size={14} className="sidebar-item-icon status-failed" />;
    return <Clock size={14} className="sidebar-item-icon status-pending" />;
  };

  return (
    <div className="sidebar">
      {/* Header */}
      <div className="sidebar-header">
        <Logo variant="full" height={32} href="/app" className="sidebar-logo" showTagline={false} />
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
            const isNewTask = item.href === '/app' && item.exact;
            return isNewTask ? (
              <button
                key={item.href}
                type="button"
                onClick={() => navigate('/app', { state: { newAgent: Date.now() } })}
                className={`sidebar-nav-item ${active ? 'active' : ''}`}
              >
                <item.icon size={18} className="sidebar-nav-icon" />
                <span className="sidebar-nav-label">{item.label}</span>
              </button>
            ) : (
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

      {/* All Tasks Section — scrollable, Engine Room font, context menu */}
      <div className="sidebar-section sidebar-section-tasks">
        <div className="sidebar-section-header">
          <h3 className="sidebar-section-title">All tasks</h3>
        </div>
        <div className="sidebar-section-items sidebar-section-items-scroll">
          {filteredListItems.length > 0 ? (
            filteredListItems.map((item) => {
              const isLocalTask = !item.isProject && item.id.startsWith('task_');
              const isSelected = isLocalTask ? currentTaskId === item.id : isActive(`/app/projects/${item.id}`);
              const isEditing = renameTaskId === item.id;
              const showMenu = menuTaskId === item.id;
              return (
                <div
                  key={item.id}
                  className={`sidebar-task-row ${isSelected ? 'active' : ''}`}
                  onClick={(e) => { if (!isEditing && !e.target.closest('.sidebar-task-menu')) openTask(item); }}
                >
                  {isEditing ? (
                    <div className="sidebar-task-rename" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="text"
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleRename();
                          if (e.key === 'Escape') { setRenameTaskId(null); setRenameValue(''); }
                        }}
                        onBlur={handleRename}
                        autoFocus
                        className="sidebar-task-rename-input"
                      />
                    </div>
                  ) : (
                      <>
                        <TaskStatusIcon status={item.status} type={item.type} />
                      <span className="sidebar-task-label">{item.name}</span>
                      <button
                        type="button"
                        className="sidebar-task-menu-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (showMenu) {
                            setMenuTaskId(null);
                          } else {
                            setMenuTaskId(item.id);
                            const rect = e.currentTarget.getBoundingClientRect();
                            setMenuPosition({ top: rect.top, left: rect.right + 4 });
                          }
                        }}
                        title="Actions"
                      >
                        <MoreHorizontal size={14} />
                      </button>
                    </>
                  )}
                  {showMenu && createPortal(
                    <div
                      className="sidebar-task-dropdown sidebar-task-dropdown-fixed"
                      style={{ top: menuPosition.top, left: menuPosition.left }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button type="button" onClick={() => { handleShare(item); }}>
                        <Share2 size={14} /> Share
                      </button>
                      {isLocalTask && (
                        <button type="button" onClick={() => { setRenameTaskId(item.id); setRenameValue(item.name || ''); setMenuTaskId(null); }}>
                          <Pencil size={14} /> Rename
                        </button>
                      )}
                      <button type="button" disabled title="Coming soon">
                        <Star size={14} /> Add to favorites
                      </button>
                      <button type="button" onClick={() => { openInNewTab(item); setMenuTaskId(null); }}>
                        <ExternalLink size={14} /> Open in new tab
                      </button>
                      <button type="button" disabled title="Coming soon" className="has-submenu">
                        <FolderInput size={14} /> Move to project
                        <ChevronRight size={14} />
                      </button>
                      {isLocalTask && (
                        <button type="button" className="danger" onClick={() => handleDeleteClick(item)}>
                          <Trash2 size={14} /> Delete
                        </button>
                      )}
                    </div>,
                    document.body
                  )}
                </div>
              );
            })
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

      {/* Delete confirmation — over right pane */}
      {deleteConfirmTask && (
        <div className="sidebar-delete-overlay" onClick={() => setDeleteConfirmTask(null)}>
          <div className="sidebar-delete-modal" onClick={(e) => e.stopPropagation()}>
            <p className="sidebar-delete-title">Delete &quot;{deleteConfirmTask.name}&quot;?</p>
            <div className="sidebar-delete-actions">
              <button type="button" onClick={() => setDeleteConfirmTask(null)}>Cancel</button>
              <button type="button" className="danger" onClick={handleDeleteConfirm}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirmation — over right pane */}
      {deleteConfirmTask && (
        <div className="sidebar-delete-overlay" onClick={() => setDeleteConfirmTask(null)}>
          <div className="sidebar-delete-modal" onClick={(e) => e.stopPropagation()}>
            <p className="sidebar-delete-title">Delete &quot;{deleteConfirmTask.name}&quot;?</p>
            <div className="sidebar-delete-actions">
              <button type="button" onClick={() => setDeleteConfirmTask(null)}>Cancel</button>
              <button type="button" className="danger" onClick={handleDeleteConfirm}>Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Token Balance */}
      <Link to="/app/tokens" className="sidebar-token-balance" title="Credit Center">
        <Coins size={16} className="sidebar-token-icon" />
        <span className="sidebar-token-amount">{(user?.token_balance ?? 0).toLocaleString()}</span>
        <span className="sidebar-token-label">credits</span>
      </Link>

      {/* Footer — user and sign out on one row */}
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
