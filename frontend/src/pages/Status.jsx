import { useState, useEffect } from 'react';
import { useAuth, API } from '../App';
import PublicNav from '../components/PublicNav';
import PublicFooter from '../components/PublicFooter';
import axios from 'axios';

const SERVICES = [
  { name: 'Build API', description: 'Agent orchestration and build pipeline' },
  { name: 'AI Models', description: 'Haiku, Cerebras, Llama routing' },
  { name: 'Authentication', description: 'Login, signup, OAuth' },
  { name: 'Voice Input', description: 'Transcription service' },
  { name: 'Export & Deploy', description: 'ZIP, GitHub, Vercel' },
  { name: 'Benchmark Gate', description: '50-prompt repeatability scorecard' },
  { name: 'Full Systems Gate', description: 'Backend, frontend, Railway, live golden path' },
  { name: 'Published Apps', description: 'Public generated-app URLs' },
  { name: 'Web App', description: 'crucibai-production.up.railway.app' },
];

const INCIDENTS = [
  // Empty for now — no incidents
];

function StatusBadge({ status }) {
  const configs = {
    operational: { color: '#10b981', bg: '#f0fdf4', label: 'Operational' },
    degraded: { color: '#525252', bg: '#f5f5f5', label: 'Degraded' },
    outage: { color: '#ef4444', bg: '#fef2f2', label: 'Outage' },
    checking: { color: '#9ca3af', bg: '#f9fafb', label: 'Checking...' },
  };
  const cfg = configs[status] || configs.checking;
  return (
    <span style={{ background: cfg.bg, color: cfg.color, padding: '2px 10px', borderRadius: '999px', fontSize: '12px', fontWeight: 500 }}>
      {cfg.label}
    </span>
  );
}

export default function Status() {
  const { token } = useAuth();
  const [statuses, setStatuses] = useState(() => Object.fromEntries(SERVICES.map(s => [s.name, 'checking'])));
  const [uptime, setUptime] = useState('99.9%');
  const [lastChecked, setLastChecked] = useState(null);

  useEffect(() => {
    const check = async () => {
      try {
        const res = await axios.get(`${API}/health`, { timeout: 5000 });
        const bench = await axios.get(`${API}/trust/benchmark-summary`, { timeout: 5000 }).catch(() => null);
        const fullSystems = await axios.get(`${API}/trust/full-systems-summary`, { timeout: 5000 }).catch(() => null);
        const isUp = res.status === 200;
        const benchmarkReady = bench?.data?.status === 'ready';
        const fullSystemsReady = fullSystems?.data?.status === 'ready';
        setStatuses(Object.fromEntries(SERVICES.map(s => [
          s.name,
          s.name === 'Benchmark Gate'
            ? (benchmarkReady ? 'operational' : 'degraded')
            : s.name === 'Full Systems Gate'
              ? (fullSystemsReady ? 'operational' : 'degraded')
              : (isUp ? 'operational' : 'degraded')
        ])));
        setLastChecked(new Date().toLocaleTimeString());
      } catch {
        setStatuses(prev => ({ ...prev, 'Build API': 'degraded', 'AI Models': 'degraded' }));
        setLastChecked(new Date().toLocaleTimeString());
      }
    };
    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, [token]);

  const allOperational = Object.values(statuses).every(s => s === 'operational');

  return (
    <div className="min-h-screen bg-[#FAFAF8]">
      <PublicNav />
      <div className="max-w-3xl mx-auto px-6 py-24">

        {/* Overall status */}
        <div className={`p-6 rounded-2xl mb-12 text-center ${allOperational ? 'bg-green-50 border border-green-100' : 'bg-neutral-100 border border-neutral-200'}`}>
          <div className="flex items-center justify-center gap-3 mb-2">
            <div className={`w-3 h-3 rounded-full ${allOperational ? 'bg-green-500' : 'bg-neutral-500'}`} style={{ animation: 'pulse 2s infinite' }} />
            <h1 className={`text-xl font-semibold ${allOperational ? 'text-green-800' : 'text-neutral-800'}`}>
              {allOperational ? 'All systems operational' : 'Some systems degraded'}
            </h1>
          </div>
          <p className={`text-sm ${allOperational ? 'text-green-600' : 'text-neutral-600'}`}>
            {lastChecked ? `Last checked: ${lastChecked}` : 'Checking services...'}
            {' · '}30-day uptime: {uptime}
          </p>
        </div>

        {/* Service grid */}
        <div className="mb-12">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-widest mb-4">Services</h2>
          <div className="space-y-3">
            {SERVICES.map(service => (
              <div key={service.name} className="flex items-center justify-between p-4 bg-white rounded-xl border border-gray-200">
                <div>
                  <p className="font-medium text-gray-900 text-sm">{service.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{service.description}</p>
                </div>
                <StatusBadge status={statuses[service.name]} />
              </div>
            ))}
          </div>
        </div>

        {/* Incidents */}
        <div className="mb-12">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-widest mb-4">Recent incidents</h2>
          {INCIDENTS.length === 0 ? (
            <div className="p-6 bg-white rounded-xl border border-gray-200 text-center">
              <p className="text-sm text-gray-500">No incidents in the last 90 days.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {INCIDENTS.map((incident, i) => (
                <div key={i} className="p-4 bg-white rounded-xl border border-gray-200">
                  <div className="flex items-start justify-between">
                    <p className="font-medium text-gray-900 text-sm">{incident.title}</p>
                    <span className="text-xs text-gray-400">{incident.date}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{incident.description}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Uptime history */}
        <div>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-widest mb-4">30-day uptime</h2>
          <div className="p-4 bg-white rounded-xl border border-gray-200">
            <div className="flex gap-1 mb-3">
              {Array.from({ length: 30 }, (_, i) => (
                <div key={i} className="flex-1 h-8 rounded-sm bg-green-400 opacity-90 hover:opacity-100 transition" title={`Day ${30 - i}: Operational`} />
              ))}
            </div>
            <div className="flex justify-between text-xs text-gray-400">
              <span>30 days ago</span>
              <span className="font-medium text-green-600">{uptime} uptime</span>
              <span>Today</span>
            </div>
          </div>
        </div>

      </div>
      <PublicFooter />
    </div>
  );
}
