import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Plus,
  Bot,
  Search,
  Library,
  FolderOpen,
  CheckCircle,
  Clock,
  AlertCircle,
  Settings,
  LogOut,
  User,
} from 'lucide-react';
import './Sidebar.css';

/**
 * Sidebar Component (Left Navigation)
 * 
 * Features:
 * - Logo/branding
 * - Primary navigation
 * - Quick actions
 * - Projects list
 * - Tasks list
 * - User menu
 */

export const Sidebar = ({ user, onLogout, projects = [], tasks = [] }) => {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  const navItems = [
    { label: 'New Task', icon: Plus, href: '/app/new', color: 'blue' },
    { label: 'Agents', icon: Bot, href: '/app/agents', color: 'purple' },
    { label: 'Search', icon: Search, href: '/app/search', color: 'gray' },
    { label: 'Library', icon: Library, href: '/app/library', color: 'indigo' },
  ];

  return (
    <div className="sidebar">
      {/* Header */}
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">🧠</div>
          <div className="sidebar-logo-text">CrucibAI</div>
        </div>
      </div>

      {/* Primary Navigation */}
      <nav className="sidebar-nav">
        <div className="sidebar-nav-section">
          {navItems.map((item) => (
            <Link
              key={item.href}
              to={item.href}
              className={`sidebar-nav-item ${isActive(item.href) ? 'active' : ''}`}
            >
              <item.icon size={18} className={`sidebar-nav-icon color-${item.color}`} />
              <span className="sidebar-nav-label">{item.label}</span>
            </Link>
          ))}
        </div>
      </nav>

      {/* Projects Section */}
      <div className="sidebar-section">
        <div className="sidebar-section-header">
          <h3 className="sidebar-section-title">Projects</h3>
          <Link to="/app/projects/new" className="sidebar-section-action" title="New project">
            <Plus size={16} />
          </Link>
        </div>
        <div className="sidebar-section-items">
          {projects.length > 0 ? (
            projects.map((project) => (
              <Link
                key={project.id}
                to={`/app/projects/${project.id}`}
                className={`sidebar-item ${isActive(`/app/projects/${project.id}`) ? 'active' : ''}`}
                title={project.name}
              >
                <FolderOpen size={14} className="sidebar-item-icon" />
                <span className="sidebar-item-label">{project.name}</span>
              </Link>
            ))
          ) : (
            <div className="sidebar-empty">No projects yet</div>
          )}
        </div>
      </div>

      {/* Tasks Section */}
      <div className="sidebar-section">
        <div className="sidebar-section-header">
          <h3 className="sidebar-section-title">All Tasks</h3>
        </div>
        <div className="sidebar-section-items">
          {tasks.length > 0 ? (
            tasks.map((task) => (
              <Link
                key={task.id}
                to={`/app/tasks/${task.id}`}
                className={`sidebar-item ${isActive(`/app/tasks/${task.id}`) ? 'active' : ''}`}
                title={task.name}
              >
                {task.status === 'completed' && (
                  <CheckCircle size={14} className="sidebar-item-icon status-completed" />
                )}
                {task.status === 'running' && (
                  <Clock size={14} className="sidebar-item-icon status-running" />
                )}
                {task.status === 'failed' && (
                  <AlertCircle size={14} className="sidebar-item-icon status-failed" />
                )}
                {!task.status && (
                  <Clock size={14} className="sidebar-item-icon status-pending" />
                )}
                <span className="sidebar-item-label">{task.name}</span>
              </Link>
            ))
          ) : (
            <div className="sidebar-empty">No tasks yet</div>
          )}
        </div>
      </div>

      {/* Spacer */}
      <div className="sidebar-spacer" />

      {/* Footer */}
      <div className="sidebar-footer">
        {/* Settings */}
        <Link to="/app/settings" className="sidebar-footer-item">
          <Settings size={18} />
          <span>Settings</span>
        </Link>

        {/* User Menu */}
        <div className="sidebar-user">
          <div className="sidebar-user-avatar">
            {user?.name?.charAt(0)?.toUpperCase() || 'U'}
          </div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{user?.name || 'User'}</div>
            <div className="sidebar-user-email">{user?.email || 'user@example.com'}</div>
          </div>
        </div>

        {/* Logout */}
        <button className="sidebar-logout" onClick={onLogout} title="Logout">
          <LogOut size={18} />
          <span>Logout</span>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
