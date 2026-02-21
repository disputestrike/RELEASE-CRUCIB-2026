import { useState, useEffect } from 'react';
import { Key, Plus, Trash2 } from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';

export default function EnvPanel() {
  const { token } = useAuth();
  const [env, setEnv] = useState({});
  const [newKey, setNewKey] = useState('');
  const [newVal, setNewVal] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!token) return;
    axios.get(`${API}/workspace/env`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => setEnv(r.data.env || {}))
      .catch(() => setEnv({}));
  }, [token]);

  const addVar = () => {
    if (!newKey.trim() || !token) return;
    const next = { ...env, [newKey.trim()]: newVal.trim() };
    setEnv(next);
    setNewKey('');
    setNewVal('');
    setSaving(true);
    axios.post(`${API}/workspace/env`, { env: next }, { headers: { Authorization: `Bearer ${token}` } })
      .then(() => {})
      .finally(() => setSaving(false));
  };

  const removeVar = (key) => {
    const next = { ...env };
    delete next[key];
    setEnv(next);
    setSaving(true);
    axios.post(`${API}/workspace/env`, { env: next }, { headers: { Authorization: `Bearer ${token}` } })
      .then(() => {})
      .finally(() => setSaving(false));
  };

  if (!token) {
    return (
      <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A] flex items-center justify-center p-4">
        <p className="text-gray-400">Sign in to manage environment variables.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A] p-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-3 rounded-xl bg-gray-800">
            <Key className="w-8 h-8 text-gray-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Workspace env</h1>
            <p className="text-gray-400">Variables available to your builds (e.g. API keys)</p>
          </div>
        </div>
        <div className="space-y-3 mb-6">
          {Object.entries(env).map(([k, v]) => (
            <div key={k} className="flex items-center gap-3 p-3 rounded-lg bg-gray-900 border border-gray-800">
              <span className="font-mono text-sm text-gray-300">{k}</span>
              <span className="flex-1 truncate text-gray-500 text-sm">{v ? '••••••' : '(empty)'}</span>
              <button onClick={() => removeVar(k)} className="p-1.5 text-gray-500 hover:text-gray-400">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            placeholder="KEY"
            className="flex-1 px-3 py-2 rounded-lg bg-gray-900 border border-gray-800 text-[#1A1A1A] placeholder-zinc-500"
          />
          <input
            value={newVal}
            onChange={(e) => setNewVal(e.target.value)}
            placeholder="value"
            className="flex-1 px-3 py-2 rounded-lg bg-gray-900 border border-gray-800 text-[#1A1A1A] placeholder-zinc-500"
          />
          <button
            onClick={addVar}
            disabled={!newKey.trim() || saving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-200/20 text-gray-500 hover:bg-gray-200/30 disabled:opacity-50"
          >
            <Plus className="w-4 h-4" /> Add
          </button>
        </div>
      </div>
    </div>
  );
}
