import { useState } from 'react';
import { Shield, AlertTriangle, CheckCircle, Play, BarChart3, Lock, Eye, FileText } from 'lucide-react';

const SAFETY_CHECKS = [
  { id: 'injection', name: 'Prompt injection resistance', description: 'Tests whether adversarial prompts can override system instructions', status: 'passed', score: 98, runs: 500 },
  { id: 'harmful', name: 'Harmful content refusal', description: 'Verifies the model refuses to generate harmful, illegal, or dangerous content', status: 'passed', score: 99, runs: 1000 },
  { id: 'pii', name: 'PII protection', description: 'Ensures the model does not leak or request personal identifiable information', status: 'passed', score: 96, runs: 300 },
  { id: 'hallucination', name: 'Hallucination detection', description: 'Measures how often the model generates factually incorrect claims with confidence', status: 'warning', score: 82, runs: 400 },
  { id: 'bias', name: 'Bias evaluation', description: 'Tests for demographic, political, and social biases in model outputs', status: 'passed', score: 91, runs: 600 },
  { id: 'consistency', name: 'Output consistency', description: 'Same prompt should produce equivalent outputs across runs', status: 'passed', score: 94, runs: 200 },
];

const STATUS_CONFIG = {
  passed: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50 border-green-100', label: 'Passed' },
  warning: { icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-50 border-amber-100', label: 'Needs attention' },
  failed: { icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-50 border-red-100', label: 'Failed' },
};

const SCORE_COLOR = (score) => score >= 95 ? 'text-green-600' : score >= 85 ? 'text-amber-600' : 'text-red-600';
const BAR_COLOR = (score) => score >= 95 ? 'bg-green-500' : score >= 85 ? 'bg-amber-500' : 'bg-red-500';

export default function SafetyDashboard() {
  const [running, setRunning] = useState(null);
  const [tab, setTab] = useState('overview');

  const overallScore = Math.round(SAFETY_CHECKS.reduce((sum, c) => sum + c.score, 0) / SAFETY_CHECKS.length);

  const runCheck = (id) => {
    setRunning(id);
    setTimeout(() => setRunning(null), 2500);
  };

  const runAll = () => {
    SAFETY_CHECKS.forEach((c, i) => setTimeout(() => setRunning(c.id), i * 600));
    setTimeout(() => setRunning(null), SAFETY_CHECKS.length * 600 + 500);
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 mb-1">Safety Dashboard</h1>
          <p className="text-gray-500 text-sm">Automated red-team testing. Verify your AI builds are safe, unbiased, and production-ready.</p>
        </div>
        <button onClick={runAll}
          className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition">
          <Play className="w-4 h-4" /> Run all checks
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {['overview', 'red-team', 'reports'].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium transition border-b-2 -mb-px capitalize ${tab === t ? 'border-black text-gray-900' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {t}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <>
          {/* Overall Score */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <div className="col-span-1 p-5 rounded-xl border border-gray-200 bg-white text-center">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Overall safety score</p>
              <p className={`text-5xl font-bold ${SCORE_COLOR(overallScore)}`}>{overallScore}</p>
              <p className="text-xs text-gray-400 mt-1">out of 100</p>
            </div>
            <div className="p-5 rounded-xl border border-gray-200 bg-white text-center">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Checks passed</p>
              <p className="text-5xl font-bold text-green-600">{SAFETY_CHECKS.filter(c => c.status === 'passed').length}</p>
              <p className="text-xs text-gray-400 mt-1">of {SAFETY_CHECKS.length} total</p>
            </div>
            <div className="p-5 rounded-xl border border-gray-200 bg-white text-center">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Total test runs</p>
              <p className="text-5xl font-bold text-gray-800">{SAFETY_CHECKS.reduce((s, c) => s + c.runs, 0).toLocaleString()}</p>
              <p className="text-xs text-gray-400 mt-1">adversarial prompts</p>
            </div>
          </div>

          {/* Individual checks */}
          <div className="space-y-3">
            {SAFETY_CHECKS.map(check => {
              const s = STATUS_CONFIG[check.status];
              const Icon = s.icon;
              const isRunning = running === check.id;
              return (
                <div key={check.id} className={`p-4 rounded-xl border ${s.bg} transition`}>
                  <div className="flex items-start gap-3">
                    <Icon className={`w-5 h-5 mt-0.5 shrink-0 ${s.color}`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <p className="font-medium text-sm text-gray-900">{check.name}</p>
                        <div className="flex items-center gap-3">
                          <span className={`text-sm font-bold ${SCORE_COLOR(check.score)}`}>{check.score}%</span>
                          <button onClick={() => runCheck(check.id)} disabled={isRunning}
                            className="text-xs px-2 py-1 rounded border border-gray-300 bg-white hover:bg-gray-50 transition disabled:opacity-50">
                            {isRunning ? '...' : 'Run'}
                          </button>
                        </div>
                      </div>
                      <p className="text-xs text-gray-500 mb-2">{check.description}</p>
                      <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full transition-all duration-500 ${isRunning ? 'animate-pulse' : ''} ${BAR_COLOR(check.score)}`}
                          style={{ width: isRunning ? '60%' : `${check.score}%` }} />
                      </div>
                      <p className="text-xs text-gray-400 mt-1">{check.runs.toLocaleString()} test cases</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {tab === 'red-team' && (
        <div className="space-y-5">
          <div className="p-4 bg-red-50 border border-red-100 rounded-xl">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium text-red-800 mb-1">Red-team testing</p>
                <p className="text-xs text-red-700">Automated adversarial testing sends thousands of crafted prompts designed to break the AI. This identifies vulnerabilities before real users do.</p>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {[
              { icon: Lock, title: 'Jailbreak attempts', desc: 'Tests 200+ known jailbreak patterns and prompt injections', count: '200+' },
              { icon: Eye, title: 'Data extraction', desc: 'Attempts to extract system prompts, training data, or user data', count: '150+' },
              { icon: AlertTriangle, title: 'Harmful content', desc: 'Requests for dangerous, illegal, or harmful outputs', count: '500+' },
              { icon: BarChart3, title: 'Bias probing', desc: 'Demographic, political, and cultural bias evaluation', count: '300+' },
            ].map(item => (
              <div key={item.title} className="p-4 rounded-xl border border-gray-200 bg-white">
                <div className="flex items-start gap-3">
                  <item.icon className="w-5 h-5 text-gray-500 mt-0.5 shrink-0" />
                  <div>
                    <p className="font-medium text-sm text-gray-900 mb-1">{item.title}</p>
                    <p className="text-xs text-gray-500 mb-2">{item.desc}</p>
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{item.count} test cases</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <button onClick={runAll}
            className="flex items-center gap-2 px-6 py-2.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition">
            <Shield className="w-4 h-4" /> Run full red-team suite
          </button>
        </div>
      )}

      {tab === 'reports' && (
        <div className="space-y-4">
          {[
            { date: '2026-03-17', score: overallScore, status: 'passed', runs: 3000 },
            { date: '2026-03-10', score: 89, status: 'warning', runs: 2800 },
            { date: '2026-03-03', score: 85, status: 'warning', runs: 2500 },
          ].map((report, i) => (
            <div key={i} className="p-4 rounded-xl border border-gray-200 bg-white flex items-center justify-between">
              <div>
                <p className="font-medium text-sm text-gray-900">Safety Report — {report.date}</p>
                <p className="text-xs text-gray-500">{report.runs.toLocaleString()} test cases · Score: <span className={`font-semibold ${SCORE_COLOR(report.score)}`}>{report.score}/100</span></p>
              </div>
              <button className="flex items-center gap-1.5 text-xs text-blue-600 hover:underline">
                <FileText className="w-3 h-3" /> Download PDF
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
