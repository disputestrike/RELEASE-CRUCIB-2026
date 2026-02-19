import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout, FileCode, Loader2 } from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';

export default function TemplatesGallery() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [creatingId, setCreatingId] = useState(null);

  useEffect(() => {
    axios.get(`${API}/templates`, token ? { headers: { Authorization: `Bearer ${token}` } } : {})
      .then((r) => setTemplates(r.data.templates || []))
      .catch(() => setTemplates([]));
  }, [token]);

  const createFromTemplate = (templateId) => {
    if (!token) {
      navigate('/auth');
      return;
    }
    setCreatingId(templateId);
    axios.post(`${API}/projects/from-template`, { template_id: templateId }, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        const files = r.data.files || {};
        const query = new URLSearchParams({ prompt: (r.data.template_id && templates.find(t => t.id === r.data.template_id)?.prompt) || '' });
        navigate(`/workspace?${query.toString()}`, { state: { initialFiles: files } });
      })
      .catch(() => setCreatingId(null))
      .finally(() => setCreatingId(null));
  };

  return (
    <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A] p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Templates</h1>
        <p className="text-zinc-400 mb-8">Start from a template to build faster.</p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {templates.map((t) => (
            <div
              key={t.id}
              className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/50 hover:border-zinc-700 transition"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-zinc-800">
                  <FileCode className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h2 className="font-semibold">{t.name}</h2>
                  <p className="text-sm text-zinc-500">{t.description}</p>
                </div>
              </div>
              <button
                onClick={() => createFromTemplate(t.id)}
                disabled={loading || creatingId !== null}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition disabled:opacity-50"
              >
                {creatingId === t.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Layout className="w-4 h-4" />}
                Use template
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
