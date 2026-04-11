import { useState } from 'react';
import { Upload, Play, CheckCircle, Clock, AlertCircle, Database, FileText, Zap } from 'lucide-react';

const DEMO_JOBS = [
  { id: 'ft-001', name: 'Customer support bot v2', base_model: 'claude-haiku', status: 'completed', created_at: '2026-03-10', samples: 1240, accuracy: '94.2%' },
  { id: 'ft-002', name: 'Legal document analyzer', base_model: 'claude-sonnet', status: 'running', created_at: '2026-03-16', samples: 3800, accuracy: null },
  { id: 'ft-003', name: 'E-commerce product desc', base_model: 'llama-70b', status: 'queued', created_at: '2026-03-17', samples: 560, accuracy: null },
];

const STATUS_STYLES = {
  completed: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50', label: 'Completed' },
  running: { icon: Play, color: 'text-blue-600', bg: 'bg-blue-50', label: 'Training...' },
  queued: { icon: Clock, color: 'text-amber-600', bg: 'bg-amber-50', label: 'Queued' },
  failed: { icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-50', label: 'Failed' },
};

export default function FineTuning() {
  const [tab, setTab] = useState('jobs');
  const [newJob, setNewJob] = useState({ name: '', base_model: 'claude-haiku', description: '' });
  const [file, setFile] = useState(null);

  const handleFileSelect = (e) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
    e.target.value = '';
  };

  const handleSubmit = () => {
    if (!newJob.name || !file) {
      alert('Please provide a job name and upload a training dataset.');
      return;
    }
    alert(`Fine-tuning job "${newJob.name}" submitted. You will be notified when training completes.\n\nNote: Fine-tuning uses the OpenAI/Anthropic fine-tuning API. Ensure your API keys are configured in Settings → Env.`);
    setNewJob({ name: '', base_model: 'claude-haiku', description: '' });
    setFile(null);
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900 mb-1">Fine-Tuning</h1>
        <p className="text-gray-500 text-sm">Train custom models on your data. Fine-tuned models are faster, cheaper, and more accurate for your specific use case.</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {['jobs', 'new', 'datasets'].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium transition border-b-2 -mb-px capitalize ${tab === t ? 'border-black text-gray-900' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {t === 'new' ? '+ New job' : t}
          </button>
        ))}
      </div>

      {tab === 'jobs' && (
        <div className="space-y-4">
          {DEMO_JOBS.map(job => {
            const s = STATUS_STYLES[job.status] || STATUS_STYLES.queued;
            const Icon = s.icon;
            return (
              <div key={job.id} className="p-4 rounded-xl border border-gray-200 bg-white hover:border-gray-300 transition">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-semibold text-gray-900">{job.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">Base: {job.base_model} · {job.samples.toLocaleString()} samples · Created {job.created_at}</p>
                  </div>
                  <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${s.bg} ${s.color}`}>
                    <Icon className="w-3 h-3" />
                    {s.label}
                  </div>
                </div>
                {job.accuracy && (
                  <div className="mt-3 flex gap-4">
                    <div className="text-xs"><span className="text-gray-500">Accuracy:</span> <span className="font-semibold text-green-700">{job.accuracy}</span></div>
                    <button className="text-xs text-blue-600 hover:underline">Deploy model</button>
                    <button className="text-xs text-blue-600 hover:underline">View results</button>
                  </div>
                )}
                {job.status === 'running' && (
                  <div className="mt-3">
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full animate-pulse" style={{ width: '62%' }} />
                    </div>
                    <p className="text-xs text-gray-400 mt-1">Training in progress... ~45 min remaining</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {tab === 'new' && (
        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Job name</label>
            <input value={newJob.name} onChange={e => setNewJob({ ...newJob, name: e.target.value })}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-gray-400"
              placeholder="e.g. customer-support-v3" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Base model</label>
            <select value={newJob.base_model} onChange={e => setNewJob({ ...newJob, base_model: e.target.value })}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-gray-400 bg-white">
              <option value="claude-haiku">Claude Haiku — fastest, good quality</option>
              <option value="llama-70b">Llama 70B — open source, cost efficient</option>
              <option value="gpt-3.5-turbo">GPT-3.5 Turbo — via OpenAI API</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Training dataset</label>
            <div
              onClick={() => document.getElementById('ft-file').click()}
              className="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center cursor-pointer hover:border-gray-300 transition">
              <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
              {file ? (
                <p className="text-sm font-medium text-gray-700">{file.name} <span className="text-gray-400">({(file.size / 1024).toFixed(0)} KB)</span></p>
              ) : (
                <>
                  <p className="text-sm text-gray-500">Upload JSONL file</p>
                  <p className="text-xs text-gray-400 mt-1">Format: {`{"prompt": "...", "completion": "..."}`} — one per line</p>
                </>
              )}
              <input id="ft-file" type="file" accept=".jsonl,.json,.csv" onChange={handleFileSelect} className="hidden" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description (optional)</label>
            <textarea value={newJob.description} onChange={e => setNewJob({ ...newJob, description: e.target.value })}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-gray-400 resize-none"
              rows={2} placeholder="What is this fine-tuned model for?" />
          </div>

          <div className="p-4 bg-amber-50 border border-amber-100 rounded-xl text-xs text-amber-800 leading-relaxed">
            <strong>Before starting:</strong> Fine-tuning uses your API keys (Anthropic or OpenAI). Make sure they are configured in <strong>Settings → Env Variables</strong>. Training typically takes 30–90 minutes and consumes API credits from your provider account, not CrucibAI credits.
          </div>

          <button onClick={handleSubmit}
            className="flex items-center gap-2 px-6 py-2.5 bg-black text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition">
            <Zap className="w-4 h-4" /> Start fine-tuning
          </button>
        </div>
      )}

      {tab === 'datasets' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl border border-gray-200 bg-white">
            <div className="flex items-center gap-3 mb-3">
              <Database className="w-5 h-5 text-gray-500" />
              <div>
                <p className="font-medium text-sm text-gray-900">CrucibAI build data</p>
                <p className="text-xs text-gray-500">Auto-collected from your builds — agent inputs/outputs, quality scores, user feedback</p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div><p className="text-lg font-semibold text-gray-900">12,400</p><p className="text-xs text-gray-500">Training samples</p></div>
              <div><p className="text-lg font-semibold text-gray-900">94.1%</p><p className="text-xs text-gray-500">Quality score avg</p></div>
              <div><p className="text-lg font-semibold text-gray-900">Broad</p><p className="text-xs text-gray-500">Agent &amp; sub-agent roles</p></div>
            </div>
            <button className="mt-3 text-xs text-blue-600 hover:underline flex items-center gap-1">
              <FileText className="w-3 h-3" /> Export as JSONL for fine-tuning
            </button>
          </div>
          <p className="text-xs text-gray-400">Every build you run on CrucibAI contributes to a proprietary dataset. The more you build, the smarter CrucibAI gets for your specific use cases.</p>
        </div>
      )}
    </div>
  );
}
