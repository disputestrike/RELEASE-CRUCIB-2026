import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Plus, Zap, FolderOpen, Clock, CheckCircle,
  AlertCircle, TrendingUp, Bot, ArrowRight, Play,
  Share2, Copy, Bookmark, Upload, X, Github, Settings,
  Eye, Code, Download
} from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';
import Layout3Column from '../components/Layout3Column';
import Sidebar from '../components/Sidebar';
import RightPanel from '../components/RightPanel';
import './DashboardRedesigned.css';

/**
 * Redesigned Dashboard Component
 * 
 * Features:
 * - 3-column Manus-inspired layout
 * - Clean, minimal stat cards
 * - Quick action buttons
 * - Recent projects list
 * - Responsive design
 * - High-quality aesthetic
 */

const DashboardRedesigned = () => {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [stats, setStats] = useState(null);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionFeedback, setActionFeedback] = useState(null);
  const [selectedProject, setSelectedProject] = useState(null);

  // Fetch dashboard data
  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const [statsRes, projectsRes] = await Promise.all([
          axios.get(`${API}/dashboard/stats`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/projects?limit=5`, { headers: { Authorization: `Bearer ${token}` } }),
        ]);
        setStats(statsRes.data);
        setProjects(projectsRes.data.projects || []);
      } catch (err) {
        console.error('Failed to fetch dashboard:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, [token]);

  // Handle project creation
  const handleNewProject = () => {
    navigate('/projects/new');
  };

  // Handle project selection
  const handleSelectProject = (project) => {
    setSelectedProject(project);
    navigate(`/projects/${project.id}`);
  };

  // Handle share
  const handleShare = async (projectId) => {
    try {
      const { data } = await axios.post(
        `${API}/share/create`,
        { project_id: projectId, read_only: true },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const url = `${window.location.origin}${data.share_url}`;
      await navigator.clipboard.writeText(url);
      setActionFeedback({ type: 'success', msg: 'Share link copied!' });
      setTimeout(() => setActionFeedback(null), 3000);
    } catch (err) {
      setActionFeedback({ type: 'error', msg: 'Share failed' });
      setTimeout(() => setActionFeedback(null), 3000);
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
      projects={projects.slice(0, 3)}
      tasks={[]}
    />
  );

  // Main content
  const mainContent = (
    <div className="dashboard-main">
      {/* Welcome Header */}
      <div className="dashboard-header">
        <div className="dashboard-header-content">
          <h1>Welcome back, {user?.name || 'User'}</h1>
          <p>Continue building amazing projects with AI</p>
        </div>
        <button
          className="dashboard-new-project-btn"
          onClick={handleNewProject}
        >
          <Plus size={18} />
          <span>New Project</span>
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="dashboard-stats">
          <motion.div
            className="stat-card"
            whileHover={{ y: -2 }}
            transition={{ duration: 0.2 }}
          >
            <div className="stat-icon projects">
              <FolderOpen size={24} />
            </div>
            <div className="stat-content">
              <p className="stat-label">Projects</p>
              <p className="stat-value">{stats.total_projects || 0}</p>
            </div>
          </motion.div>

          <motion.div
            className="stat-card"
            whileHover={{ y: -2 }}
            transition={{ duration: 0.2 }}
          >
            <div className="stat-icon agents">
              <Bot size={24} />
            </div>
            <div className="stat-content">
              <p className="stat-label">Agents Used</p>
              <p className="stat-value">{stats.agents_used || 0}</p>
            </div>
          </motion.div>

          <motion.div
            className="stat-card"
            whileHover={{ y: -2 }}
            transition={{ duration: 0.2 }}
          >
            <div className="stat-icon deployments">
              <Zap size={24} />
            </div>
            <div className="stat-content">
              <p className="stat-label">Deployments</p>
              <p className="stat-value">{stats.total_deployments || 0}</p>
            </div>
          </motion.div>

          <motion.div
            className="stat-card"
            whileHover={{ y: -2 }}
            transition={{ duration: 0.2 }}
          >
            <div className="stat-icon uptime">
              <TrendingUp size={24} />
            </div>
            <div className="stat-content">
              <p className="stat-label">Uptime</p>
              <p className="stat-value">99.9%</p>
            </div>
          </motion.div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="dashboard-quick-actions">
        <h2>Quick Actions</h2>
        <div className="quick-actions-grid">
          <button className="quick-action-btn" onClick={handleNewProject}>
            <Plus size={20} />
            <span>New Project</span>
          </button>
          <button className="quick-action-btn" onClick={() => navigate('/agents')}>
            <Bot size={20} />
            <span>Browse Agents</span>
          </button>
          <button className="quick-action-btn" onClick={() => navigate('/templates')}>
            <Bookmark size={20} />
            <span>Templates</span>
          </button>
          <button className="quick-action-btn" onClick={() => navigate('/docs')}>
            <Upload size={20} />
            <span>Documentation</span>
          </button>
        </div>
      </div>

      {/* Recent Projects */}
      <div className="dashboard-recent-projects">
        <div className="section-header">
          <h2>Recent Projects</h2>
          <a href="/projects" className="view-all-link">
            View all <ArrowRight size={16} />
          </a>
        </div>

        {loading ? (
          <div className="loading">Loading projects...</div>
        ) : projects.length === 0 ? (
          <div className="empty-state">
            <FolderOpen size={48} />
            <h3>No projects yet</h3>
            <p>Create your first project to get started</p>
            <button className="empty-state-btn" onClick={handleNewProject}>
              Create Project
            </button>
          </div>
        ) : (
          <div className="projects-list">
            {projects.map((project) => (
              <motion.div
                key={project.id}
                className="project-card"
                whileHover={{ y: -2 }}
                onClick={() => handleSelectProject(project)}
              >
                <div className="project-card-header">
                  <h3>{project.name}</h3>
                  <div className="project-status">
                    {project.status === 'deployed' && (
                      <span className="status-badge deployed">Deployed</span>
                    )}
                    {project.status === 'building' && (
                      <span className="status-badge building">Building</span>
                    )}
                    {project.status === 'draft' && (
                      <span className="status-badge draft">Draft</span>
                    )}
                  </div>
                </div>

                <p className="project-description">{project.description || 'No description'}</p>

                <div className="project-meta">
                  <span className="meta-item">
                    <Clock size={14} />
                    {new Date(project.updated_at).toLocaleDateString()}
                  </span>
                  <span className="meta-item">
                    <Bot size={14} />
                    {project.agents_count || 0} agents
                  </span>
                </div>

                <div className="project-actions">
                  <button
                    className="action-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleShare(project.id);
                    }}
                    title="Share"
                  >
                    <Share2 size={16} />
                  </button>
                  <button
                    className="action-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/projects/${project.id}`);
                    }}
                    title="Open"
                  >
                    <ArrowRight size={16} />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  // Right panel content
  const rightPanelContent = (
    <RightPanel
      preview={
        <div className="preview-placeholder">
          <TrendingUp size={48} />
          <h3>Analytics</h3>
          <p>Select a project to view analytics</p>
        </div>
      }
      code={`// Your generated code appears here
// Select a project to view its code`}
      onShare={() => console.log('Share')}
      onDownload={() => console.log('Download')}
      onClose={() => console.log('Close')}
    />
  );

  return (
    <>
      {/* Feedback Toast */}
      {actionFeedback && (
        <motion.div
          className={`feedback-toast ${actionFeedback.type}`}
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
        >
          {actionFeedback.msg}
        </motion.div>
      )}

      {/* 3-Column Layout */}
      <Layout3Column
        sidebar={sidebarContent}
        main={mainContent}
        rightPanel={rightPanelContent}
      />
    </>
  );
};

export default DashboardRedesigned;
