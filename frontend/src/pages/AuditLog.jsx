import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth, API } from '../App';
import { Download, Filter } from 'lucide-react';

export default function AuditLog() {
  const { token } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(50);
  const [skip, setSkip] = useState(0);
  const [actionFilter, setActionFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    const params = { limit, skip };
    if (actionFilter) params.action = actionFilter;
    axios.get(`${API}/audit/logs`, { params, headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        setLogs(r.data.logs || []);
        setTotal(r.data.total || 0);
      })
      .catch(() => setLogs([]))
      .finally(() => setLoading(false));
  }, [token, limit, skip, actionFilter]);

  const handleExport = () => {
    if (!startDate || !endDate) {
      alert('Please select start and end dates');
      return;
    }
    axios.get(`${API}/audit/logs/export`, {
      params: { start_date: startDate, end_date: endDate, format: 'csv' },
      headers: { Authorization: `Bearer ${token}` },
      responseType: 'text',
    })
      .then((r) => {
        const csv = typeof r.data === 'string' ? r.data : (r.data?.data || '');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-log-${startDate}-to-${endDate}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch((e) => alert(e.response?.data?.detail || 'Export failed'));
  };

  return (
    <div className="p-6 max-w-5xl">
      <h1 className="text-2xl font-bold text-[#1A1A1A] mb-6">Audit Log</h1>

      <div className="mb-6 p-4 bg-[#0a0a0a] border border-white/10 rounded-xl">
        <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
          <Download className="w-4 h-4" />
          Export
        </h3>
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Start</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-[#1A1A1A]"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">End</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-[#1A1A1A]"
            />
          </div>
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-4 py-2 bg-gray-200 hover:bg-black rounded-lg text-sm font-medium"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      <div className="mb-4 p-3 bg-[#0a0a0a] border border-white/10 rounded-lg flex items-center gap-2">
        <Filter className="w-4 h-4 text-[#666666]" />
        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-[#1A1A1A] text-sm"
        >
          <option value="">All actions</option>
          <option value="login">Login</option>
          <option value="login_mfa_verified">Login (MFA)</option>
          <option value="signup">Signup</option>
          <option value="mfa_enabled">MFA enabled</option>
          <option value="mfa_disabled">MFA disabled</option>
          <option value="project_created">Project created</option>
          <option value="project_deployed">Project deployed</option>
        </select>
      </div>

      {loading ? (
        <p className="text-[#666666]">Loading...</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-white/10">
          <table className="w-full text-sm text-gray-300">
            <thead>
              <tr className="border-b border-white/10 bg-white/5">
                <th className="px-4 py-3 text-left text-[#666666] font-medium">Time</th>
                <th className="px-4 py-3 text-left text-[#666666] font-medium">Action</th>
                <th className="px-4 py-3 text-left text-[#666666] font-medium">Resource</th>
                <th className="px-4 py-3 text-left text-[#666666] font-medium">Status</th>
                <th className="px-4 py-3 text-left text-[#666666] font-medium">IP</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id || log._id} className="border-b border-white/5 hover:bg-white/5">
                  <td className="px-4 py-3 whitespace-nowrap">
                    {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 bg-gray-200/20 text-#c0c0c0 rounded text-xs font-medium">
                      {log.action}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {log.resource_type}
                    {log.resource_id && ` (${String(log.resource_id).slice(0, 8)}…)`}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${log.status === 'success' ? 'bg-gray-500/20 text-gray-400' : 'bg-gray-500/20 text-gray-400'}`}>
                      {log.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-500 text-xs">{log.ip_address || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between text-sm text-[#666666]">
        <span>
          Showing {skip + 1}–{Math.min(skip + limit, total)} of {total}
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => setSkip(Math.max(0, skip - limit))}
            disabled={skip === 0}
            className="px-3 py-1.5 bg-white/10 hover:bg-white/20 disabled:opacity-50 rounded-lg"
          >
            Previous
          </button>
          <button
            onClick={() => setSkip(skip + limit)}
            disabled={skip + limit >= total}
            className="px-3 py-1.5 bg-white/10 hover:bg-white/20 disabled:opacity-50 rounded-lg"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
