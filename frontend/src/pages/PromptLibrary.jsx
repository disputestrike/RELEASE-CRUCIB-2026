import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Plus, Copy, Check, Save } from 'lucide-react';
import { useAuth } from '../App';
import { API_BASE as API } from '../apiBase';
import axios from 'axios';
import { logApiError } from '../utils/apiError';
import { withWorkspaceHandoffNonce } from '../utils/workspaceHandoff';

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
      .catch((e) => logApiError('PromptLibrary', e));
    if (token) {
      axios.get(`${API}/prompts/saved`, { headers: { Authorization: `Bearer ${token}` } })
        .then((r) => setSaved(r.data.prompts || []))
        .catch((e) => logApiError('PromptLibrary', e));
      axios.get(`${API}/prompts/recent`, { headers: { Authorization: `Bearer ${token}` } })
        .then((r) => setRecent(r.data.prompts || []))
        .catch((e) => logApiError('PromptLibrary', e));
    }
  }, [token]);

  const goToPrompt = (prompt) => {
    navigate('/app/workspace', { state: withWorkspaceHandoffNonce({ initialPrompt: prompt }) });
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
        <p className="text-[#666666] mb-6">Templates and your saved prompts.</p>
        {token && (
          <div className="p-4 rounded-xl border border-black/10 bg-[#F5F5F4] mb-6">
            <h3 className="text-sm font-medium text-[#1A1A1A] mb-3">Save new prompt</h3>
            <input type="text" value={saveName} onChange={(e) => setSaveName(e.target.value)} placeholder="Name" className="w-full mb-2 px-3 py-2 rounded-lg bg-white border border-black/10 text-[#1A1A1A] placeholder-[#666666] text-sm" />
            <textarea value={savePrompt} onChange={(e) => setSavePrompt(e.target.value)} placeholder="Prompt text..." rows={2} className="w-full mb-2 px-3 py-2 rounded-lg bg-white border border-black/10 text-[#1A1A1A] placeholder-[#666666] text-sm resize-none" />
            <button type="button" onClick={handleSavePrompt} disabled={saving || !saveName.trim() || !savePrompt.trim()} className="flex items-center gap-2 px-4 py-2 bg-[#1A1A1A] hover:bg-[#333] text-white rounded-lg text-sm font-medium disabled:opacity-50">
              {saveDone ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />} {saving ? 'Saving...' : saveDone ? 'Saved!' : 'Save prompt'}
            </button>
          </div>
        )}
        <div className="flex gap-2 border-b border-black/10 pb-4 mb-6">
          {['templates', 'saved', 'recent'].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-lg text-sm capitalize ${tab === t ? 'bg-[#F3F1ED] text-[#1A1A1A]' : 'text-[#666666] hover:text-[#1A1A1A]'}`}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="space-y-4">
          {tab === 'templates' && templates.map((t) => (
            <div key={t.id} className="p-4 rounded-xl border border-black/10 bg-[#F5F5F4]">
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="font-medium">{t.name}</span>
                <div className="flex gap-2">
                  <button onClick={() => copyPrompt(t.prompt, t.id)} className="p-1.5 text-[#666666] hover:text-[#1A1A1A]">
                    {copiedId === t.id ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </button>
                  <button onClick={() => goToPrompt(t.prompt)} className="flex items-center gap-1 text-sm text-[#1A1A1A] hover:text-[#333]">
                    <Plus className="w-4 h-4" /> Use
                  </button>
                </div>
              </div>
              <p className="text-sm text-[#666666] line-clamp-2">{t.prompt}</p>
            </div>
          ))}
          {tab === 'saved' && (saved.length === 0 ? <p className="text-[#666666]">No saved prompts yet.</p> : saved.map((p) => (
            <div key={p.id} className="p-4 rounded-xl border border-black/10 bg-[#F5F5F4]">
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="font-medium">{p.name}</span>
                <div className="flex gap-2">
                  <button onClick={() => copyPrompt(p.prompt, p.id)} className="p-1.5 text-[#666666] hover:text-[#1A1A1A]">
                    {copiedId === p.id ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </button>
                  <button onClick={() => goToPrompt(p.prompt)} className="text-sm text-[#1A1A1A] hover:text-[#333]">Use</button>
                </div>
              </div>
              <p className="text-sm text-[#666666] line-clamp-2">{p.prompt}</p>
            </div>
          )))}
          {tab === 'recent' && (recent.length === 0 ? <p className="text-[#666666]">No recent prompts.</p> : recent.map((p, i) => (
            <div key={i} className="p-4 rounded-xl border border-black/10 bg-[#F5F5F4]">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm text-[#1A1A1A] line-clamp-2 flex-1">{p.prompt}</p>
                <button onClick={() => goToPrompt(p.prompt)} className="text-sm text-[#1A1A1A] hover:text-[#333] shrink-0">Use</button>
              </div>
            </div>
          )))}
        </div>
      </div>
    </div>
  );
}
