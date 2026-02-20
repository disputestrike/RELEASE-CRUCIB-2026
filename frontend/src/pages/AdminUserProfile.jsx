import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth, API } from '../App';
import axios from 'axios';
import { ArrowLeft, Coins, FolderOpen, Gift, Ban } from 'lucide-react';

const AdminUserProfile = () => {
  const { id } = useParams();
  const { token, user: currentUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [grantCredits, setGrantCredits] = useState('');
  const [grantReason, setGrantReason] = useState('Support bonus');
  const [suspendReason, setSuspendReason] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const isOwnerOrOps = ['owner', 'operations'].includes(currentUser?.admin_role);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await axios.get(`${API}/admin/users/${id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setProfile(res.data);
      } catch (e) {
        setError(e.response?.data?.detail || e.message);
      } finally {
        setLoading(false);
      }
    };
    if (token && id) fetchProfile();
  }, [token, id]);

  const handleGrantCredits = async (e) => {
    e.preventDefault();
    const credits = parseInt(grantCredits, 10);
    if (!credits || credits < 1) return;
    setActionLoading(true);
    setMessage(null);
    try {
      await axios.post(
        `${API}/admin/users/${id}/grant-credits`,
        { credits, reason: grantReason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setMessage(`Granted ${credits} credits.`);
      setGrantCredits('');
      const res = await axios.get(`${API}/admin/users/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setProfile(res.data);
    } catch (e) {
      setMessage(e.response?.data?.detail || e.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleSuspend = async (e) => {
    e.preventDefault();
    if (!suspendReason.trim()) return;
    setActionLoading(true);
    setMessage(null);
    try {
      await axios.post(
        `${API}/admin/users/${id}/suspend`,
        { reason: suspendReason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setMessage('User suspended.');
      const res = await axios.get(`${API}/admin/users/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setProfile(res.data);
    } catch (e) {
      setMessage(e.response?.data?.detail || e.message);
    } finally {
      setActionLoading(false);
    }
  };

  if (error) {
    return (
      <div className="p-8">
        <div className="rounded-lg border border-gray-500/30 bg-gray-500/10 p-4 text-gray-400">{error}</div>
        <Link to="/app/admin/users" className="inline-flex items-center mt-4 text-#c0c0c0">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to users
        </Link>
      </div>
    );
  }

  if (loading || !profile) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <div className="w-12 h-12 border-2 border-gray-300 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8" data-testid="admin-user-profile">
      <Link to="/app/admin/users" className="inline-flex items-center text-[#666666] hover:text-[#1A1A1A]">
        <ArrowLeft className="w-4 h-4 mr-2" /> Back to users
      </Link>
      <div>
        <h1 className="text-2xl font-bold">{profile.email}</h1>
        <p className="text-[#666666]">ID: {profile.id}</p>
      </div>
      {message && (
        <div className={`p-4 rounded-lg ${message.includes('Granted') || message.includes('suspended') ? 'bg-gray-500/10 text-gray-400' : 'bg-gray-500/10 text-gray-400'}`}>
          {message}
        </div>
      )}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="p-6 rounded-xl border border-white/10 bg-white/5">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Coins className="w-5 h-5" /> Balance & plan
          </h2>
          <p><span className="text-[#666666]">Credits:</span> {profile.credit_balance ?? '-'}</p>
          <p><span className="text-[#666666]">Plan:</span> {profile.plan || 'free'}</p>
          <p><span className="text-[#666666]">Created:</span> {profile.created_at ? new Date(profile.created_at).toLocaleString() : '-'}</p>
          <p><span className="text-[#666666]">Last login:</span> {profile.last_login ? new Date(profile.last_login).toLocaleString() : '-'}</p>
          <p><span className="text-[#666666]">Lifetime revenue:</span> ${profile.lifetime_revenue ?? 0}</p>
          {profile.suspended && (
            <p className="text-gray-400 mt-2">Suspended: {profile.suspended_reason}</p>
          )}
        </div>
        <div className="p-6 rounded-xl border border-white/10 bg-white/5">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <FolderOpen className="w-5 h-5" /> Activity
          </h2>
          <p><span className="text-[#666666]">Projects:</span> {profile.projects_count ?? 0}</p>
          <p><span className="text-[#666666]">Referrals:</span> {profile.referral_count ?? 0}</p>
        </div>
      </div>
      {profile.recent_ledger?.length > 0 && (
        <div className="p-6 rounded-xl border border-white/10">
          <h2 className="font-semibold mb-4">Recent ledger</h2>
          <ul className="space-y-2">
            {profile.recent_ledger.slice(0, 10).map((entry) => (
              <li key={entry.id} className="flex justify-between text-sm">
                <span>{entry.type} – {entry.description || '-'}</span>
                <span className={entry.credits > 0 ? 'text-gray-400' : 'text-gray-400'}>
                  {entry.credits > 0 ? '+' : ''}{entry.credits} credits
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {!profile.suspended && (
        <>
          <div className="p-6 rounded-xl border border-white/10">
            <h2 className="font-semibold mb-4 flex items-center gap-2">
              <Gift className="w-5 h-5" /> Grant bonus credits
            </h2>
            <form onSubmit={handleGrantCredits} className="flex flex-wrap gap-4">
              <input
                type="number"
                min="1"
                placeholder="Credits"
                value={grantCredits}
                onChange={(e) => setGrantCredits(e.target.value)}
                className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 w-24"
              />
              <input
                type="text"
                placeholder="Reason"
                value={grantReason}
                onChange={(e) => setGrantReason(e.target.value)}
                className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 flex-1 min-w-[200px]"
              />
              <button
                type="submit"
                disabled={actionLoading || !grantCredits}
                className="px-4 py-2 rounded-lg bg-black hover:bg-gray-200 disabled:opacity-50"
              >
                {actionLoading ? '...' : 'Grant'}
              </button>
            </form>
          </div>
          {isOwnerOrOps && (
            <div className="p-6 rounded-xl border border-gray-500/20 bg-gray-500/5">
              <h2 className="font-semibold mb-4 flex items-center gap-2 text-gray-400">
                <Ban className="w-5 h-5" /> Suspend account
              </h2>
              <form onSubmit={handleSuspend} className="flex flex-wrap gap-4">
                <input
                  type="text"
                  placeholder="Reason"
                  value={suspendReason}
                  onChange={(e) => setSuspendReason(e.target.value)}
                  className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 flex-1 min-w-[200px]"
                />
                <button
                  type="submit"
                  disabled={actionLoading || !suspendReason.trim()}
                  className="px-4 py-2 rounded-lg bg-gray-600 hover:bg-gray-500 disabled:opacity-50"
                >
                  {actionLoading ? '...' : 'Suspend'}
                </button>
              </form>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default AdminUserProfile;
