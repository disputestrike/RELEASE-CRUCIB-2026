import React, { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useTaskStore } from '../stores/useTaskStore';
import {
  Plus, Search, Library, FolderOpen, FolderPlus, CheckCircle, Clock,
  MessageCircle, Zap, AlertCircle, LogOut, ChevronRight, ChevronLeft,
  FileOutput, FileText, LayoutGrid, BookOpen, Key, Keyboard,
  CreditCard, ScrollText, BarChart3, Wrench, HelpCircle, Coins,
  X, Bell, MoreHorizontal, ExternalLink, Pencil, Share2,
  Trash2, FolderInput, Star, Settings, ShieldCheck, Code, Monitor
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

export const Sidebar = ({ user, onLogout, projects = [], tasks: propTasks = [], sidebarOpen = true, onToggleSidebar }) => {
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
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const accountMenuRef = React.useRef(null);
  const { tasks: storeTasks, removeTask, updateTask } = useTaskStore();

  // Close account menu on outside click
  useEffect(() => {
    const close = (e) => {
      if (accountMenuRef.current && !accountMenuRef.current.contains(e.target)) setAccountMenuOpen(false);
    };
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, []);

  const isActive = (path) => location.pathname === path;
  const isActivePrefix = (path) => location.pathname.startsWith(path);
  const currentTaskId = location.pathname === '/app/workspace' ? searchParams.get('taskId') : null;

  // Pinned navigation: New Task, New Project, Agents
  const pinnedNav = [
    { label: 'New Task', icon: Plus, href: '/app', exact: true, state: { newAgent: Date.now() } },
    { label: 'New Project', icon: FolderPlus, href: '/app', exact: true, state: { newProject: true } },
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
    { label: 'Model Manager', icon: BarChart3, href: '/app/models' },
    { label: 'Fine-Tuning', icon: Zap, href: '/app/fine-tuning' },
    { label: 'Safety Dashboard', icon: ShieldCheck, href: '/app/safety' },
    { label: 'Monitoring', icon: BarChart3, href: '/app/monitoring' },
    { label: 'VibeCode', icon: Code, href: '/app/vibecode' },
    { label: 'IDE', icon: Monitor, href: '/app/ide' },
  ];

  // Show BOTH projects and store tasks — chat tasks must always be visible; include createdAt for History grouping
  const listItems = useMemo(() => {
    const fromProjects = (projects || []).map(p => ({
      id: p.id,
      name: p.name || p.requirements?.prompt?.slice(0, 80) || 'Project',
      status: p.status || 'pending',
      prompt: null,
      type: 'build',
      isProject: true,
      createdAt: p.createdAt ?? Date.now(),
    }));
    const fromStore = (storeTasks.length > 0 ? storeTasks : propTasks || []).slice(0, 200).map(t => ({
      id: t.id,
      name: t.name || 'Task',
      status: t.status || 'pending',
      prompt: t.prompt || null,
      type: t.type || 'build',
      isProject: false,
      createdAt: t.createdAt ?? Date.now(),
    }));
    return [...fromProjects, ...fromStore];
  }, [projects, storeTasks, propTasks]);

  const filteredListItems = useMemo(() => {
    if (!searchQuery) return listItems.slice(0, 50);
    const q = searchQuery.toLowerCase();
    return listItems.filter(item => item.name?.toLowerCase().includes(q)).slice(0, 50);
  }, [listItems, searchQuery]);

  // Group history into Today vs Earlier (by task createdAt or id timestamp)
  const historyGrouped = useMemo(() => {
    const now = Date.now();
    const startOfToday = new Date();
    startOfToday.setHours(0, 0, 0, 0);
    const todayStart = startOfToday.getTime();
    const today = [];
    const earlier = [];
    filteredListItems.forEach((item) => {
      const ts = item.createdAt ?? ((typeof item.id === 'string' && item.id.startsWith('task_') ? parseInt(item.id.replace(/^task_(\d+).*/, '$1'), 10) : now) || now);
      if (ts >= todayStart) today.push(item);
      else earlier.push(item);
    });
    return { today, earlier };
  }, [filteredListItems]);

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

  const collapsed = sidebarOpen === false;

  // Collapsed rail: portaled to body. Anchor like expanded footer: menu *above* the G button (drop-up), not top-aligned to mid-screen.
  useLayoutEffect(() => {
    if (!accountMenuOpen || !collapsed) {
      setAccountMenuPortaledStyle(null);
      return;
    }
    const el = collapsedAccountBtnRef.current;
    if (!el) {
      setAccountMenuPortaledStyle(null);
      return;
    }
    const place = () => {
      const r = el.getBoundingClientRect();
      const menuGuessW = 240;
      const m = 8;
      const gap = 6; // space between bottom of menu and top of G button (matches expanded margin feel)
      let left = r.right + m;
      if (left + menuGuessW > window.innerWidth - m) {
        left = Math.max(m, r.left - menuGuessW - m);
      }
      // Bottom of menu = just above the avatar (y from viewport top) — same idea as .sidebar-account-menu { bottom: 100% } on the expanded footer
      const menuBottomY = Math.max(m, r.top - gap);
      const bottomPx = window.innerHeight - menuBottomY;
      const maxSpaceAbove = menuBottomY - m;
      const maxH = Math.min(420, maxSpaceAbove, window.innerHeight * 0.55);
      setAccountMenuPortaledStyle({
        position: 'fixed',
        left: `${left}px`,
        bottom: `${bottomPx}px`,
        top: 'auto',
        zIndex: 10050,
        maxHeight: `${Math.max(120, maxH)}px`,
        overflowY: 'auto',
        margin: 0,
        right: 'auto',
      });
    };
    place();
    window.addEventListener('scroll', place, true);
    window.addEventListener('resize', place);
    return () => {
      window.removeEventListener('scroll', place, true);
      window.removeEventListener('resize', place);
    };
  }, [accountMenuOpen, collapsed]);

  const renderHistoryRow = (item) => {
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
            <span className="sidebar-task-label-wrap">
              <span className="sidebar-task-label">{item.name}</span>
              {isLocalTask && !item.jobId && item.type === 'build' && (
                <span
                  className="sidebar-task-norun"
                  title="Build not started yet — open Workspace to run a plan."
                >
                  draft
                </span>
              )}
            </span>
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
  };

  return (
    <div className={`sidebar ${collapsed ? 'sidebar--collapsed' : ''}`}>
      {/* Collapse toggle — visible when expanded (desktop) */}
      {!collapsed && onToggleSidebar && (
        <button
          type="button"
          className="sidebar-collapse-btn"
          onClick={onToggleSidebar}
          aria-label="Collapse sidebar"
          title="Collapse sidebar"
        >
          <ChevronLeft size={14} />
        </button>
      )}

      {/* Collapsed strip — only when collapsed */}
      <div className="sidebar-collapsed-strip">
        <button
          type="button"
          className="sidebar-collapse-btn"
          onClick={onToggleSidebar}
          aria-label="Expand sidebar"
          title="Expand sidebar"
        >
          <ChevronRight size={18} />
        </button>
      </div>

      {/* Header */}
      <div className="sidebar-header">
        <Logo variant="full" height={32} href="/app" className="sidebar-logo" showTagline={false} dark />
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

      {/* Pinned Navigation: New Task, New Project, Agents */}
      <nav className="sidebar-nav">
        <div className="sidebar-nav-section">
          {pinnedNav.map((item) => {
            const active = item.exact ? isActive(item.href) : isActivePrefix(item.href);
            const isAppHome = item.href === '/app' && item.exact;
            return isAppHome ? (
              <button
                key={item.label}
                type="button"
                onClick={() => navigate('/app', { state: item.state || { newAgent: Date.now() } })}
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

      {/* History Section — Today / Earlier, scrollable, context menu */}
      <div className="sidebar-section sidebar-section-tasks">
        <div className="sidebar-section-header">
          <h3 className="sidebar-section-title">History</h3>
        </div>
        <div className="sidebar-section-items sidebar-section-items-scroll">
          {(historyGrouped.today.length > 0 || historyGrouped.earlier.length > 0) ? (
            <>
              {historyGrouped.today.length > 0 && (
                <>
                  <div className="sidebar-history-group-label">Today</div>
                  {historyGrouped.today.map((item) => renderHistoryRow(item))}
                </>
              )}
              {historyGrouped.earlier.length > 0 && (
                <>
                  <div className="sidebar-history-group-label">Earlier</div>
                  {historyGrouped.earlier.map((item) => renderHistoryRow(item))}
                </>
              )}
            </>
          ) : (
            <div className="sidebar-empty">{searchQuery ? 'No matches' : 'No history yet'}</div>
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

      {/* Delete confirmation — portaled to body so .sidebar overflow/transform never traps it in the left rail */}
      {deleteConfirmTask &&
        createPortal(
          <div
            className="sidebar-delete-overlay"
            onClick={() => setDeleteConfirmTask(null)}
            role="presentation"
          >
            <div
              className="sidebar-delete-modal"
              onClick={(e) => e.stopPropagation()}
              role="dialog"
              aria-modal="true"
              aria-labelledby="sidebar-delete-confirm-title"
            >
              <p className="sidebar-delete-title" id="sidebar-delete-confirm-title">
                Delete &quot;{deleteConfirmTask.name}&quot;?
              </p>
              <div className="sidebar-delete-actions">
                <button type="button" onClick={() => setDeleteConfirmTask(null)}>
                  Cancel
                </button>
                <button type="button" className="danger" onClick={handleDeleteConfirm}>
                  Delete
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}

      {/* Collapsed sidebar: account menu portaled to body (see useLayoutEffect) — avoids overflow clip on narrow rail */}
      {collapsed &&
        accountMenuOpen &&
        accountMenuPortaledStyle &&
        createPortal(
          <div
            ref={accountMenuDropdownRef}
            className="sidebar-account-menu sidebar-account-menu--portaled"
            style={accountMenuPortaledStyle}
            role="menu"
          >
            <Link to="/app/settings" role="menuitem" onClick={() => setAccountMenuOpen(false)}>
              <Settings size={16} /> Settings
            </Link>
            <Link to="/app/settings" state={{ openTab: 'engine' }} role="menuitem" onClick={() => setAccountMenuOpen(false)}>
              <LayoutGrid size={16} /> Engine room
            </Link>
            <Link to="/app/billing" role="menuitem" onClick={() => setAccountMenuOpen(false)}>
              <Coins size={16} /> Manage billing
            </Link>
            <Link to="/pricing" role="menuitem" onClick={() => setAccountMenuOpen(false)}>
              <Zap size={16} /> Upgrade plan
            </Link>
            <div className="sidebar-account-menu-divider" />
            <button
              type="button"
              className="sidebar-account-menu-logout"
              role="menuitem"
              onClick={() => {
                setAccountMenuOpen(false);
                onLogout?.();
              }}
            >
              <LogOut size={16} /> Log out
            </button>
          </div>,
          document.body
        )}

      {/* Token Balance */}
      <Link to="/app/tokens" className="sidebar-token-balance" title="Credit Center">
        <Coins size={16} className="sidebar-token-icon" />
        <span className="sidebar-token-amount">{(user?.token_balance ?? 0).toLocaleString()}</span>
        <span className="sidebar-token-label">credits</span>
      </Link>

      {/* Footer — account trigger with dropdown (Settings, Logout) */}
      <div className="sidebar-footer" ref={accountMenuRef}>
        <button
          type="button"
          className="sidebar-account-trigger"
          onClick={() => setAccountMenuOpen((o) => !o)}
          aria-expanded={accountMenuOpen}
          aria-haspopup="true"
          aria-label="Account menu"
        >
          <div className="sidebar-user-avatar">
            {user?.name?.charAt(0)?.toUpperCase() || 'G'}
          </div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{user?.name || 'Guest'}</div>
            <div className="sidebar-user-plan">{user?.plan ? String(user.plan).charAt(0).toUpperCase() + String(user.plan).slice(1) : 'Free'}</div>
          </div>
          <ChevronRight size={16} className="sidebar-account-chevron" />
        </button>
        {accountMenuOpen && (
          <div className="sidebar-account-menu" role="menu">
            <Link
              to="/app/settings"
              role="menuitem"
              onClick={() => setAccountMenuOpen(false)}
            >
              <Settings size={16} /> Settings
            </Link>
            <button
              type="button"
              className="sidebar-account-menu-logout"
              role="menuitem"
              onClick={() => { setAccountMenuOpen(false); onLogout?.(); }}
            >
              <LogOut size={16} /> Log out
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;
