import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileCode, Loader2, GitFork } from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';
import QualityScore from '../components/QualityScore';

export default function ExamplesGallery() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [examples, setExamples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [forking, setForking] = useState(null);

  useEffect(() => {
    axios.get(`${API}/examples`, token ? { headers: { Authorization: `Bearer ${token}` } } : {})
      .then((r) => setExamples(r.data.examples || []))
      .catch(() => setExamples([]))
      .finally(() => setLoading(false));
  }, [token]);

  const forkExample = (name) => {
    if (!token) {
      navigate('/auth');
      return;
    }
    setForking(name);
    axios.post(`${API}/examples/${encodeURIComponent(name)}/fork`, {}, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        const project = r.data.project;
        if (project?.id) navigate(`/app/projects/${project.id}`);
      })
      .catch(() => setForking(null))
      .finally(() => setForking(null));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-orange-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A] p-6">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Generated App Examples</h1>
        <p className="text-zinc-400 mb-8">Proof of what CrucibAI generates. Fork any example to start from its code.</p>

        <div className="grid gap-4 sm:grid-cols-2">
          {examples.map((ex) => (
            <div
              key={ex.name}
              className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/50 hover:border-zinc-700 transition cursor-pointer"
              onClick={() => setSelected(selected?.name === ex.name ? null : ex)}
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-zinc-800">
                  <FileCode className="w-5 h-5 text-orange-400" />
                </div>
                <div>
                  <h2 className="font-semibold">{ex.name}</h2>
                  <p className="text-sm text-zinc-500 line-clamp-1">{ex.prompt?.slice(0, 60)}...</p>
                </div>
              </div>
              {ex.quality_metrics && <QualityScore score={ex.quality_metrics} />}
              <button
                onClick={(e) => { e.stopPropagation(); forkExample(ex.name); }}
                disabled={forking !== null}
                className="mt-3 w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-orange-500/20 text-orange-400 hover:bg-orange-500/30 transition disabled:opacity-50"
              >
                {forking === ex.name ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitFork className="w-4 h-4" />}
                Fork & open in workspace
              </button>
            </div>
          ))}
        </div>

        {examples.length === 0 && (
          <p className="text-zinc-500">No examples yet. Run a build to see generated apps here.</p>
        )}

        {selected && (
          <div className="fixed inset-0 bg-zinc-900/80 flex items-center justify-center z-50 p-4" onClick={() => setSelected(null)}>
            <div className="bg-zinc-900 rounded-xl border border-zinc-700 max-w-2xl w-full max-h-[80vh] overflow-auto p-6" onClick={(e) => e.stopPropagation()}>
              <h2 className="text-xl font-bold mb-2">{selected.name}</h2>
              <p className="text-zinc-400 text-sm mb-4">{selected.prompt}</p>
              {selected.quality_metrics && <QualityScore score={selected.quality_metrics} />}
              {selected.generated_code?.frontend && (
                <pre className="mt-4 p-3 rounded bg-zinc-800 text-xs overflow-x-auto whitespace-pre-wrap break-words max-h-48 overflow-y-auto">
                  {selected.generated_code.frontend.slice(0, 800)}...
                </pre>
              )}
              <button onClick={() => setSelected(null)} className="mt-4 px-4 py-2 rounded bg-zinc-700 hover:bg-zinc-600">Close</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
