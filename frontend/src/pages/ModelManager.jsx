import { useState, useEffect } from 'react';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import axios from 'axios';
import { logApiError } from '../utils/apiError';
import { Cpu, Zap, CheckCircle, AlertCircle, RefreshCw, Info } from 'lucide-react';

const MODELS = [
  {
    id: 'claude-sonnet',
    name: 'Claude Sonnet',
    provider: 'Anthropic',
    speed: 'Fast',
    quality: 'Highest',
    best_for: 'Complex builds, architecture, security',
    color: 'bg-purple-50 border-purple-200 text-purple-800',
    badge: 'bg-purple-100 text-purple-700',
  },
  {
    id: 'claude-haiku',
    name: 'Claude Haiku',
    provider: 'Anthropic',
    speed: 'Fastest',
    quality: 'High',
    best_for: 'Quick edits, simple builds, iterations',
    color: 'bg-blue-50 border-blue-200 text-blue-800',
    badge: 'bg-blue-100 text-blue-700',
  },
  {
    id: 'llama-70b',
    name: 'Llama 70B',
    provider: 'Together AI',
    speed: 'Fast',
    quality: 'High',
    best_for: 'Open source, cost efficient, general builds',
    color: 'bg-green-50 border-green-200 text-green-800',
    badge: 'bg-green-100 text-green-700',
  },
  {
    id: 'cerebras-llama',
    name: 'Cerebras Llama',
    provider: 'Cerebras',
    speed: 'Ultra Fast',
    quality: 'Good',
    best_for: 'Simple tasks, formatting, quick fixes',
    color: 'bg-neutral-100 border-neutral-200 text-neutral-800',
    badge: 'bg-neutral-200 text-neutral-700',
  },
];

const ROUTING_MODES = [
  { id: 'auto', label: 'Auto (recommended)', description: 'CrucibAI intelligently routes each agent to the best model based on task complexity and your credit tier.' },
  { id: 'quality', label: 'Max quality', description: 'Always use Claude Sonnet. Slower but best results. Uses more credits.' },
  { id: 'speed', label: 'Max speed', description: 'Always use Cerebras for simple tasks, Claude Haiku for complex. Fastest builds.' },
  { id: 'economy', label: 'Economy', description: 'Prefer open source models. Lowest cost per build.' },
];

export default function ModelManager() {
  const { token } = useAuth();
  const [routingMode, setRoutingMode] = useState('auto');
  const [saved, setSaved] = useState(false);
  const [usage, setUsage] = useState(null);
  const [loadingUsage, setLoadingUsage] = useState(true);

  useEffect(() => {
    if (!token) return;
    setLoadingUsage(true);
    axios.get(`${API}/tokens/usage`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => setUsage(r.data))
      .catch(e => logApiError('ModelManager usage', e))
      .finally(() => setLoadingUsage(false));
  }, [token]);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900 mb-1">Model Manager</h1>
        <p className="text-gray-500 text-sm">Control which AI models power your builds. CrucibAI routes across multiple models for speed, quality, and cost.</p>
      </div>

      {/* Routing Mode */}
      <div className="mb-8">
        <h2 className="text-sm font-medium text-gray-700 mb-3 uppercase tracking-wide">Routing mode</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {ROUTING_MODES.map(mode => (
            <button
              key={mode.id}
              onClick={() => setRoutingMode(mode.id)}
              className={`text-left p-4 rounded-xl border transition ${routingMode === mode.id ? 'border-black bg-gray-50' : 'border-gray-200 hover:border-gray-300 bg-white'}`}
            >
              <div className="flex items-center gap-2 mb-1">
                {routingMode === mode.id ? <CheckCircle className="w-4 h-4 text-green-500" /> : <div className="w-4 h-4 rounded-full border-2 border-gray-300" />}
                <span className="font-medium text-gray-900 text-sm">{mode.label}</span>
              </div>
              <p className="text-xs text-gray-500 ml-6">{mode.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Available Models */}
      <div className="mb-8">
        <h2 className="text-sm font-medium text-gray-700 mb-3 uppercase tracking-wide">Available models</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {MODELS.map(model => (
            <div key={model.id} className={`p-4 rounded-xl border ${model.color}`}>
              <div className="flex items-start justify-between mb-2">
                <div>
                  <p className="font-semibold text-sm">{model.name}</p>
                  <p className="text-xs opacity-70">{model.provider}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${model.badge}`}>{model.speed}</span>
              </div>
              <p className="text-xs opacity-80">Best for: {model.best_for}</p>
              <p className="text-xs mt-1 opacity-70">Quality: {model.quality}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Usage Stats */}
      <div className="mb-8">
        <h2 className="text-sm font-medium text-gray-700 mb-3 uppercase tracking-wide">Model usage this month</h2>
        <div className="p-4 rounded-xl border border-gray-200 bg-white">
          {loadingUsage ? (
            <div className="flex items-center gap-2 text-gray-400 text-sm"><RefreshCw className="w-4 h-4 animate-spin" /> Loading usage...</div>
          ) : usage ? (
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-gray-500">Total tokens used</p>
                <p className="text-lg font-semibold text-gray-900">{(usage.tokens_used || 0).toLocaleString()}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Credits remaining</p>
                <p className="text-lg font-semibold text-gray-900">{(usage.credits_remaining || 0).toLocaleString()}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Builds this month</p>
                <p className="text-lg font-semibold text-gray-900">{usage.builds_count || 0}</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-gray-400 text-sm"><Info className="w-4 h-4" /> Usage data unavailable</div>
          )}
        </div>
      </div>

      {/* How routing works */}
      <div className="mb-8 p-4 rounded-xl border border-blue-100 bg-blue-50">
        <div className="flex items-start gap-3">
          <Cpu className="w-5 h-5 text-blue-600 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-blue-900 mb-1">How CrucibAI routing works</p>
            <p className="text-xs text-blue-700 leading-relaxed">
              Each agent in CrucibAI&apos;s swarm is classified by task complexity: Critical (architecture, security, database design) → Claude Sonnet. Moderate (component generation, API integration) → Claude Haiku or Llama 70B. Simple (formatting, style changes, comments) → Cerebras Llama. This hybrid approach gives you Claude-quality output on the decisions that matter, at 40-60% lower cost than using Claude for everything.
            </p>
          </div>
        </div>
      </div>

      <button
        onClick={handleSave}
        className="flex items-center gap-2 px-6 py-2.5 bg-black text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition"
      >
        {saved ? <><CheckCircle className="w-4 h-4" /> Saved</> : <><Zap className="w-4 h-4" /> Save routing preference</>}
      </button>
    </div>
  );
}
