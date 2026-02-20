import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth, API } from '../App';
import axios from 'axios';
import {
  BarChart3,
  Calendar,
  Download,
  FileText,
  ArrowLeft,
  Search,
} from 'lucide-react';

const AdminAnalytics = () => {
  const { token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [fromDate, setFromDate] = useState(searchParams.get('from') || '');
  const [toDate, setToDate] = useState(searchParams.get('to') || '');
  const [mode, setMode] = useState(searchParams.get('mode') || 'daily'); // daily | weekly
  const [days, setDays] = useState(parseInt(searchParams.get('days') || '30', 10));
  const [daily, setDaily] = useState([]);
  const [weekly, setWeekly] = useState([]);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runQuery = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    const params = new URLSearchParams();
    if (fromDate) params.set('from_date', fromDate);
    if (toDate) params.set('to_date', toDate);
    if (mode === 'daily' && !fromDate && !toDate) params.set('days', days);
    if (mode === 'weekly') params.set('weeks', 12);
    try {
      if (mode === 'daily') {
        const res = await axios.get(`${API}/admin/analytics/daily?${params}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setDaily(res.data.daily || []);
      } else {
        const res = await axios.get(`${API}/admin/analytics/weekly?${params}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setWeekly(res.data.weekly || []);
      }
      const reportParams = new URLSearchParams();
      if (fromDate) reportParams.set('from_date', fromDate);
      if (toDate) reportParams.set('to_date', toDate);
      const reportRes = await axios.get(`${API}/admin/analytics/report?${reportParams}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setReport(reportRes.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) runQuery();
  }, [token, mode]);

  const handleSearch = (e) => {
    e.preventDefault();
    setSearchParams({ ...(fromDate && { from: fromDate }), ...(toDate && { to: toDate }), mode, days: String(days) });
    runQuery();
  };

  const downloadCsv = async () => {
    const params = new URLSearchParams();
    params.set('format', 'csv');
    if (fromDate) params.set('from_date', fromDate);
    if (toDate) params.set('to_date', toDate);
    if (!fromDate && !toDate) params.set('days', days);
    try {
      const res = await axios.get(`${API}/admin/analytics/daily?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `analytics-daily-${fromDate && toDate ? `${fromDate}-${toDate}` : `last-${days}-days`}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'CSV download failed');
    }
  };

  const downloadPdf = () => {
    const data = report || {};
    const from = data.from_date || fromDate || 'N/A';
    const to = data.to_date || toDate || 'N/A';
    const totalSignups = data.total_signups ?? daily.reduce((s, r) => s + (r.signups || 0), 0);
    const totalRevenue = data.total_revenue ?? daily.reduce((s, r) => s + (r.revenue || 0), 0);
    const rows = mode === 'daily' ? daily : weekly;
    const headers = mode === 'daily' ? ['Date', 'Signups', 'Revenue'] : ['Week start', 'Week end', 'Signups', 'Revenue'];
    const body = mode === 'daily'
      ? rows.map((r) => [r.date, r.signups, `$${Number(r.revenue || 0).toFixed(2)}`])
      : rows.map((r) => [r.week_start, r.week_end, r.signups, `$${Number(r.revenue || 0).toFixed(2)}`]);

    const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>CrucibAI Analytics Report</title>
  <style>
    body { font-family: system-ui, sans-serif; padding: 24px; color: #111; }
    h1 { font-size: 20px; margin-bottom: 8px; }
    .meta { color: #666; font-size: 12px; margin-bottom: 16px; }
    table { border-collapse: collapse; width: 100%; font-size: 12px; }
    th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
    th { background: #f5f5f5; }
    .totals { margin-top: 16px; font-weight: 600; }
    @media print { body { padding: 16px; } }
  </style>
</head>
<body>
  <h1>CrucibAI Analytics Report</h1>
  <p class="meta">Period: ${from} to ${to} | Generated: ${new Date().toISOString().slice(0, 19)}</p>
  <table>
    <thead><tr>${headers.map((h) => `<th>${h}</th>`).join('')}</tr></thead>
    <tbody>
      ${body.map((row) => `<tr>${row.map((c) => `<td>${c}</td>`).join('')}</tr>`).join('')}
    </tbody>
  </table>
  <p class="totals">Total signups: ${totalSignups} | Total revenue: $${Number(totalRevenue).toFixed(2)}</p>
</body>
</html>`;
    const win = window.open('', '_blank');
    win.document.write(html);
    win.document.close();
    win.focus();
    setTimeout(() => {
      win.print();
      win.onafterprint = () => win.close();
    }, 250);
  };

  return (
    <div className="space-y-6" data-testid="admin-analytics">
      <div className="flex items-center gap-4 flex-wrap">
        <Link to="/app/admin" className="inline-flex items-center text-[#666666] hover:text-[#1A1A1A]">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Link>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <BarChart3 className="w-8 h-8 text-gray-200" />
          Analytics
        </h1>
      </div>

      <form onSubmit={handleSearch} className="flex flex-wrap items-end gap-4 p-4 rounded-xl border border-white/10 bg-white/5">
        <div className="flex items-center gap-2">
          <Calendar className="w-5 h-5 text-[#666666]" />
          <input
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            className="bg-gray-900/30 border border-white/10 rounded-lg px-3 py-2 text-sm"
          />
          <span className="text-[#666666]">to</span>
          <input
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            className="bg-gray-900/30 border border-white/10 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        {!fromDate && !toDate && mode === 'daily' && (
          <div className="flex items-center gap-2">
            <span className="text-[#666666] text-sm">Last</span>
            <select
              value={days}
              onChange={(e) => setDays(parseInt(e.target.value, 10))}
              className="bg-gray-900/30 border border-white/10 rounded-lg px-3 py-2 text-sm"
            >
              <option value={7}>7 days</option>
              <option value={14}>14 days</option>
              <option value={30}>30 days</option>
              <option value={90}>90 days</option>
            </select>
          </div>
        )}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setMode('daily')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${mode === 'daily' ? 'bg-black text-[#1A1A1A]' : 'bg-white/10 text-[#666666] hover:text-[#1A1A1A]'}`}
          >
            Daily
          </button>
          <button
            type="button"
            onClick={() => setMode('weekly')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${mode === 'weekly' ? 'bg-black text-[#1A1A1A]' : 'bg-white/10 text-[#666666] hover:text-[#1A1A1A]'}`}
          >
            Weekly
          </button>
        </div>
        <button
          type="submit"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-black hover:bg-gray-200 text-[#1A1A1A] font-medium"
        >
          <Search className="w-4 h-4" /> Run query
        </button>
      </form>

      {error && (
        <div className="rounded-lg border border-gray-500/30 bg-gray-500/10 p-4 text-gray-400">{error}</div>
      )}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={downloadCsv}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-white/20 bg-white/5 hover:bg-white/10 text-sm"
        >
          <Download className="w-4 h-4" /> Download CSV
        </button>
        <button
          type="button"
          onClick={downloadPdf}
          disabled={loading || (mode === 'daily' ? !daily.length : !weekly.length)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-white/20 bg-white/5 hover:bg-white/10 text-sm"
        >
          <FileText className="w-4 h-4" /> Download PDF
        </button>
      </div>

      {report && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl border border-white/10 bg-white/5">
            <p className="text-[#666666] text-sm">Period</p>
            <p className="font-semibold">{report.from_date} → {report.to_date}</p>
          </div>
          <div className="p-4 rounded-xl border border-white/10 bg-white/5">
            <p className="text-[#666666] text-sm">Total signups</p>
            <p className="font-semibold text-xl">{report.total_signups}</p>
          </div>
          <div className="p-4 rounded-xl border border-white/10 bg-white/5">
            <p className="text-[#666666] text-sm">Total revenue</p>
            <p className="font-semibold text-xl text-gray-400">${Number(report.total_revenue || 0).toFixed(2)}</p>
          </div>
          <div className="p-4 rounded-xl border border-white/10 bg-white/5">
            <p className="text-[#666666] text-sm">Generated</p>
            <p className="font-semibold text-sm">{report.generated_at ? new Date(report.generated_at).toLocaleString() : '-'}</p>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-10 h-10 border-2 border-gray-300 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : mode === 'daily' ? (
        <div className="rounded-xl border border-white/10 overflow-hidden">
          <table className="w-full">
            <thead className="bg-white/5 border-b border-white/10">
              <tr>
                <th className="text-left py-3 px-4">Date</th>
                <th className="text-left py-3 px-4">Signups</th>
                <th className="text-left py-3 px-4">Paid (cumulative)</th>
                <th className="text-left py-3 px-4">Revenue</th>
              </tr>
            </thead>
            <tbody>
              {daily.map((r) => (
                <tr key={r.date} className="border-b border-white/5 hover:bg-white/5">
                  <td className="py-3 px-4">{r.date}</td>
                  <td className="py-3 px-4">{r.signups}</td>
                  <td className="py-3 px-4">{r.paid_users_cumulative}</td>
                  <td className="py-3 px-4 text-gray-400">${Number(r.revenue || 0).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {daily.length === 0 && (
            <div className="text-center py-12 text-gray-500">No data. Set a date range and run query.</div>
          )}
        </div>
      ) : (
        <div className="rounded-xl border border-white/10 overflow-hidden">
          <table className="w-full">
            <thead className="bg-white/5 border-b border-white/10">
              <tr>
                <th className="text-left py-3 px-4">Week start</th>
                <th className="text-left py-3 px-4">Week end</th>
                <th className="text-left py-3 px-4">Signups</th>
                <th className="text-left py-3 px-4">Revenue</th>
              </tr>
            </thead>
            <tbody>
              {weekly.map((r) => (
                <tr key={r.week_start + r.week_end} className="border-b border-white/5 hover:bg-white/5">
                  <td className="py-3 px-4">{r.week_start}</td>
                  <td className="py-3 px-4">{r.week_end}</td>
                  <td className="py-3 px-4">{r.signups}</td>
                  <td className="py-3 px-4 text-gray-400">${Number(r.revenue || 0).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {weekly.length === 0 && (
            <div className="text-center py-12 text-gray-500">No data. Run query.</div>
          )}
        </div>
      )}
    </div>
  );
};

export default AdminAnalytics;
