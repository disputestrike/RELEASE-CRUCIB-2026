import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../App';
import { API_BASE as API } from '../apiBase';
import axios from 'axios';
import { logApiError } from '../utils/apiError';
import { Zap, Plus, ChevronRight, Copy, Check, Pencil, Trash2 } from 'lucide-react';

const getToken = () => localStorage.getItem('token');

function formatSchedule(agent) {
  const tc = agent?.trigger_config;
  if (!tc) return agent?.trigger_type || '—';
  if (tc.cron_expression) {
    const parts = tc.cron_expression.trim().split(/\s+/);
    if (parts.length >= 5) {
      const [min, hour, dom, month, dow] = parts;
      if (min === '0' && hour !== '*' && dom === '*' && month === '*' && dow === '*') return `every day at ${hour.padStart(2, '0')}:00`;
      if (min !== '*' && hour === '*' && dom === '*' && month === '*' && dow === '*') return `every hour at :${min}`;
      if (dow !== '*' && dom === '*' && month === '*') {
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const dayNames = dow.split(',').map(d => days[parseInt(d, 10)]).filter(Boolean).join(', ') || dow;
        return `every ${dayNames}`;
      }
    }
    return tc.cron_expression;
  }
  return agent?.trigger_type || '—';
}

export default function AgentsPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const { user } = useAuth();
  const [agents, setAgents] = useState([]);
  const [agent, setAgent] = useState(null);
  const [runs, setRuns] = useState([]);
  const [logRunId, setLogRunId] = useState(null);
  const [logLines, setLogLines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [rotateModal, setRotateModal] = useState(null);

  const refetchAgents = () => {
    setLoading(true);
    axios.get(`${API}/agents`, { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => setAgents(r.data.items || []))
      .catch((e) => { logApiError('AgentsPage list', e); setAgents([]); })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (id) return;
    const headers = { Authorization: `Bearer ${getToken()}` };
    axios.get(`${API}/agents`, { headers })
      .then((r) => setAgents(r.data.items || []))
      .catch((e) => { logApiError('AgentsPage list', e); setAgents([]); })
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!id) return;
    const headers = { Authorization: `Bearer ${getToken()}` };
    axios.get(`${API}/agents/${id}`, { headers })
      .then((r) => setAgent(r.data))
      .catch((e) => { logApiError('AgentsPage detail', e); setAgent(null); });
    axios.get(`${API}/agents/${id}/runs`, { headers })
      .then((r) => setRuns(r.data.items || []))
      .catch((e) => { logApiError('AgentsPage runs', e); setRuns([]); });
  }, [id]);

  useEffect(() => {
    if (!logRunId) { setLogLines([]); return; }
    const headers = { Authorization: `Bearer ${getToken()}` };
    axios.get(`${API}/agents/runs/${logRunId}/logs`, { headers })
      .then((r) => setLogLines(r.data.log_lines || []))
      .catch((e) => { logApiError('AgentsPage logs', e); setLogLines([]); });
  }, [logRunId]);

  const copyWebhook = (url) => {
    if (!url) return;
    navigator.clipboard.writeText(url);
    setCopied(true);
  };
  const rotateWebhookSecret = () => {
    if (!id || !agent?.webhook_url) return;
    setLoading(true);
    axios.post(`${API}/agents/${id}/webhook-rotate-secret`, {}, { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => {
        setRotateModal({ secret: r.data.webhook_secret, url: r.data.webhook_url });
        setAgent((a) => a ? { ...a, webhook_url: r.data.webhook_url } : null);
      })
      .catch((e) => logApiError('AgentsPage', e))
      .finally(() => setLoading(false));
  };
  const closeRotateModal = () => {
    setRotateModal(null);
  };
  const copyWebhookModal = (url) => {
    if (!url) return;
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!user) return null;
  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-[#1A1A1A] flex items-center gap-2">
          <Zap className="w-7 h-7 text-[#666666]" />
          Agents & Automations
        </h1>
        <button
          onClick={() => navigate('/app', { state: { focusPrompt: true } })}
          className="flex items-center gap-2 px-4 py-2 bg-[#1A1A1A] hover:bg-[#333] text-white rounded-lg"
        >
          <Plus className="w-5 h-5" /> New Agent
        </button>
      </div>

      {loading ? (
        <div className="text-[#666666]">Loading agents...</div>
      ) : !id ? (
        <div className="space-y-4">
          {agents.length === 0 ? (
            <p className="text-[#666666]">No agents yet. Go to Home and describe what you want your agent to do.</p>
          ) : (
            agents.map((a) => (
              <div
                key={a.id}
                className="flex items-center justify-between p-4 rounded-lg bg-white/5 border border-white/10 hover:border-[#1A1A1A]/20"
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <Zap className="w-5 h-5 text-[#666666] flex-shrink-0" />
                  <div className="min-w-0">
                    <div className="font-medium text-[#1A1A1A]">{a.name}</div>
                    <div className="text-sm text-[#666666]">{formatSchedule(a)}</div>
                    <div className="text-xs text-[#666666]">Last run: {a.last_run_at ? new Date(a.last_run_at).toLocaleString() : 'Never'}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-xs px-2 py-1 rounded bg-emerald-500/20 text-emerald-700">{a.enabled !== false ? '● Active' : 'Paused'}</span>
                  <button
                    type="button"
                    onClick={() => navigate(`/app/agents/${a.id}`)}
                    className="p-2 rounded hover:bg-white/10 text-[#666666] hover:text-[#1A1A1A]"
                    title="Edit"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (!window.confirm('Delete this agent?')) return;
                      axios.delete(`${API}/agents/${a.id}`, { headers: { Authorization: `Bearer ${getToken()}` } })
                        .then(() => refetchAgents())
                        .catch((err) => alert(err.response?.data?.detail || err.message || 'Delete failed'));
                    }}
                    className="p-2 rounded hover:bg-red-500/20 text-[#666666] hover:text-red-600"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      ) : agent ? (
        <div className="space-y-6">
          <button onClick={() => navigate('/app/agents')} className="text-[#666666] hover:text-[#1A1A1A] text-sm">← Back to list</button>
          <div className="p-4 rounded-lg bg-white/5 border border-white/10">
            <h2 className="text-lg font-semibold text-[#1A1A1A]">{agent.name}</h2>
            {agent.description && <p className="text-[#666666] text-sm mt-1">{agent.description}</p>}
            <div className="mt-2 text-sm text-[#666666]">Trigger: {agent.trigger_type}</div>
            {agent.webhook_url && (
              <div className="mt-3 space-y-2">
                <div className="flex items-center gap-2">
                  <code className="text-xs bg-zinc-900/30 px-2 py-1 rounded truncate max-w-md">{agent.webhook_url}</code>
                  <button onClick={() => copyWebhook(agent.webhook_url)} className="p-1 rounded hover:bg-white/10" title="Copy URL">
                    {copied ? <Check className="w-4 h-4 text-[#1A1A1A]" /> : <Copy className="w-4 h-4" />}
                  </button>
                  <button onClick={rotateWebhookSecret} className="text-xs px-2 py-1 rounded border border-white/20 hover:bg-white/10" title="Regenerate secret (old URL will stop working)">
                    Regenerate secret
                  </button>
                </div>
                {rotateModal && (
                  <div className="p-3 rounded bg-neutral-100 border border-neutral-200 text-sm text-[#1A1A1A]">
                    <p className="font-medium mb-1">New secret — copy and save; shown once.</p>
                    <p className="text-xs text-[#666666] mb-1">Secret: <code className="bg-white/80 px-1 rounded">{rotateModal.secret}</code></p>
                    <div className="flex items-center gap-2">
                      <code className="text-xs flex-1 truncate bg-white/80 px-2 py-1 rounded">{rotateModal.url}</code>
                      <button onClick={() => copyWebhookModal(rotateModal.url)} className="p-1 rounded hover:bg-white/80">{copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}</button>
                    </div>
                    <button onClick={closeRotateModal} className="mt-2 text-xs text-[#666666] hover:text-[#1A1A1A]">Dismiss</button>
                  </div>
                )}
              </div>
            )}
            <div className="mt-4">
              <h3 className="text-sm font-medium text-gray-300 mb-2">Runs</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[#666666] border-b border-white/10">
                      <th className="pb-2 pr-4">Time</th>
                      <th className="pb-2 pr-4">Trigger</th>
                      <th className="pb-2 pr-4">Status</th>
                      <th className="pb-2">Duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.map((r) => (
                      <tr key={r.id} className="border-b border-white/5">
                        <td className="py-2 pr-4 text-gray-300">{r.triggered_at ? new Date(r.triggered_at).toLocaleString() : '-'}</td>
                        <td className="py-2 pr-4 text-[#666666]">{r.triggered_by || '-'}</td>
                        <td className="py-2 pr-4"><span className={r.status === 'success' ? 'text-[#1A1A1A]' : r.status === 'failed' ? 'text-[#666666]' : 'text-[#666666]'}>{r.status}</span></td>
                        <td className="py-2">{r.duration_seconds != null ? `${r.duration_seconds.toFixed(1)}s` : '-'}</td>
                        <td>
                          <button onClick={() => setLogRunId(logRunId === r.id ? null : r.id)} className="text-[#1A1A1A] hover:underline text-xs">Logs</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            {logRunId && (
              <div className="mt-4 p-4 rounded bg-zinc-900/30 border border-white/10 font-mono text-xs text-gray-300 max-h-48 overflow-auto">
                <div className="flex justify-between items-center mb-2">
                  <span>Run logs</span>
                  <button onClick={() => setLogRunId(null)} className="text-[#666666] hover:text-[#1A1A1A]">Close</button>
                </div>
                {(logLines.length ? logLines : ['No logs']).map((line, i) => (
                  <div key={i} className="whitespace-pre-wrap break-all">{line}</div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
