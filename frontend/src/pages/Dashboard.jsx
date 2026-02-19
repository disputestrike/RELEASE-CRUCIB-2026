import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Plus, Zap, FolderOpen, Clock, CheckCircle, 
  AlertCircle, TrendingUp, Bot, ArrowRight, Play,
  Share2, Copy, Bookmark, Upload, X, Github
} from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';
import DeployButton from '../components/DeployButton';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

const Dashboard = () => {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [stats, setStats] = useState(null);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionFeedback, setActionFeedback] = useState(null);
  const [showImportModal, setShowImportModal] = useState(false);
  const [importSource, setImportSource] = useState('paste');
  const [importName, setImportName] = useState('');
  const [pasteFiles, setPasteFiles] = useState([{ path: '/App.js', code: '' }]);
  const [zipFile, setZipFile] = useState(null);
  const [gitUrl, setGitUrl] = useState('');
  const [importLoading, setImportLoading] = useState(false);
  const [importError, setImportError] = useState(null);

  const handleShare = async (e, projectId) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const { data } = await axios.post(`${API}/share/create`, { project_id: projectId, read_only: true }, { headers: { Authorization: `Bearer ${token}` } });
      const url = `${window.location.origin}${data.share_url}`;
      await navigator.clipboard.writeText(url);
      setActionFeedback({ type: 'share', msg: 'Share link copied!' });
      setTimeout(() => setActionFeedback(null), 3000);
    } catch (err) {
      setActionFeedback({ type: 'error', msg: err.response?.data?.detail || 'Share failed' });
      setTimeout(() => setActionFeedback(null), 3000);
    }
  };

  const handleDuplicate = async (e, projectId) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const { data } = await axios.post(`${API}/projects/${projectId}/duplicate`, {}, { headers: { Authorization: `Bearer ${token}` } });
      setProjects(prev => [data.project, ...prev.slice(0, 4)]);
      setActionFeedback({ type: 'duplicate', msg: 'Project duplicated!' });
      setTimeout(() => setActionFeedback(null), 3000);
    } catch (err) {
      setActionFeedback({ type: 'error', msg: err.response?.data?.detail || 'Duplicate failed' });
      setTimeout(() => setActionFeedback(null), 3000);
    }
  };

  const handleSaveAsTemplate = async (e, projectId) => {
    e.preventDefault();
    e.stopPropagation();
    const name = window.prompt('Template name:', 'My template');
    if (name == null) return;
    try {
      await axios.post(`${API}/projects/${projectId}/save-as-template`, { name: name || 'My template' }, { headers: { Authorization: `Bearer ${token}` } });
      setActionFeedback({ type: 'template', msg: 'Saved as template!' });
      setTimeout(() => setActionFeedback(null), 3000);
    } catch (err) {
      setActionFeedback({ type: 'error', msg: err.response?.data?.detail || 'Save failed' });
      setTimeout(() => setActionFeedback(null), 3000);
    }
  };

  const handleImportSubmit = async (e) => {
    e.preventDefault();
    setImportError(null);
    setImportLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      let body = { source: importSource, name: importName || undefined };
      if (importSource === 'paste') {
        const files = pasteFiles.filter((f) => (f.path || '').trim() && (f.code || '').trim());
        if (files.length === 0) {
          setImportError('Add at least one file with path and code.');
          setImportLoading(false);
          return;
        }
        body.files = files.map((f) => ({ path: (f.path || '').trim().replace(/^\/+/, '') || 'App.js', code: (f.code || '').trim() }));
      } else if (importSource === 'zip') {
        if (!zipFile) {
          setImportError('Choose a ZIP file to upload.');
          setImportLoading(false);
          return;
        }
        const buf = await zipFile.arrayBuffer();
        const base64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
        body.zip_base64 = base64;
      } else {
        const url = (gitUrl || '').trim();
        if (!url) {
          setImportError('Enter a GitHub repository URL.');
          setImportLoading(false);
          return;
        }
        body.git_url = url;
      }
      const { data } = await axios.post(`${API}/projects/import`, body, { headers });
      setShowImportModal(false);
      setImportName('');
      setPasteFiles([{ path: '/App.js', code: '' }]);
      setZipFile(null);
      setGitUrl('');
      navigate(`/app/workspace?projectId=${data.project_id}`);
    } catch (err) {
      setImportError(err.response?.data?.detail || err.message || 'Import failed');
    } finally {
      setImportLoading(false);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, projectsRes] = await Promise.all([
          axios.get(`${API}/dashboard/stats`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/projects`, { headers: { Authorization: `Bearer ${token}` } })
        ]);
        setStats(statsRes.data);
        setProjects(projectsRes.data.projects.slice(0, 5));
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-[#666666]">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  const statCards = [
    { label: 'Token Balance', value: stats?.token_balance?.toLocaleString() || 0, icon: Zap, color: 'blue', trend: '+5%' },
    { label: 'Total Projects', value: stats?.total_projects || 0, icon: FolderOpen, color: 'purple', trend: '+12%' },
    { label: 'Completed', value: stats?.completed_projects || 0, icon: CheckCircle, color: 'green', trend: '+8%' },
    { label: 'Running', value: stats?.running_projects || 0, icon: Clock, color: 'orange', trend: null }
  ];

  return (
    <div className="space-y-8 bg-[#FAF9F7] min-h-full" data-testid="dashboard">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold mb-2 text-gray-900">Welcome back, {user?.name?.split(' ')[0]}!</h1>
          <p className="text-gray-600">Here's what's happening with your projects.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowImportModal(true)}
            className="inline-flex items-center gap-2 px-5 py-3 bg-gray-100 hover:bg-gray-200 text-gray-800 rounded-lg font-medium transition border border-gray-300"
            data-testid="import-project-btn"
          >
            <Upload className="w-5 h-5" />
            Import project
          </button>
          <Link
            to="/app/projects/new"
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-500 hover:bg-blue-600 rounded-lg font-medium transition neon-blue"
            data-testid="new-project-btn"
          >
            <Plus className="w-5 h-5" />
            New Project
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className={`p-6 bg-white rounded-xl border border-gray-200 hover:border-${stat.color}-500/40 transition-all group shadow-sm`}
            data-testid={`stat-${stat.label.toLowerCase().replace(' ', '-')}`}
          >
            <div className="flex items-start justify-between mb-4">
              <div className={`w-12 h-12 bg-${stat.color}-500/10 rounded-lg flex items-center justify-center group-hover:bg-${stat.color}-500/20 transition`}>
                <stat.icon className={`w-6 h-6 text-${stat.color}-400`} />
              </div>
              {stat.trend && (
                <span className="flex items-center gap-1 text-sm text-green-400">
                  <TrendingUp className="w-4 h-4" />
                  {stat.trend}
                </span>
              )}
            </div>
            <p className="text-3xl font-bold mb-1">{stat.value}</p>
            <p className="text-gray-500 text-sm">{stat.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Charts & Activity */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Usage Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="lg:col-span-2 p-6 bg-white rounded-xl border border-gray-200 shadow-sm"
        >
          <h3 className="text-lg font-semibold mb-6 text-gray-900">Weekly Token Usage</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={stats?.weekly_data || []}>
                <defs>
                  <linearGradient id="tokenGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: '#6B7280', fontSize: 12 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#6B7280', fontSize: 12 }} tickFormatter={(v) => `${(v/1000).toFixed(0)}K`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#111', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                  labelStyle={{ color: '#fff' }}
                  formatter={(value) => [`${value.toLocaleString()} tokens`, 'Usage']}
                />
                <Area type="monotone" dataKey="tokens" stroke="#3B82F6" strokeWidth={2} fill="url(#tokenGradient)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="p-6 bg-white rounded-xl border border-gray-200 shadow-sm"
        >
          <h3 className="text-lg font-semibold mb-6 text-gray-900">Quick Actions</h3>
          <div className="space-y-3">
            {[
              { label: 'Create Website', icon: Plus, href: '/app/projects/new?type=website' },
              { label: 'Create API', icon: Bot, href: '/app/projects/new?type=api' },
              { label: 'Buy Tokens', icon: Zap, href: '/app/tokens' },
              { label: 'View Patterns', icon: FolderOpen, href: '/app/patterns' }
            ].map(action => (
              <Link
                key={action.label}
                to={action.href}
                className="flex items-center gap-3 p-4 bg-gray-50 hover:bg-gray-100 rounded-lg transition group"
              >
                <action.icon className="w-5 h-5 text-gray-500 group-hover:text-blue-600" />
                <span className="flex-1">{action.label}</span>
                <ArrowRight className="w-4 h-4 text-gray-500 group-hover:text-blue-600 transition" />
              </Link>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Recent Projects */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="p-6 bg-[#0a0a0a] rounded-xl border border-white/10"
      >
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold">Recent Projects</h3>
          <Link to="/app" className="text-sm text-blue-400 hover:text-blue-300">View all</Link>
        </div>
        
        {projects.length === 0 ? (
          <div className="text-center py-12">
            <FolderOpen className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-[#666666] mb-4">No projects yet</p>
            <Link
              to="/app/projects/new"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 rounded-lg font-medium transition"
            >
              <Plus className="w-4 h-4" />
              Create your first project
            </Link>
          </div>
        ) : (
          <>
            {actionFeedback && (
              <div className={`mb-4 px-4 py-2 rounded-lg text-sm ${actionFeedback.type === 'error' ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}>
                {actionFeedback.msg}
              </div>
            )}
            <div className="space-y-4">
            {projects.map(project => (
              <div
                key={project.id}
                className="flex items-center gap-4 p-4 bg-gray-50 hover:bg-gray-100 rounded-lg transition group"
                data-testid={`project-${project.id}`}
              >
                <Link to={`/app/projects/${project.id}`} className="flex items-center gap-4 flex-1 min-w-0">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
                    project.status === 'completed' ? 'bg-green-500/20' :
                    project.status === 'running' ? 'bg-blue-500/20 animate-pulse' :
                    project.status === 'failed' ? 'bg-red-500/20' :
                    'bg-gray-500/20'
                  }`}>
                    {project.status === 'completed' ? <CheckCircle className="w-5 h-5 text-green-400" /> :
                     project.status === 'running' ? <Play className="w-5 h-5 text-blue-400" /> :
                     project.status === 'failed' ? <AlertCircle className="w-5 h-5 text-red-400" /> :
                     <Clock className="w-5 h-5 text-[#666666]" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{project.name}</p>
                    <p className="text-sm text-gray-500">{project.project_type} • {project.tokens_used?.toLocaleString()} tokens used</p>
                  </div>
                  <div className="text-right shrink-0 flex items-center gap-2">
                    {project.status === 'completed' && project.quality_score?.overall_score != null && (
                      <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-700 text-slate-200 text-xs font-medium" title="Code quality score">
                        <span className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold bg-emerald-500/30 text-emerald-300">{Math.round(project.quality_score.overall_score)}</span>
                        Quality
                      </span>
                    )}
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      project.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                      project.status === 'running' ? 'bg-blue-500/20 text-blue-400' :
                      project.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                      'bg-gray-500/20 text-[#666666]'
                    }`}>
                      {project.status}
                    </span>
                  </div>
                </Link>
                <div className="flex items-center gap-1 shrink-0" onClick={e => e.preventDefault()}>
                  {project.status === 'completed' && (
                    <DeployButton projectId={project.id} variant="icon" onFeedback={(fb) => { setActionFeedback(fb); setTimeout(() => setActionFeedback(null), fb.type === 'error' ? 4000 : 3000); }} />
                  )}
                  <button type="button" onClick={(e) => handleShare(e, project.id)} className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-500/10 rounded-lg" title="Share"> <Share2 className="w-4 h-4" /> </button>
                  <button type="button" onClick={(e) => handleDuplicate(e, project.id)} className="p-2 text-gray-500 hover:text-green-600 hover:bg-green-500/10 rounded-lg" title="Duplicate"> <Copy className="w-4 h-4" /> </button>
                  <button type="button" onClick={(e) => handleSaveAsTemplate(e, project.id)} className="p-2 text-gray-500 hover:text-purple-600 hover:bg-purple-500/10 rounded-lg" title="Save as template"> <Bookmark className="w-4 h-4" /> </button>
                </div>
              </div>
            ))}
            </div>
          </>
        )}
      </motion.div>

      {/* Import project modal */}
      {showImportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => setShowImportModal(false)}>
          <div className="bg-[#111] border border-white/10 rounded-xl max-w-lg w-full max-h-[90vh] overflow-auto shadow-xl" onClick={e => e.stopPropagation()}>
            <div className="p-6">
              <h3 className="text-lg font-semibold text-[#1A1A1A] mb-2">Import project</h3>
              <p className="text-sm text-[#666666] mb-4">Bring your code from paste, a ZIP file, or a GitHub repo. We create a project and open it in the Workspace.</p>
              <form onSubmit={handleImportSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm text-[#666666] mb-1">Project name (optional)</label>
                  <input type="text" value={importName} onChange={e => setImportName(e.target.value)} placeholder="Imported project" className="w-full px-3 py-2 rounded bg-black/30 border border-white/10 text-[#1A1A1A]" />
                </div>
                <div>
                  <label className="block text-sm text-[#666666] mb-2">Source</label>
                  <div className="flex gap-2">
                    {['paste', 'zip', 'git'].map(s => (
                      <button key={s} type="button" onClick={() => setImportSource(s)} className={`px-3 py-1.5 rounded text-sm capitalize ${importSource === s ? 'bg-blue-600 text-[#1A1A1A]' : 'bg-white/10 text-[#666666] hover:text-[#1A1A1A]'}`}>{s === 'git' ? 'GitHub URL' : s}</button>
                    ))}
                  </div>
                </div>
                {importSource === 'paste' && (
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <label className="text-sm text-[#666666]">Files (path + code)</label>
                      <button type="button" onClick={() => setPasteFiles(prev => [...prev, { path: '', code: '' }])} className="text-xs text-blue-400 hover:text-blue-300">+ Add file</button>
                    </div>
                    {pasteFiles.map((f, i) => (
                      <div key={i} className="flex gap-2 items-start">
                        <input value={f.path} onChange={e => setPasteFiles(prev => prev.map((x, j) => j === i ? { ...x, path: e.target.value } : x))} placeholder="e.g. /App.js" className="flex-1 min-w-0 px-2 py-1.5 rounded bg-black/30 border border-white/10 text-[#1A1A1A] text-sm font-mono" />
                        <button type="button" onClick={() => setPasteFiles(prev => prev.filter((_, j) => j !== i))} className="p-1.5 text-[#666666] hover:text-red-400" title="Remove"><X className="w-4 h-4" /></button>
                        <textarea value={f.code} onChange={e => setPasteFiles(prev => prev.map((x, j) => j === i ? { ...x, code: e.target.value } : x))} placeholder="Code..." className="flex-[2] min-w-0 px-2 py-1.5 rounded bg-black/30 border border-white/10 text-[#1A1A1A] text-sm font-mono min-h-[60px]" rows={3} />
                      </div>
                    ))}
                  </div>
                )}
                {importSource === 'zip' && (
                  <div>
                    <label className="block text-sm text-[#666666] mb-1">ZIP file (max 10MB)</label>
                    <input type="file" accept=".zip" onChange={e => setZipFile(e.target.files?.[0] || null)} className="w-full text-sm text-[#666666] file:mr-2 file:py-2 file:px-3 file:rounded file:border-0 file:bg-white/10 file:text-[#1A1A1A]" />
                  </div>
                )}
                {importSource === 'git' && (
                  <div>
                    <label className="block text-sm text-[#666666] mb-1">GitHub repo URL</label>
                    <input type="url" value={gitUrl} onChange={e => setGitUrl(e.target.value)} placeholder="https://github.com/owner/repo" className="w-full px-3 py-2 rounded bg-black/30 border border-white/10 text-[#1A1A1A]" />
                  </div>
                )}
                {importError && <p className="text-sm text-red-400">{importError}</p>}
                <div className="flex gap-2 justify-end pt-2">
                  <button type="button" onClick={() => setShowImportModal(false)} className="px-4 py-2 rounded border border-white/20 text-gray-300 hover:bg-white/5">Cancel</button>
                  <button type="submit" disabled={importLoading} className="px-4 py-2 rounded bg-blue-600 text-[#1A1A1A] hover:bg-blue-500 disabled:opacity-50">{importLoading ? 'Importing…' : 'Import'}</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;