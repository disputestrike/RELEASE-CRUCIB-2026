import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  FileText, Table, FileCode, Download, 
  Calendar, Plus, Rocket
} from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';
import DeployButton from '../components/DeployButton';

const ExportCenter = () => {
  const { token } = useAuth();
  const [exports, setExports] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [selectedProject, setSelectedProject] = useState('');
  const [selectedFormat, setSelectedFormat] = useState('pdf');
  const [deployProjectId, setDeployProjectId] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [exportsRes, projectsRes] = await Promise.all([
          axios.get(`${API}/exports`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/projects`, { headers: { Authorization: `Bearer ${token}` } })
        ]);
        setExports(exportsRes.data.exports);
        setProjects(projectsRes.data.projects.filter(p => p.status === 'completed'));
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  const handleCreateExport = async () => {
    if (!selectedProject) return;
    setCreating(true);
    try {
      const res = await axios.post(`${API}/exports`, {
        project_id: selectedProject,
        format: selectedFormat,
        include_images: true
      }, { headers: { Authorization: `Bearer ${token}` } });
      setExports([res.data.export, ...exports]);
      setSelectedProject('');
    } catch (e) {
      console.error(e);
    } finally {
      setCreating(false);
    }
  };

  const getFormatIcon = (format) => {
    switch (format) {
      case 'pdf': return FileText;
      case 'excel': return Table;
      case 'markdown': return FileCode;
      case 'all': return Download;
      default: return FileText;
    }
  };

  const getFormatColor = (format) => {
    switch (format) {
      case 'pdf': return 'red';
      case 'excel': return 'green';
      case 'markdown': return 'purple';
      case 'all': return 'blue';
      default: return 'gray';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-12 h-12 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8" data-testid="export-center">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Export Center</h1>
        <p className="text-[#666666]">Generate and download your project documentation in multiple formats.</p>
      </div>

      {/* Deploy: one-click deploy ZIP, Vercel, Netlify */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-6 bg-[#0a0a0a] rounded-xl border border-white/10"
      >
        <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
          <Rocket className="w-5 h-5 text-emerald-500" />
          Deploy to production
        </h3>
        <p className="text-sm text-gray-500 mb-4">Download a deploy-ready ZIP or open Vercel / Netlify to upload it.</p>
        <div className="flex flex-wrap items-center gap-4">
          <select
            value={deployProjectId}
            onChange={(e) => setDeployProjectId(e.target.value)}
            className="px-4 py-2.5 rounded-lg bg-white/5 border border-white/10 focus:border-emerald-500 outline-none min-w-[200px]"
          >
            <option value="">Select a completed project</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          {deployProjectId && (
            <DeployButton projectId={deployProjectId} variant="buttons" />
          )}
        </div>
      </motion.div>

      {/* Create Export */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-6 bg-[#0a0a0a] rounded-xl border border-white/10"
      >
        <h3 className="text-lg font-semibold mb-6">Create New Export</h3>
        <div className="grid md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Project</label>
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg focus:border-blue-500 outline-none"
              data-testid="export-project-select"
            >
              <option value="">Select a project</option>
              {projects.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Format</label>
            <select
              value={selectedFormat}
              onChange={(e) => setSelectedFormat(e.target.value)}
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg focus:border-blue-500 outline-none"
              data-testid="export-format-select"
            >
              <option value="pdf">PDF Report</option>
              <option value="excel">Excel Spreadsheet</option>
              <option value="markdown">Markdown Documentation</option>
              <option value="all">All Formats (ZIP)</option>
            </select>
          </div>
          
          <div className="flex items-end">
            <button
              onClick={handleCreateExport}
              disabled={!selectedProject || creating}
              className="w-full py-3 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg font-medium transition flex items-center justify-center gap-2"
              data-testid="create-export-btn"
            >
              {creating ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <Plus className="w-5 h-5" />
                  Generate Export
                </>
              )}
            </button>
          </div>
        </div>
      </motion.div>

      {/* Format Cards */}
      <div className="grid md:grid-cols-4 gap-4">
        {[
          { format: 'pdf', name: 'PDF', desc: 'Formatted reports with images', icon: FileText },
          { format: 'excel', name: 'Excel', desc: 'Data with formulas & charts', icon: Table },
          { format: 'markdown', name: 'Markdown', desc: 'Clean documentation', icon: FileCode },
          { format: 'all', name: 'All Formats', desc: 'Complete package (ZIP)', icon: Download }
        ].map((item, i) => (
          <motion.div
            key={item.format}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className={`p-4 rounded-xl border transition-all cursor-pointer ${
              selectedFormat === item.format
                ? `bg-${getFormatColor(item.format)}-500/10 border-${getFormatColor(item.format)}-500/50`
                : 'bg-[#0a0a0a] border-white/10 hover:border-white/20'
            }`}
            onClick={() => setSelectedFormat(item.format)}
          >
            <item.icon className={`w-8 h-8 mb-3 text-${getFormatColor(item.format)}-400`} />
            <h4 className="font-medium">{item.name}</h4>
            <p className="text-sm text-gray-500">{item.desc}</p>
          </motion.div>
        ))}
      </div>

      {/* Exports List */}
      <div className="p-6 bg-[#0a0a0a] rounded-xl border border-white/10">
        <h3 className="text-lg font-semibold mb-6">Recent Exports</h3>
        
        {exports.length === 0 ? (
          <div className="text-center py-12">
            <Download className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-[#666666]">No exports yet. Create your first export above.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {exports.map(exp => {
              const FormatIcon = getFormatIcon(exp.format);
              const project = projects.find(p => p.id === exp.project_id);
              return (
                <div
                  key={exp.id}
                  className="flex items-center justify-between p-4 bg-white/5 rounded-lg hover:bg-white/10 transition"
                  data-testid={`export-${exp.id}`}
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center bg-${getFormatColor(exp.format)}-500/20`}>
                      <FormatIcon className={`w-5 h-5 text-${getFormatColor(exp.format)}-400`} />
                    </div>
                    <div>
                      <p className="font-medium">{project?.name || 'Unknown Project'}</p>
                      <p className="text-sm text-gray-500 flex items-center gap-2">
                        <span className="uppercase">{exp.format}</span>
                        <span>•</span>
                        <Calendar className="w-3 h-3" />
                        {new Date(exp.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      exp.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                      exp.status === 'processing' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-gray-500/20 text-[#666666]'
                    }`}>
                      {exp.status}
                    </span>
                    <a
                      href={exp.download_url}
                      className="p-2 hover:bg-white/10 rounded-lg transition"
                      title="Download"
                    >
                      <Download className="w-5 h-5" />
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default ExportCenter;