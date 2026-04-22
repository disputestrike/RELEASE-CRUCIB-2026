import React, { useState, useEffect, useLayoutEffect, useMemo, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useTaskStore } from '../stores/useTaskStore';
import {
  Plus, Search, Library, FolderOpen, FolderPlus, CheckCircle, Clock,
  MessageCircle, Zap, AlertCircle, LogOut, ChevronRight, ChevronDown,
  LayoutGrid, BookOpen, HelpCircle, Coins,
  X, MoreHorizontal, ExternalLink, Pencil, Share2,
  Trash2, FolderInput, Star, Settings, Shield,
  PanelLeftClose, PanelLeftOpen, History, Home, GitBranch,
} from 'lucide-react';
import Logo from './Logo';
import './Sidebar.css';

/**
 * Sidebar — minimal primary nav (Manus-style density).
 * Create: New + menu (task / project). Work: Home, Agents. Library: Prompts / Learn / Patterns.
 * History: only when there is at least one task or project.
 * Runs, Marketplace, and other power routes: Settings → Engine room only (not duplicated here).
 */

export const Sidebar = ({ user, onLogout, projects = [], tasks: propTasks = [], sidebarOpen = true, onToggleSidebar }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchFocused, setSearchFocused] = useState(false);
  const [createMenuOpen, setCreateMenuOpen] = useState(false);
  const [libraryOpen, setLibraryOpen] = useState(() =>
    /^\/app\/(prompts|learn|patterns)(\/|$)/.test(location.pathname || '')
  );
  const createMenuRef = useRef(null);
  const [menuTaskId, setMenuTaskId] = useState(null);
  const [renameTaskId, setRenameTaskId] = useState(null);
  const [renameValue, setRenameValue] = useState('');
  const [deleteConfirmTask, setDeleteConfirmTask] = useState(null);
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
  const [moveProjectExpanded, setMoveProjectExpanded] = useState(false);
  const menuDropdownRef = useRef(null);
  const menuAnchorRef = useRef({ top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0 });
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

  useEffect(() => {
    if (/^\/app\/(prompts|learn|patterns)(\/|$)/.test(location.pathname || '')) setLibraryOpen(true);
  }, [location.pathname]);

  useEffect(() => {
    if (!createMenuOpen) return;
    const onDoc = (e) => {
      if (createMenuRef.current && !createMenuRef.current.contains(e.target)) setCreateMenuOpen(false);
    };
    document.addEventListener('click', onDoc);
    return () => document.removeEventListener('click', onDoc);
  }, [createMenuOpen]);

  const isActive = (path) => location.pathname === path;
  const isActivePrefix = (path) => location.pathname.startsWith(path);
  /** Unified workspace: Manus-style headline — logo only in pane 1; wordmark lives in workspace center header. */
  const workspaceHeadlineLayout =
    /^\/app\/workspace(\/|$)/.test(location.pathname) || /^\/app\/workspace-manus(\/|$)/.test(location.pathname);
  const currentTaskId =
    location.pathname === '/app/workspace' || location.pathname === '/app/workspace-manus'
      ? searchParams.get('taskId')
      : null;

  const togglePin = React.useCallback((id) => {
    setPinnedIds((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id].slice(0, 40);
      try {
        localStorage.setItem('crucibai_sidebar_pinned_ids', JSON.stringify(next));
      } catch {
        /* ignore quota / private mode */
      }
      return next;
    });
  }, []);

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
      linkedProjectId: t.linkedProjectId || null,
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
      const qs = new URLSearchParams({ taskId: item.id });
      if (item.linkedProjectId) qs.set('projectId', item.linkedProjectId);
      if (item.jobId) qs.set('jobId', item.jobId);
      navigate(`/app/workspace?${qs.toString()}`);
    }
  };

  const openInNewTab = (item) => {
    if (item.isProject) window.open(`${window.location.origin}/app/projects/${item.id}`, '_blank');
    else if (item.type === 'chat' || item.type === 'query') {
      window.open(`${window.location.origin}/app?chatTaskId=${encodeURIComponent(item.id)}`, '_blank');
    } else {
      const qs = new URLSearchParams({ taskId: item.id });
      if (item.linkedProjectId) qs.set('projectId', item.linkedProjectId);
      if (item.jobId) qs.set('jobId', item.jobId);
      window.open(`${window.location.origin}/app/workspace?${qs.toString()}`, '_blank');
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
    const origin = window.location.origin;
    let url;
    if (item.isProject) url = `${origin}/app/projects/${item.id}`;
    else if (item.type === 'chat' || item.type === 'query') {
      const qs = new URLSearchParams({ chatTaskId: item.id });
      if (item.linkedProjectId) qs.set('projectId', item.linkedProjectId);
      url = `${origin}/app?${qs.toString()}`;
    } else {
      const qs = new URLSearchParams({ taskId: item.id });
      if (item.linkedProjectId) qs.set('projectId', item.linkedProjectId);
      if (item.jobId) qs.set('jobId', item.jobId);
      url = `${origin}/app/workspace?${qs.toString()}`;
    }
    navigator.clipboard?.writeText(url).then(() => {});
    setMenuTaskId(null);
  };

  const clampTaskMenuToViewport = useCallback(() => {
    const el = menuDropdownRef.current;
    if (!el) return;
    const pad = 8;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const ar = menuAnchorRef.current;
    let left = ar.right + 4;
    let top = ar.top;
    el.style.maxHeight = `${Math.max(120, vh - 2 * pad)}px`;
    const w = el.offsetWidth;
    const h = el.offsetHeight;
    if (left + w > vw - pad) left = ar.left - w - 4;
    if (left < pad) left = pad;
    if (left + w > vw - pad) left = Math.max(pad, vw - pad - w);
    if (top + h > vh - pad) top = vh - pad - h;
    if (top < pad) top = pad;
    el.style.top = `${top}px`;
    el.style.left = `${left}px`;
  }, []);

  useLayoutEffect(() => {
    if (!menuTaskId) return;
    const run = () => {
      clampTaskMenuToViewport();
      requestAnimationFrame(() => clampTaskMenuToViewport());
    };
    run();
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(run) : null;
    if (menuDropdownRef.current && ro) ro.observe(menuDropdownRef.current);
    window.addEventListener('resize', run);
    window.addEventListener('scroll', run, true);
    return () => {
      ro?.disconnect();
      window.removeEventListener('resize', run);
      window.removeEventListener('scroll', run, true);
    };
  }, [menuTaskId, moveProjectExpanded, clampTaskMenuToViewport]);

  useEffect(() => {
    if (!menuTaskId) setMoveProjectExpanded(false);
  }, [menuTaskId]);

  useEffect(() => {
    const close = (e) => {
      if (e?.target?.closest?.('.sidebar-task-dropdown') || e?.target?.closest?.('.sidebar-task-menu-btn')) return;
      setMenuTaskId(null);
    };
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, []);

  useEffect(() => {
    if (!menuTaskId) return;
    const onKey = (e) => {
      if (e.key !== 'Escape') return;
      if (moveProjectExpanded) setMoveProjectExpanded(false);
      else setMenuTaskId(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [menuTaskId, moveProjectExpanded]);

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
        onClick={(e) => { if (!isEditing && !e.target.closest('.sidebar-task-menu-btn')) openTask(item); }}
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
                  const rect = e.currentTarget.getBoundingClientRect();
                  menuAnchorRef.current = {
                    top: rect.top,
                    left: rect.left,
                    right: rect.right,
                    bottom: rect.bottom,
                    width: rect.width,
                    height: rect.height,
                  };
                  setMoveProjectExpanded(false);
                  setMenuTaskId(item.id);
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
            ref={menuDropdownRef}
            className="sidebar-task-dropdown sidebar-task-dropdown-fixed"
            style={{ top: menuPosition.top, left: menuPosition.left }}
            onClick={(e) => e.stopPropagation()}
            role="menu"
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
            {!item.isProject && (
              <>
                <button
                  type="button"
                  className={`has-submenu${moveProjectExpanded ? ' sidebar-task-move-trigger--open' : ''}`}
                  onClick={() => setMoveProjectExpanded((v) => !v)}
                  aria-expanded={moveProjectExpanded}
                >
                  <FolderInput size={14} /> Move to project
                  <ChevronRight size={14} className="sidebar-task-move-chevron" />
                </button>
                {moveProjectExpanded && (
                  <div className="sidebar-task-move-panel" role="group" aria-label="Choose project">
                    {(projects || []).filter((p) => p && p.id).length === 0 ? (
                      <div className="sidebar-task-move-empty">No projects yet. Use Create → New Project.</div>
                    ) : (
                      (projects || []).filter((p) => p && p.id).map((p) => (
                        <button
                          key={p.id}
                          type="button"
                          className={item.linkedProjectId === p.id ? 'sidebar-task-move-project sidebar-task-move-project--current' : 'sidebar-task-move-project'}
                          onClick={() => {
                            updateTask(item.id, { linkedProjectId: p.id });
                            setMenuTaskId(null);
                            setMoveProjectExpanded(false);
                          }}
                        >
                          {item.linkedProjectId === p.id ? '✓ ' : ''}
                          {p.name || p.requirements?.prompt?.slice(0, 48) || 'Project'}
                        </button>
                      ))
                    )}
                    {item.linkedProjectId && (
                      <button
                        type="button"
                        className="sidebar-task-move-clear"
                        onClick={() => {
                          updateTask(item.id, { linkedProjectId: null });
                          setMenuTaskId(null);
                          setMoveProjectExpanded(false);
                        }}
                      >
                        Remove from project
                      </button>
                    )}
                  </div>
                )}
              </>
            )}
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
      {/* Collapsed strip — Manus-like: top nav, spacer, account (credits live in app header) */}
      <div className="sidebar-collapsed-strip">
        <div className="sidebar-collapsed-top">
          <button
            type="button"
            className="sidebar-collapse-btn sidebar-collapse-btn--expand"
            onClick={onToggleSidebar}
            aria-label="Expand sidebar"
            title="Expand sidebar"
          >
            {/* Rest state: cube logo identity. Hover: expand-toggle icon swaps in. */}
            <span className="sidebar-collapse-btn-logo" aria-hidden="true">
              <Logo height={20} showWordmark={false} showTagline={false} />
            </span>
            <PanelLeftOpen size={20} className="sidebar-collapse-btn-icon" aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={() => navigate('/app', { state: { newAgent: Date.now() } })}
            className="sidebar-collapsed-icon"
            title="New task"
            aria-label="New task"
          >
            <Plus size={20} />
          </button>
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
                <Link to="/app/settings" state={{ openTab: 'engine' }} role="menuitem" onClick={() => setAccountMenuOpen(false)}><LayoutGrid size={16} /> Engine room</Link>
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
      <div className={`sidebar-header ${workspaceHeadlineLayout ? 'sidebar-header--workspace-headline' : ''}`}>
        <Logo
          variant="full"
          height={32}
          href="/app"
          className="sidebar-logo"
          showTagline={false}
          showWordmark={true}
          nameClassName="sidebar-logo-text"
        />
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
        <div className="sidebar-nav-section sidebar-nav-section--create" ref={createMenuRef}>
          <div className="sidebar-create-row">
            <button
              type="button"
              onClick={() => navigate('/app', { state: { newAgent: Date.now() } })}
              className={`sidebar-nav-item sidebar-create-main ${isActive('/app') ? 'active' : ''}`}
            >
              <Plus size={18} className="sidebar-nav-icon" />
              <span className="sidebar-nav-label">New</span>
            </button>
            <button
              type="button"
              className={`sidebar-create-chevron ${createMenuOpen ? 'open' : ''}`}
              aria-label="More create options"
              aria-expanded={createMenuOpen}
              onClick={(e) => {
                e.stopPropagation();
                setCreateMenuOpen((o) => !o);
              }}
            >
              <ChevronDown size={16} />
            </button>
          </div>
          {createMenuOpen && (
            <div className="sidebar-create-popover" role="menu">
              <button type="button" role="menuitem" className="sidebar-create-popover-item" onClick={() => { navigate('/app', { state: { newAgent: Date.now() } }); setCreateMenuOpen(false); }}>
                <Plus size={14} /> New task
              </button>
              <button type="button" role="menuitem" className="sidebar-create-popover-item" onClick={() => { navigate('/app', { state: { newProject: true } }); setCreateMenuOpen(false); }}>
                <FolderPlus size={14} /> New project
              </button>
            </div>
          )}
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
          <Link to="/app/what-if" className={`sidebar-nav-item ${isActivePrefix('/app/what-if') ? 'active' : ''}`}>
            <GitBranch size={18} className="sidebar-nav-icon" />
            <span className="sidebar-nav-label">What-If</span>
          </Link>
        </div>
        <div className="sidebar-nav-group-label">Library</div>
        <div className="sidebar-nav-section">
          <button
            type="button"
            className={`sidebar-nav-item sidebar-library-toggle ${libraryOpen ? 'open' : ''}`}
            onClick={() => setLibraryOpen((o) => !o)}
            aria-expanded={libraryOpen}
          >
            <Library size={18} className="sidebar-nav-icon" />
            <span className="sidebar-nav-label">Prompts, Learn &amp; Patterns</span>
            <ChevronRight size={16} className={`sidebar-library-chevron ${libraryOpen ? 'rotated' : ''}`} />
          </button>
          {libraryOpen && (
            <div className="sidebar-library-nested">
              <Link to="/app/prompts" className={`sidebar-nav-item sidebar-nav-item--nested ${isActivePrefix('/app/prompts') ? 'active' : ''}`} onClick={() => setLibraryOpen(true)}>
                <BookOpen size={16} className="sidebar-nav-icon" />
                <span className="sidebar-nav-label">Prompts</span>
              </Link>
              <Link to="/app/learn" className={`sidebar-nav-item sidebar-nav-item--nested ${isActivePrefix('/app/learn') ? 'active' : ''}`} onClick={() => setLibraryOpen(true)}>
                <HelpCircle size={16} className="sidebar-nav-icon" />
                <span className="sidebar-nav-label">Learn</span>
              </Link>
              <Link to="/app/patterns" className={`sidebar-nav-item sidebar-nav-item--nested ${isActivePrefix('/app/patterns') ? 'active' : ''}`} onClick={() => setLibraryOpen(true)}>
                <Library size={16} className="sidebar-nav-icon" />
                <span className="sidebar-nav-label">Patterns</span>
              </Link>
            </div>
          )}
        </div>
      </nav>

      {/* History — only when there is at least one task or project */}
      {listItems.length > 0 && (
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
      )}

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
              to="/app/settings"
              state={{ openTab: 'engine' }}
              role="menuitem"
              onClick={() => setAccountMenuOpen(false)}
            >
              <LayoutGrid size={16} /> Engine room
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
