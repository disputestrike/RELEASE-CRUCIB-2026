import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import axios from 'axios';
import { Users, TrendingUp, UserPlus, Shield, Link2, Activity, DollarSign } from 'lucide-react';

const AdminDashboard = () => {
  const { token } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const res = await axios.get(`${API}/admin/dashboard`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setData(res.data);
      } catch (e) {
        setError(e.response?.data?.detail || e.message);
      }
    };
    if (token) fetchDashboard();
  }, [token]);

  if (error) {
    return (
      <div className="p-8">
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-400">
          {error}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <div className="w-12 h-12 border-2 border-[#666666] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const cards = [
    { label: 'Total users', value: data.total_users, icon: Users, href: '/app/admin/users' },
    { label: 'Signups today', value: data.signups_today, icon: UserPlus },
    { label: 'Signups (7d)', value: data.signups_week, icon: TrendingUp },
    { label: 'Referrals', value: data.referral_count, icon: Link2 },
    { label: 'Projects today', value: data.projects_today, icon: Activity },
    { label: 'Revenue today', value: `$${data.revenue_today ?? 0}`, icon: DollarSign },
    { label: 'Revenue (7d)', value: `$${data.revenue_week ?? 0}`, icon: DollarSign },
    { label: 'Revenue (30d)', value: `$${data.revenue_month ?? 0}`, icon: DollarSign },
    { label: 'Fraud flags', value: data.fraud_flags_count, icon: Shield },
  ];

  return (
    <div className="space-y-8" data-testid="admin-dashboard">
      <div>
        <h1 className="text-3xl font-bold">Admin Dashboard</h1>
        <p className="text-[#666666] mt-1">Operational overview</p>
        <p className="text-sm text-[#666666] mt-2 max-w-2xl">
          <strong>Access:</strong> Use the <strong>Admin</strong> link in the app footer (bottom of every app page), or go to <code className="bg-black/5 px-1 rounded">/app/admin</code>. Only accounts with admin role can use this section. Typical use: view signups and revenue, manage users and grant credits, run analytics and exports. See <a href="/docs" className="underline text-[#1A1A1A]">Docs</a> or <code className="bg-black/5 px-1 rounded">docs/ADMIN_ACCESS_AND_USE.md</code> for details.
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cards.map(({ label, value, icon: Icon, href }) => (
          <div
            key={label}
            className="p-6 rounded-xl border border-black/10 bg-white hover:bg-[#FAFAF8] transition"
          >
            {href ? (
              <Link to={href} className="block">
                <div className="flex items-center justify-between">
                  <span className="text-[#666666]">{label}</span>
                  <Icon className="w-5 h-5 text-[#666666]" />
                </div>
                <p className="text-2xl font-bold mt-2">{value}</p>
              </Link>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-[#666666]">{label}</span>
                  <Icon className="w-5 h-5 text-[#666666]" />
                </div>
                <p className="text-2xl font-bold mt-2">{value}</p>
              </>
            )}
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-4">
        <Link to="/app/admin/analytics" className="p-4 rounded-lg border border-black/10 bg-[#FAFAF8] hover:bg-[#F3F1ED] text-[#1A1A1A]">
          Analytics & reports →
        </Link>
        <Link to="/app/admin/billing" className="p-4 rounded-lg border border-black/10 bg-[#FAFAF8] hover:bg-[#F3F1ED] text-[#1A1A1A]">
          View billing transactions →
        </Link>
        <Link to="/app/admin/legal" className="p-4 rounded-lg border border-black/10 bg-[#FAFAF8] hover:bg-[#F3F1ED] text-[#1A1A1A]">
          Legal & AUP (blocked requests) →
        </Link>
        <div className="p-4 rounded-lg border border-black/10 bg-[#F5F5F4] text-[#666666] flex items-center gap-2">
          <Activity className="w-5 h-5" />
          System health: {data.system_health}
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
