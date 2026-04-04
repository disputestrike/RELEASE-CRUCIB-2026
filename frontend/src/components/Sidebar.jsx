import React, { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useTaskStore } from '../stores/useTaskStore';
import {
  Plus, Search, Library, FolderOpen, FolderPlus, CheckCircle, Clock,
  MessageCircle, Zap, AlertCircle, LogOut, ChevronRight,
  FileOutput, FileText, LayoutGrid, BookOpen, Key, Keyboard,
  CreditCard, ScrollText, BarChart3, Wrench, HelpCircle, Coins,
  X, Bell, MoreHorizontal, ExternalLink, Pencil, Share2,
  Trash2, FolderInput, Star, Settings, ShieldCheck, Code, Monitor,
  PanelLeftClose, PanelLeftOpen, History, Home,
  Bot, Radio, MessageSquare, ShoppingBag, Users, Sparkles, PlayCircle,
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
  const [pinnedIds, setPinnedIds] = useState(() => {
    try {
      const raw = localStorage.getItem('crucibai_sidebar_pinned_ids');
      const a = raw ? JSON.parse(raw) : [];
      return Array.isArray(a) ? a : [];
    } catch {
      return [];
    }
  });
  const accountMenuRef = React.useRef(null);
  const collapsedAccountRef = React.useRef(null);
  const { tasks: storeTasks, removeTask, updateTask } = useTaskStore();

  // Close account menu on outside click (expanded footer or collapsed strip)
  useEffect(() => {
    const close = (e) => {
      const inside = accountMenuRef.current?.contains(e.target) || collapsedAccountRef.current?.contains(e.target);
      if (!inside) setAccountMenuOpen(false);
    };
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, []);

  const isActive = (path) => location.pathname === path;
  const isActivePrefix = (path) => location.pathname.startsWith(path);
  const currentTaskId = location.pathname === '/app/workspace' ? searchParams.get('taskId') : null;

  const togglePin = React.useCallback((id) => {
    setPinnedIds((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id].slice(0, 40);
      try {
        localStorage.setItem('crucibai_sidebar_pinned_ids', JSON.stringify(next));
      } catch (_) {}
      return next;
    });
  }, []);

  /** Create — primary actions (compliance S-01: grouped IA) */
  const createNav = [
    { label: 'New Task', icon: Plus, href: '/app', exact: true, state: { newAgent: Date.now() } },
    { label: 'New Project', icon: FolderPlus, href: '/app', exact: true, state: { newProject: true } },
  ];

  // Engine Room — collapsed by default, for power users
  // Includes platform infrastructure items (Studio/Knowledge/Channels/Sessions/Commerce/Members)
  // which are internal config and not part of the main builder workflow
  const engineRoomItems = [
    { label: 'Skills', icon: Sparkles, href: '/app/skills' },
    { label: 'Studio', icon: Bot, href: '/app/studio' },
    { label: 'Knowledge', icon: BookOpen, href: '/app/knowledge' },
    { label: 'Channels', icon: Radio, href: '/app/channels' },
    { label: 'Sessions', icon: MessageSquare, href: '/app/sessions' },
    { label: 'Commerce', icon: ShoppingBag, href: '/app/commerce' },
    { label: 'Members', icon: Users, href: '/app/members' },
    // original engine items below:
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
    { label: 'Auto-Runner', icon: PlayCircle, href: '/app/auto-runner' },
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

  /** Pinned → Active → Failed → Recent (Today / Earlier) — compliance: meaningful task history */
  const historyBuckets = useMemo(() => {
    const pinSet = new Set(pinnedIds);
    const pinned = [];
    const active = [];
    const failed = [];
    const pool = [];
    const now = Date.now();
    for (const item of filteredListItems) {
      if (pinSet.has(item.id)) {
        pinned.push(item);
        continue;
      }
      const st = String(item.status || '').toLowerCase();
      if (st === 'running' || st === 'queued') {
        active.push(item);
        continue;
      }
      if (st === 'failed') {
        failed.push(item);
        continue;
      }
      pool.push(item);
    }
    const startOfToday = new Date();
    startOfToday.setHours(0, 0, 0, 0);
    const todayStart = startOfToday.getTime();
    const today = [];
    const earlier = [];
    pool.forEach((item) => {
      let ts = item.createdAt;
      if (ts == null && typeof item.id === 'string' && item.id.startsWith('task_')) {
        const parsed = parseInt(item.id.replace(/^task_(\d+).*/, '$1'), 10);
        ts = Number.isFinite(parsed) ? parsed : now;
      }
      if (ts == null) ts = now;
      if (ts >= todayStart) today.push(item);
      else earlier.push(item);
    });
    return { pinned, active, failed, today, earlier };
  }, [filteredListItems, pinnedIds]);

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
  const displayName = user?.name
    || (user?.email && !String(user.email).toLowerCase().includes('guest') ? (user.email.split('@')[0] || 'User') : null)
    || 'Guest';

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
            <button
              type="button"
              onClick={() => {
                togglePin(item.id);
                setMenuTaskId(null);
              }}
            >
              <Star size={14} className={pinnedIds.includes(item.id) ? 'sidebar-star-pinned' : ''} />
              {pinnedIds.includes(item.id) ? 'Unpin from sidebar' : 'Pin to sidebar'}
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
      {/* Collapsed strip — Manus-like: top nav, then spacer, then bottom (Engine, Credit, Settings, Account) */}
      <div className="sidebar-collapsed-strip">
        <div className="sidebar-collapsed-top">
          <button
            type="button"
            className="sidebar-collapse-btn sidebar-collapse-btn--expand"
            onClick={onToggleSidebar}
            aria-label="Expand sidebar"
            title="Expand sidebar"
          >
            <PanelLeftOpen size={20} />
          </button>
          {createNav.map((item) => {
            const isAppHome = item.exact && item.href === '/app';
            return isAppHome ? (
              <button
                key={item.label}
                type="button"
                onClick={() => navigate('/app', { state: item.state || { newAgent: Date.now() } })}
                className="sidebar-collapsed-icon"
                title={item.label}
                aria-label={item.label}
              >
                <item.icon size={20} />
              </button>
            ) : (
              <Link
                key={item.href}
                to={item.href}
                className="sidebar-collapsed-icon"
                title={item.label}
                aria-label={item.label}
              >
                <item.icon size={20} />
              </Link>
            );
          })}
          <Link to="/app" className="sidebar-collapsed-icon" title="Home" aria-label="Home">
            <Home size={20} />
          </Link>
          <Link to="/app/agents" className="sidebar-collapsed-icon" title="Agents" aria-label="Agents">
            <FolderOpen size={20} />
          </Link>
          <button type="button" className="sidebar-collapsed-icon" onClick={onToggleSidebar} title="Search" aria-label="Search">
            <Search size={20} />
          </button>
          <button type="button" className="sidebar-collapsed-icon" onClick={onToggleSidebar} title="History" aria-label="History">
            <History size={20} />
          </button>
        </div>
        <div className="sidebar-collapsed-spacer" aria-hidden="true" />
        <div className="sidebar-collapsed-bottom">
          <button type="button" className="sidebar-collapsed-icon" onClick={onToggleSidebar} title="Engine Room" aria-label="Engine Room">
            <Wrench size={20} />
          </button>
          <Link to="/app/tokens" className="sidebar-collapsed-icon" title="Credit Center" aria-label="Credit Center">
            <Coins size={20} />
          </Link>
          <div className="sidebar-collapsed-account-wrap" ref={collapsedAccountRef}>
            <button
              type="button"
              className={`sidebar-collapsed-icon sidebar-collapsed-account ${accountMenuOpen ? 'active' : ''}`}
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); setAccountMenuOpen((o) => !o); }}
              title={`Account: ${displayName} — Settings, Credits, Log out`}
              aria-label="Account menu (Settings, Credits, Log out)"
              aria-expanded={accountMenuOpen}
            >
              <div className="sidebar-collapsed-avatar">{(displayName || 'G').charAt(0).toUpperCase()}</div>
            </button>
            {accountMenuOpen && (
              <div className="sidebar-account-menu sidebar-account-menu--dropup" role="menu">
                <Link to="/app/settings" role="menuitem" onClick={() => setAccountMenuOpen(false)}><Settings size={16} /> Settings</Link>
                <Link to="/app/tokens" role="menuitem" onClick={() => setAccountMenuOpen(false)}><Coins size={16} /> Credits & Billing</Link>
                <Link to="/pricing" role="menuitem" onClick={() => setAccountMenuOpen(false)}><Zap size={16} /> Upgrade plan</Link>
                <div className="sidebar-account-menu-divider" />
                <button type="button" className="sidebar-account-menu-logout" role="menuitem" onClick={() => { setAccountMenuOpen(false); onLogout?.(); }}><LogOut size={16} /> Log out</button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Header — collapse button at top inside pane one (Manus-like) */}
      <div className="sidebar-header">
        <Logo variant="full" height={32} href="/app" className="sidebar-logo" showTagline={false} dark />
        {onToggleSidebar && (
          <button
            type="button"
            className="sidebar-header-collapse"
            onClick={onToggleSidebar}
            aria-label="Collapse sidebar"
            title="Collapse sidebar"
          >
            <PanelLeftClose size={18} />
          </button>
        )}
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

      {/* Grouped navigation — Create / Work / Knowledge (Engine Room stays secondary, below) */}
      <nav className="sidebar-nav" aria-label="Primary">
        <div className="sidebar-nav-group-label">Create</div>
        <div className="sidebar-nav-section">
          {createNav.map((item) => {
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
        <div className="sidebar-nav-group-label">Work</div>
        <div className="sidebar-nav-section">
          <Link to="/app" className={`sidebar-nav-item ${isActive('/app') ? 'active' : ''}`}>
            <Home size={18} className="sidebar-nav-icon" />
            <span className="sidebar-nav-label">Home</span>
          </Link>
          <Link to="/app/agents" className={`sidebar-nav-item ${isActivePrefix('/app/agents') ? 'active' : ''}`}>
            <FolderOpen size={18} className="sidebar-nav-icon" />
            <span className="sidebar-nav-label">Agents</span>
          </Link>
        </div>
        <div className="sidebar-nav-group-label">Knowledge</div>
        <div className="sidebar-nav-section">
          <Link to="/app/prompts" className={`sidebar-nav-item ${isActivePrefix('/app/prompts') ? 'active' : ''}`}>
            <BookOpen size={18} className="sidebar-nav-icon" />
            <span className="sidebar-nav-label">Prompts</span>
          </Link>
          <Link to="/app/learn" className={`sidebar-nav-item ${isActivePrefix('/app/learn') ? 'active' : ''}`}>
            <HelpCircle size={18} className="sidebar-nav-icon" />
            <span className="sidebar-nav-label">Learn</span>
          </Link>
          <Link to="/app/patterns" className={`sidebar-nav-item ${isActivePrefix('/app/patterns') ? 'active' : ''}`}>
            <Library size={18} className="sidebar-nav-icon" />
            <span className="sidebar-nav-label">Patterns</span>
          </Link>
        </div>
      </nav>

      {/* History Section — Today / Earlier, scrollable, context menu */}
      <div className="sidebar-section sidebar-section-tasks">
        <div className="sidebar-section-header">
          <h3 className="sidebar-section-title">History</h3>
        </div>
        <div className="sidebar-section-items sidebar-section-items-scroll">
          {(historyBuckets.pinned.length > 0
            || historyBuckets.active.length > 0
            || historyBuckets.failed.length > 0
            || historyBuckets.today.length > 0
            || historyBuckets.earlier.length > 0) ? (
            <>
              {historyBuckets.pinned.length > 0 && (
                <>
                  <div className="sidebar-history-group-label">Pinned</div>
                  {historyBuckets.pinned.map((item) => renderHistoryRow(item))}
                </>
              )}
              {historyBuckets.active.length > 0 && (
                <>
                  <div className="sidebar-history-group-label">Active</div>
                  {historyBuckets.active.map((item) => renderHistoryRow(item))}
                </>
              )}
              {historyBuckets.failed.length > 0 && (
                <>
                  <div className="sidebar-history-group-label">Failed</div>
                  {historyBuckets.failed.map((item) => renderHistoryRow(item))}
                </>
              )}
              {historyBuckets.today.length > 0 && (
                <>
                  <div className="sidebar-history-group-label">Today</div>
                  {historyBuckets.today.map((item) => renderHistoryRow(item))}
                </>
              )}
              {historyBuckets.earlier.length > 0 && (
                <>
                  <div className="sidebar-history-group-label">Earlier</div>
                  {historyBuckets.earlier.map((item) => renderHistoryRow(item))}
                </>
              )}
            </>
          ) : (
            <div className="sidebar-empty">{searchQuery ? 'No matches' : 'No history yet'}</div>
          )}
        </div>
      </div>

      {/* Spacer — pushes History up, keeps Engine/Credits/Settings at bottom */}
      <div className="sidebar-spacer" />

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

      {/* Bottom section: Engine Room + Credits only (Settings is in Guest dropdown) */}
      <div className="sidebar-bottom">
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
        <Link to="/app/tokens" className="sidebar-token-balance" title="Credit Center">
          <Coins size={16} className="sidebar-token-icon" />
          <span className="sidebar-token-amount">
            {user != null
              ? (user.credit_balance ?? Math.floor((user.token_balance ?? 0) / 1000) ?? 0).toLocaleString()
              : '—'}
          </span>
          <span className="sidebar-token-label">credits</span>
        </Link>
      </div>

      {/* Footer — account trigger with dropdown (Logout, etc.) */}
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
            {(displayName || 'G').charAt(0).toUpperCase()}
          </div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{displayName}</div>
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
            <Link
              to="/app/tokens"
              role="menuitem"
              onClick={() => setAccountMenuOpen(false)}
            >
              <Coins size={16} /> Credits & Billing
            </Link>
            <Link
              to="/pricing"
              role="menuitem"
              onClick={() => setAccountMenuOpen(false)}
            >
              <Zap size={16} /> Upgrade plan
            </Link>
            <div className="sidebar-account-menu-divider" />
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
