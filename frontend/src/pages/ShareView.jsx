import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ExternalLink, Lock, AlertCircle } from 'lucide-react';
import { API } from '../App';
import axios from 'axios';

export default function ShareView() {
  const { token } = useParams();
  const [project, setProject] = useState(null);
  const [readOnly, setReadOnly] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios.get(`${API}/share/${token}`)
      .then((r) => {
        setProject(r.data.project);
        setReadOnly(r.data.read_only !== false);
      })
      .catch((e) => {
        setError(e.response?.data?.detail || e.message);
      })
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAFAF8] flex items-center justify-center">
        <div className="w-10 h-10 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A] flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
          <h1 className="text-xl font-semibold mb-2">Share not found</h1>
          <p className="text-zinc-400 mb-6">{error || 'This link may have expired.'}</p>
          <Link to="/" className="text-[#1A1A1A] hover:text-#d0d0d0">Back to CrucibAI</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A] p-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-2 text-zinc-400 mb-2">
          {readOnly && <Lock className="w-4 h-4" />}
          <span>Shared project</span>
        </div>
        <h1 className="text-2xl font-bold mb-2">{project.name}</h1>
        {project.description && <p className="text-zinc-400 mb-6">{project.description}</p>}
        <div className="flex flex-wrap gap-2 text-sm">
          <span className="px-3 py-1 bg-zinc-800 rounded-full text-zinc-300">{project.project_type || 'app'}</span>
          {project.status && <span className="px-3 py-1 bg-zinc-800 rounded-full text-zinc-300">{project.status}</span>}
          {project.live_url && (
            <a href={project.live_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 px-3 py-1 bg-gray-200 text-[#1A1A1A] rounded-full hover:bg-gray-200/30">
              <ExternalLink className="w-3 h-3" /> Open live app
            </a>
          )}
        </div>
        <p className="mt-8 text-zinc-500 text-sm">This is a read-only share. Sign in to edit or duplicate.</p>
        <Link to="/auth" className="inline-block mt-4 text-[#1A1A1A] hover:text-#d0d0d0">Sign in to CrucibAI</Link>
      </div>
    </div>
  );
}
