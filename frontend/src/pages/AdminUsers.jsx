import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth, API } from '../App';
import axios from 'axios';
import { Search, User, ChevronRight } from 'lucide-react';

const AdminUsers = () => {
  const { token } = useAuth();
  const [searchParams] = useSearchParams();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [emailQ, setEmailQ] = useState(searchParams.get('email') || '');
  const [planQ, setPlanQ] = useState(searchParams.get('plan') || '');

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const params = new URLSearchParams();
        if (emailQ) params.set('email', emailQ);
        if (planQ) params.set('plan', planQ);
        const res = await axios.get(`${API}/admin/users?${params}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setUsers(res.data.users || []);
      } catch (e) {
        setError(e.response?.data?.detail || e.message);
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchUsers();
  }, [token, emailQ, planQ]);

  if (error) {
    return (
      <div className="p-8">
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-400">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-users">
      <div>
        <h1 className="text-3xl font-bold">User management</h1>
        <p className="text-[#666666] mt-1">Search and filter users</p>
      </div>
      <div className="flex flex-wrap gap-4">
        <div className="flex items-center gap-2 bg-white/5 rounded-lg border border-white/10 px-3 py-2">
          <Search className="w-4 h-4 text-[#666666]" />
          <input
            type="text"
            placeholder="Email"
            value={emailQ}
            onChange={(e) => setEmailQ(e.target.value)}
            className="bg-transparent border-none outline-none min-w-[180px]"
          />
        </div>
        <select
          value={planQ}
          onChange={(e) => setPlanQ(e.target.value)}
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2"
        >
          <option value="">All plans</option>
          <option value="free">Free</option>
          <option value="starter">Starter</option>
          <option value="builder">Builder</option>
          <option value="pro">Pro</option>
          <option value="agency">Agency</option>
        </select>
      </div>
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="rounded-xl border border-white/10 overflow-hidden">
          <table className="w-full">
            <thead className="bg-white/5 border-b border-white/10">
              <tr>
                <th className="text-left py-3 px-4">Email</th>
                <th className="text-left py-3 px-4">Plan</th>
                <th className="text-left py-3 px-4">Credits</th>
                <th className="text-left py-3 px-4">Created</th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-white/5 hover:bg-white/5">
                  <td className="py-3 px-4">{u.email}</td>
                  <td className="py-3 px-4 capitalize">{u.plan || 'free'}</td>
                  <td className="py-3 px-4">{u.credit_balance ?? '-'}</td>
                  <td className="py-3 px-4 text-[#666666]">
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : '-'}
                  </td>
                  <td className="py-3 px-4">
                    <Link
                      to={`/app/admin/users/${u.id}`}
                      className="inline-flex items-center text-blue-400 hover:text-blue-300"
                    >
                      <User className="w-4 h-4 mr-1" />
                      View
                      <ChevronRight className="w-4 h-4" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {users.length === 0 && (
            <div className="text-center py-12 text-gray-500">No users match the filters.</div>
          )}
        </div>
      )}
    </div>
  );
};

export default AdminUsers;
