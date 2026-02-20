import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Plus, Copy, Check, Save } from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';

export default function PromptLibrary() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [templates, setTemplates] = useState([]);
  const [saved, setSaved] = useState([]);
  const [recent, setRecent] = useState([]);
  const [tab, setTab] = useState('templates');
  const [copiedId, setCopiedId] = useState(null);
  const [saveName, setSaveName] = useState('');
  const [savePrompt, setSavePrompt] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveDone, setSaveDone] = useState(false);

  const handleSavePrompt = async () => {
    if (!saveName.trim() || !savePrompt.trim() || !token) return;
    setSaving(true);
    setSaveDone(false);
    try {
      await axios.post(`${API}/prompts/save`, { name: saveName.trim(), prompt: savePrompt.trim(), category: 'general' }, { headers: { Authorization: `Bearer ${token}` } });
      setSaveName('');
      setSavePrompt('');
      setSaveDone(true);
      const r = await axios.get(`${API}/prompts/saved`, { headers: { Authorization: `Bearer ${token}` } });
      setSaved(r.data.prompts || []);
      setTimeout(() => setSaveDone(false), 2000);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    axios.get(`${API}/prompts/templates`, token ? { headers: { Authorization: `Bearer ${token}` } } : {})
      .then((r) => setTemplates(r.data.templates || []))
      .catch(() => {});
    if (token) {
      axios.get(`${API}/prompts/saved`, { headers: { Authorization: `Bearer ${token}` } })
        .then((r) => setSaved(r.data.prompts || []))
        .catch(() => {});
      axios.get(`${API}/prompts/recent`, { headers: { Authorization: `Bearer ${token}` } })
        .then((r) => setRecent(r.data.prompts || []))
        .catch(() => {});
    }
  }, [token]);

  const goToPrompt = (prompt) => {
    navigate('/workspace', { state: { initialPrompt: prompt } });
  };

  const copyPrompt = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A] p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-2">Prompt Library</h1>
        <p className="text-gray-400 mb-6">Templates and your saved prompts.</p>
        {token && (
          <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/50 mb-6">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Save new prompt</h3>
            <input type="text" value={saveName} onChange={(e) => setSaveName(e.target.value)} placeholder="Name" className="w-full mb-2 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-[#1A1A1A] placeholder-zinc-500 text-sm" />
            <textarea value={savePrompt} onChange={(e) => setSavePrompt(e.target.value)} placeholder="Prompt text..." rows={2} className="w-full mb-2 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-[#1A1A1A] placeholder-zinc-500 text-sm resize-none" />
            <button type="button" onClick={handleSavePrompt} disabled={saving || !saveName.trim() || !savePrompt.trim()} className="flex items-center gap-2 px-4 py-2 bg-black hover:bg-gray-200 rounded-lg text-sm font-medium disabled:opacity-50">
              {saveDone ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />} {saving ? 'Saving...' : saveDone ? 'Saved!' : 'Save prompt'}
            </button>
          </div>
        )}
        <div className="flex gap-2 border-b border-gray-800 pb-4 mb-6">
          {['templates', 'saved', 'recent'].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-lg text-sm capitalize ${tab === t ? 'bg-gray-800 text-[#1A1A1A]' : 'text-gray-400 hover:text-[#1A1A1A]'}`}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="space-y-4">
          {tab === 'templates' && templates.map((t) => (
            <div key={t.id} className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="font-medium">{t.name}</span>
                <div className="flex gap-2">
                  <button onClick={() => copyPrompt(t.prompt, t.id)} className="p-1.5 text-gray-400 hover:text-[#1A1A1A]">
                    {copiedId === t.id ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </button>
                  <button onClick={() => goToPrompt(t.prompt)} className="flex items-center gap-1 text-sm text-#c0c0c0 hover:text-#d0d0d0">
                    <Plus className="w-4 h-4" /> Use
                  </button>
                </div>
              </div>
              <p className="text-sm text-gray-400 line-clamp-2">{t.prompt}</p>
            </div>
          ))}
          {tab === 'saved' && (saved.length === 0 ? <p className="text-gray-500">No saved prompts yet.</p> : saved.map((p) => (
            <div key={p.id} className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="font-medium">{p.name}</span>
                <div className="flex gap-2">
                  <button onClick={() => copyPrompt(p.prompt, p.id)} className="p-1.5 text-gray-400 hover:text-[#1A1A1A]">
                    {copiedId === p.id ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </button>
                  <button onClick={() => goToPrompt(p.prompt)} className="text-sm text-#c0c0c0 hover:text-#d0d0d0">Use</button>
                </div>
              </div>
              <p className="text-sm text-gray-400 line-clamp-2">{p.prompt}</p>
            </div>
          )))}
          {tab === 'recent' && (recent.length === 0 ? <p className="text-gray-500">No recent prompts.</p> : recent.map((p, i) => (
            <div key={i} className="p-4 rounded-xl border border-gray-800 bg-gray-900/50">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm text-gray-300 line-clamp-2 flex-1">{p.prompt}</p>
                <button onClick={() => goToPrompt(p.prompt)} className="text-sm text-#c0c0c0 hover:text-#d0d0d0 shrink-0">Use</button>
              </div>
            </div>
          )))}
        </div>
      </div>
    </div>
  );
}
