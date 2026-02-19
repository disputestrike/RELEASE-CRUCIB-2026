import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth, API } from '../App';
import axios from 'axios';
import { ShieldAlert, ArrowLeft, CheckCircle, XCircle } from 'lucide-react';

export default function AdminLegal() {
  const { token } = useAuth();
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const url = filter === 'all' ? `${API}/admin/legal/blocked-requests` : `${API}/admin/legal/blocked-requests?status=${filter}`;
        const res = await axios.get(url, { headers: { Authorization: `Bearer ${token}` } });
        setList(res.data.blocked_requests || []);
      } catch (e) {
        setError(e.response?.data?.detail || e.message);
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchData();
  }, [token, filter]);

  const handleReview = async (requestId, action) => {
    try {
      await axios.post(`${API}/admin/legal/review/${requestId}`, { action }, { headers: { Authorization: `Bearer ${token}` } });
      setList(prev => prev.map(r => r.id === requestId ? { ...r, status: 'reviewed', review_action: action } : r));
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  if (error) {
    return (
      <div className="p-8">
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-400">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-legal">
      <div className="flex items-center gap-4">
        <Link to="/app/admin" className="p-2 hover:bg-white/10 rounded-lg transition"><ArrowLeft className="w-5 h-5" /></Link>
        <div>
          <h1 className="text-2xl font-bold">Legal & AUP</h1>
          <p className="text-[#666666] text-sm">Blocked build requests (Acceptable Use Policy)</p>
        </div>
      </div>

      <div className="flex gap-2">
        <button onClick={() => setFilter('all')} className={`px-3 py-1.5 rounded text-sm ${filter === 'all' ? 'bg-blue-600' : 'bg-white/10'}`}>All</button>
        <button onClick={() => setFilter('blocked')} className={`px-3 py-1.5 rounded text-sm ${filter === 'blocked' ? 'bg-blue-600' : 'bg-white/10'}`}>Blocked</button>
        <button onClick={() => setFilter('reviewed')} className={`px-3 py-1.5 rounded text-sm ${filter === 'reviewed' ? 'bg-blue-600' : 'bg-white/10'}`}>Reviewed</button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" /></div>
      ) : (
        <div className="space-y-4">
          {list.length === 0 && <p className="text-[#666666]">No blocked requests</p>}
          {list.map((r) => (
            <div key={r.id} className="p-4 rounded-xl border border-white/10 bg-[#0a0a0a]">
              <div className="flex justify-between items-start gap-4 mb-2">
                <div>
                  <span className="text-xs text-gray-500">User: {r.user_id}</span>
                  <span className="ml-3 px-2 py-0.5 rounded text-xs bg-amber-500/20 text-amber-400">{r.category || 'policy'}</span>
                </div>
                <span className={`text-xs px-2 py-1 rounded ${r.status === 'reviewed' ? 'bg-gray-500/20' : 'bg-red-500/20 text-red-400'}`}>{r.status}</span>
              </div>
              <p className="text-sm text-gray-300 font-mono break-words mb-2">"{r.prompt}"</p>
              <p className="text-xs text-gray-500 mb-3">{r.reason}</p>
              {r.status === 'blocked' && (
                <div className="flex gap-2">
                  <button onClick={() => handleReview(r.id, 'false_positive')} className="flex items-center gap-1 px-3 py-1.5 rounded bg-green-600 hover:bg-green-700 text-sm">
                    <CheckCircle className="w-4 h-4" /> False positive
                  </button>
                  <button onClick={() => handleReview(r.id, 'confirmed')} className="flex items-center gap-1 px-3 py-1.5 rounded bg-amber-600 hover:bg-amber-700 text-sm">
                    <ShieldAlert className="w-4 h-4" /> Confirm
                  </button>
                  <button onClick={() => handleReview(r.id, 'escalated')} className="flex items-center gap-1 px-3 py-1.5 rounded bg-red-600 hover:bg-red-700 text-sm">
                    <XCircle className="w-4 h-4" /> Escalate
                  </button>
                </div>
              )}
              <p className="text-xs text-gray-500 mt-2">{r.timestamp}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
