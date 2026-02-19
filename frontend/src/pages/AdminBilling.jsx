import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth, API } from '../App';
import axios from 'axios';
import { DollarSign, ArrowLeft } from 'lucide-react';

const AdminBilling = () => {
  const { token } = useAuth();
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        const res = await axios.get(`${API}/admin/billing/transactions?limit=100`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setTransactions(res.data.transactions || []);
      } catch (e) {
        setError(e.response?.data?.detail || e.message);
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchTransactions();
  }, [token]);

  if (error) {
    return (
      <div className="p-8">
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-400">{error}</div>
        <Link to="/app/admin" className="inline-flex items-center mt-4 text-blue-400">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Admin
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-billing">
      <div className="flex items-center gap-4">
        <Link to="/app/admin" className="inline-flex items-center text-[#666666] hover:text-[#1A1A1A]">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back
        </Link>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <DollarSign className="w-8 h-8 text-green-500" />
          Billing transactions
        </h1>
      </div>
      <p className="text-[#666666]">Who paid, when, amount (from Stripe webhook ledger).</p>
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="rounded-xl border border-white/10 overflow-hidden">
          <table className="w-full">
            <thead className="bg-white/5 border-b border-white/10">
              <tr>
                <th className="text-left py-3 px-4">User ID</th>
                <th className="text-left py-3 px-4">Bundle</th>
                <th className="text-left py-3 px-4">Credits</th>
                <th className="text-left py-3 px-4">Amount</th>
                <th className="text-left py-3 px-4">Date</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((t) => (
                <tr key={t.id || t.created_at + t.user_id} className="border-b border-white/5 hover:bg-white/5">
                  <td className="py-3 px-4 font-mono text-sm">{t.user_id}</td>
                  <td className="py-3 px-4">{t.bundle || '-'}</td>
                  <td className="py-3 px-4">{t.credits ?? '-'}</td>
                  <td className="py-3 px-4 text-green-400">${Number(t.price || 0).toFixed(2)}</td>
                  <td className="py-3 px-4 text-[#666666]">
                    {t.created_at ? new Date(t.created_at).toLocaleString() : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {transactions.length === 0 && (
            <div className="text-center py-12 text-gray-500">No transactions yet.</div>
          )}
        </div>
      )}
    </div>
  );
};

export default AdminBilling;
