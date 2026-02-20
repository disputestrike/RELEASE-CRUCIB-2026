import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth, API } from '../App';
import axios from 'axios';
import { Zap, Plus, ChevronRight, Play, Copy, Check } from 'lucide-react';

const getToken = () => localStorage.getItem('token');

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
  const [createOpen, setCreateOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const headers = { Authorization: `Bearer ${getToken()}` };
    axios.get(`${API}/agents`, { headers })
      .then((r) => setAgents(r.data.items || []))
      .catch(() => setAgents([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!id) return;
    const headers = { Authorization: `Bearer ${getToken()}` };
    axios.get(`${API}/agents/${id}`, { headers })
      .then((r) => setAgent(r.data))
      .catch(() => setAgent(null));
    axios.get(`${API}/agents/${id}/runs`, { headers })
      .then((r) => setRuns(r.data.items || []))
      .catch(() => setRuns([]));
  }, [id]);

  useEffect(() => {
    if (!logRunId) { setLogLines([]); return; }
    const headers = { Authorization: `Bearer ${getToken()}` };
    axios.get(`${API}/agents/runs/${logRunId}/logs`, { headers })
      .then((r) => setLogLines(r.data.log_lines || []))
      .catch(() => setLogLines([]));
  }, [logRunId]);

  const copyWebhook = (url) => {
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
          <Zap className="w-7 h-7 text-gray-600" />
          Agents & Automations
        </h1>
        <button
          onClick={() => setCreateOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-black hover:bg-gray-200 rounded-lg text-[#1A1A1A]"
        >
          <Plus className="w-5 h-5" /> Create Agent
        </button>
      </div>

      {loading ? (
        <div className="text-gray-600">Loading agents...</div>
      ) : !id ? (
        <div className="space-y-6">
          {/* Prompt-to-automation: describe in plain language */}
          <div className="p-4 rounded-xl border border-white/10 bg-white/5">
            <h2 className="text-sm font-semibold text-[#1A1A1A] mb-2">Describe your automation</h2>
            <p className="text-xs text-gray-600 mb-3">The same AI that builds your app runs inside your automations. Describe what you want in plain language and we create the agent.</p>
            <DescribeAndCreate
              onCreated={(agentId) => {
                setLoading(true);
                axios.get(`${API}/agents`, { headers: { Authorization: `Bearer ${getToken()}` } })
                  .then((r) => setAgents(r.data.items || []))
                  .finally(() => setLoading(false));
                if (agentId) navigate(`/app/agents/${agentId}`);
              }}
            />
          </div>
          <div className="space-y-2">
          {agents.length === 0 ? (
            <p className="text-gray-600">No agents yet. Create one to run tasks on a schedule or via webhook.</p>
          ) : (
            agents.map((a) => (
              <div
                key={a.id}
                onClick={() => navigate(`/app/agents/${a.id}`)}
                className="flex items-center justify-between p-4 rounded-lg bg-white/5 border border-white/10 hover:border-gray-300/50 cursor-pointer"
              >
                <div>
                  <div className="font-medium text-[#1A1A1A]">{a.name}</div>
                  <div className="text-sm text-gray-600">{a.trigger_type} · {a.run_count ?? 0} runs</div>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-600" />
              </div>
            ))
          )}
          </div>
        </div>
      ) : agent ? (
        <div className="space-y-6">
          <button onClick={() => navigate('/app/agents')} className="text-gray-600 hover:text-[#1A1A1A] text-sm">← Back to list</button>
          <div className="p-4 rounded-lg bg-white/5 border border-white/10">
            <h2 className="text-lg font-semibold text-[#1A1A1A]">{agent.name}</h2>
            {agent.description && <p className="text-gray-600 text-sm mt-1">{agent.description}</p>}
            <div className="mt-2 text-sm text-gray-600">Trigger: {agent.trigger_type}</div>
            {agent.webhook_url && (
              <div className="mt-3 flex items-center gap-2">
                <code className="text-xs bg-gray-900/30 px-2 py-1 rounded truncate max-w-md">{agent.webhook_url}</code>
                <button onClick={() => copyWebhook(agent.webhook_url)} className="p-1 rounded hover:bg-white/10">
                  {copied ? <Check className="w-4 h-4 text-gray-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            )}
            <div className="mt-4">
              <h3 className="text-sm font-medium text-gray-300 mb-2">Runs</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-600 border-b border-white/10">
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
                        <td className="py-2 pr-4 text-gray-600">{r.triggered_by || '-'}</td>
                        <td className="py-2 pr-4"><span className={r.status === 'success' ? 'text-gray-400' : r.status === 'failed' ? 'text-gray-400' : 'text-gray-600'}>{r.status}</span></td>
                        <td className="py-2">{r.duration_seconds != null ? `${r.duration_seconds.toFixed(1)}s` : '-'}</td>
                        <td>
                          <button onClick={() => setLogRunId(logRunId === r.id ? null : r.id)} className="text-gray-500 hover:underline text-xs">Logs</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            {logRunId && (
              <div className="mt-4 p-4 rounded bg-gray-900/30 border border-white/10 font-mono text-xs text-gray-300 max-h-48 overflow-auto">
                <div className="flex justify-between items-center mb-2">
                  <span>Run logs</span>
                  <button onClick={() => setLogRunId(null)} className="text-gray-600 hover:text-[#1A1A1A]">Close</button>
                </div>
                {(logLines.length ? logLines : ['No logs']).map((line, i) => (
                  <div key={i} className="whitespace-pre-wrap break-all">{line}</div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}

      {createOpen && (
        <CreateAgentModal
          onClose={() => setCreateOpen(false)}
          onCreated={(agentId) => {
            setCreateOpen(false);
            setLoading(true);
            axios.get(`${API}/agents`, { headers: { Authorization: `Bearer ${getToken()}` } })
              .then((r) => setAgents(r.data.items || []))
              .finally(() => setLoading(false));
            if (agentId) navigate(`/app/agents/${agentId}`);
          }}
        />
      )}
    </div>
  );
}

function DescribeAndCreate({ onCreated }) {
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const handleSubmit = (e) => {
    e.preventDefault();
    if (!description.trim()) return;
    setError('');
    setLoading(true);
    axios.post(`${API}/agents/from-description`, { description: description.trim() }, { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => {
        if (r.data && r.data.id) onCreated(r.data.id);
      })
      .catch((err) => setError(err.response?.data?.detail || err.message || 'Failed to create automation'))
      .finally(() => setLoading(false));
  };
  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2">
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="e.g. Every morning at 9, summarize key updates and email them to me."
        className="w-full px-3 py-2 rounded bg-gray-900/30 border border-white/10 text-[#1A1A1A] placeholder-gray-500 min-h-[80px] text-sm"
        rows={3}
      />
      {error && <p className="text-gray-400 text-xs">{error}</p>}
      <button type="submit" disabled={loading || !description.trim()} className="self-start px-4 py-2 rounded bg-black text-[#1A1A1A] text-sm font-medium hover:bg-gray-200 disabled:opacity-50">
        {loading ? 'Creating…' : 'Create from description'}
      </button>
    </form>
  );
}

function CreateAgentModal({ onClose, onCreated }) {
  const [mode, setMode] = useState('describe'); // 'describe' | 'configure'
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [triggerType, setTriggerType] = useState('schedule');
  const [cronExpression, setCronExpression] = useState('0 9 * * *');
  const [webhookSecret, setWebhookSecret] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [describeText, setDescribeText] = useState('');
  const [describeLoading, setDescribeLoading] = useState(false);
  const [describeError, setDescribeError] = useState('');

  const handleDescribeSubmit = (e) => {
    e.preventDefault();
    if (!describeText.trim()) return;
    setDescribeError('');
    setDescribeLoading(true);
    axios.post(`${API}/agents/from-description`, { description: describeText.trim() }, { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => { if (r.data && r.data.id) onCreated(r.data.id); })
      .catch((err) => setDescribeError(err.response?.data?.detail || err.message || 'Failed'))
      .finally(() => setDescribeLoading(false));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    const trigger = triggerType === 'schedule'
      ? { type: 'schedule', cron_expression: cronExpression }
      : { type: 'webhook', webhook_secret: webhookSecret || undefined };
    const body = {
      name: name || 'My Agent',
      description: description || undefined,
      trigger,
      actions: [{ type: 'http', config: { method: 'GET', url: 'https://httpbin.org/get' } }],
      enabled: true,
    };
    setSubmitting(true);
    axios.post(`${API}/agents`, body, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
      .then(() => onCreated())
      .catch((err) => setError(err.response?.data?.detail || err.message))
      .finally(() => setSubmitting(false));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/70" onClick={onClose}>
      <div className="bg-[#111] border border-white/10 rounded-xl p-6 max-w-md w-full shadow-xl max-h-[90vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-semibold text-[#1A1A1A] mb-4">Create Agent</h3>
        <div className="flex gap-2 mb-4 border-b border-white/10 pb-2">
          <button type="button" onClick={() => setMode('describe')} className={`px-3 py-1.5 rounded text-sm ${mode === 'describe' ? 'bg-black text-[#1A1A1A]' : 'text-gray-600 hover:text-[#1A1A1A]'}`}>Describe</button>
          <button type="button" onClick={() => setMode('configure')} className={`px-3 py-1.5 rounded text-sm ${mode === 'configure' ? 'bg-black text-[#1A1A1A]' : 'text-gray-600 hover:text-[#1A1A1A]'}`}>Configure</button>
        </div>
        {mode === 'describe' && (
          <>
            <p className="text-xs text-gray-600 mb-2">Describe what you want in plain language. We create the automation.</p>
            <form onSubmit={handleDescribeSubmit} className="space-y-3">
              <textarea value={describeText} onChange={(e) => setDescribeText(e.target.value)} placeholder="e.g. Every morning at 9, summarize key updates and email them to me." className="w-full px-3 py-2 rounded bg-gray-900/30 border border-white/10 text-[#1A1A1A] placeholder-gray-500 min-h-[100px] text-sm" />
              {describeError && <p className="text-gray-400 text-sm">{describeError}</p>}
              <div className="flex gap-2 justify-end">
                <button type="button" onClick={onClose} className="px-4 py-2 rounded border border-white/20 text-gray-300 hover:bg-white/5">Cancel</button>
                <button type="submit" disabled={describeLoading || !describeText.trim()} className="px-4 py-2 rounded bg-black text-[#1A1A1A] hover:bg-gray-200 disabled:opacity-50">{describeLoading ? 'Creating…' : 'Create from description'}</button>
              </div>
            </form>
          </>
        )}
        {mode === 'configure' && (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="w-full px-3 py-2 rounded bg-gray-900/30 border border-white/10 text-[#1A1A1A]" placeholder="My Agent" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Description</label>
            <input type="text" value={description} onChange={(e) => setDescription(e.target.value)} className="w-full px-3 py-2 rounded bg-gray-900/30 border border-white/10 text-[#1A1A1A]" placeholder="Optional" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Trigger</label>
            <select value={triggerType} onChange={(e) => setTriggerType(e.target.value)} className="w-full px-3 py-2 rounded bg-gray-900/30 border border-white/10 text-[#1A1A1A]">
              <option value="schedule">Schedule (cron)</option>
              <option value="webhook">Webhook</option>
            </select>
          </div>
          {triggerType === 'schedule' && (
            <div>
              <label className="block text-sm text-gray-600 mb-1">Cron (e.g. 0 9 * * * = 9am daily)</label>
              <input type="text" value={cronExpression} onChange={(e) => setCronExpression(e.target.value)} className="w-full px-3 py-2 rounded bg-gray-900/30 border border-white/10 text-[#1A1A1A] font-mono" />
            </div>
          )}
          {triggerType === 'webhook' && (
            <div>
              <label className="block text-sm text-gray-600 mb-1">Webhook secret (optional)</label>
              <input type="text" value={webhookSecret} onChange={(e) => setWebhookSecret(e.target.value)} className="w-full px-3 py-2 rounded bg-gray-900/30 border border-white/10 text-[#1A1A1A]" placeholder="Auto-generated if empty" />
            </div>
          )}
          {error && <p className="text-gray-400 text-sm">{error}</p>}
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded border border-white/20 text-gray-300 hover:bg-white/5">Cancel</button>
            <button type="submit" disabled={submitting} className="px-4 py-2 rounded bg-black text-[#1A1A1A] hover:bg-gray-200 disabled:opacity-50">Create</button>
          </div>
        </form>
        )}
      </div>
    </div>
  );
}
