import React, { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { AlertCircle, Users, TrendingUp, DollarSign, Settings, Activity } from 'lucide-react';

interface AdminPanelProps {
  isAdmin?: boolean;
}

interface User {
  id: string;
  email: string;
  username: string;
  role: string;
  status: string;
  created_at: string;
  last_login?: string;
}

interface SystemMetrics {
  total_users: number;
  active_users: number;
  total_builds: number;
  total_revenue: number;
  error_rate: number;
  avg_response_time: number;
}

interface Alert {
  id: string;
  severity: string;
  message: string;
  timestamp: string;
}

export const AdminPanel: React.FC<AdminPanelProps> = ({ isAdmin = true }) => {
  const [users, setUsers] = useState<User[]>([]);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  useEffect(() => {
    if (isAdmin) {
      fetchAdminData();
    }
  }, [isAdmin]);

  const fetchAdminData = async () => {
    try {
      setLoading(true);
      
      // Fetch users
      const usersRes = await fetch('/api/admin/users');
      const usersData = await usersRes.json();
      setUsers(usersData);

      // Fetch metrics
      const metricsRes = await fetch('/api/admin/metrics');
      const metricsData = await metricsRes.json();
      setMetrics(metricsData);

      // Fetch alerts
      const alertsRes = await fetch('/api/admin/alerts');
      const alertsData = await alertsRes.json();
      setAlerts(alertsData);

    } catch (error) {
      console.error('Failed to fetch admin data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBanUser = async (userId: string) => {
    try {
      await fetch(`/api/admin/users/${userId}/ban`, { method: 'POST' });
      fetchAdminData();
    } catch (error) {
      console.error('Failed to ban user:', error);
    }
  };

  const handleResetPassword = async (userId: string) => {
    try {
      await fetch(`/api/admin/users/${userId}/reset-password`, { method: 'POST' });
      alert('Password reset email sent');
    } catch (error) {
      console.error('Failed to reset password:', error);
    }
  };

  const filteredUsers = users.filter(user =>
    user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
    user.username.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-500" />
              Access Denied
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p>You do not have permission to access the admin panel.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Admin Dashboard</h1>
          <p className="text-muted-foreground">System monitoring and management</p>
        </div>

        {/* Metrics Cards */}
        {metrics && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center justify-between">
                  <span>Total Users</span>
                  <Users className="w-4 h-4 text-blue-500" />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{metrics.total_users}</div>
                <p className="text-xs text-muted-foreground">{metrics.active_users} active</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center justify-between">
                  <span>Total Builds</span>
                  <TrendingUp className="w-4 h-4 text-green-500" />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{metrics.total_builds}</div>
                <p className="text-xs text-muted-foreground">All time</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center justify-between">
                  <span>Total Revenue</span>
                  <DollarSign className="w-4 h-4 text-green-600" />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">${metrics.total_revenue.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground">All time</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center justify-between">
                  <span>System Health</span>
                  <Activity className="w-4 h-4 text-neutral-500" />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{(100 - metrics.error_rate * 100).toFixed(1)}%</div>
                <p className="text-xs text-muted-foreground">Uptime</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Alerts */}
        {alerts.length > 0 && (
          <Card className="mb-8 border-neutral-200 bg-neutral-50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-neutral-600" />
                Active Alerts ({alerts.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {alerts.map(alert => (
                  <div key={alert.id} className="flex items-center justify-between p-2 bg-white rounded">
                    <div>
                      <p className="font-medium">{alert.message}</p>
                      <p className="text-xs text-muted-foreground">{alert.timestamp}</p>
                    </div>
                    <Badge variant={alert.severity === 'critical' ? 'destructive' : 'secondary'}>
                      {alert.severity}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Tabs */}
        <Tabs defaultValue="users" className="space-y-4">
          <TabsList>
            <TabsTrigger value="users">User Management</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
            <TabsTrigger value="billing">Billing</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>

          {/* Users Tab */}
          <TabsContent value="users">
            <Card>
              <CardHeader>
                <CardTitle>Users</CardTitle>
                <CardDescription>Manage system users</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input
                  placeholder="Search users..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />

                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="border-b">
                      <tr>
                        <th className="text-left py-2">Email</th>
                        <th className="text-left py-2">Username</th>
                        <th className="text-left py-2">Role</th>
                        <th className="text-left py-2">Status</th>
                        <th className="text-left py-2">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredUsers.map(user => (
                        <tr key={user.id} className="border-b hover:bg-muted/50">
                          <td className="py-2">{user.email}</td>
                          <td className="py-2">{user.username}</td>
                          <td className="py-2">
                            <Badge variant="outline">{user.role}</Badge>
                          </td>
                          <td className="py-2">
                            <Badge variant={user.status === 'active' ? 'default' : 'secondary'}>
                              {user.status}
                            </Badge>
                          </td>
                          <td className="py-2 space-x-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleResetPassword(user.id)}
                            >
                              Reset Password
                            </Button>
                            {user.status === 'active' && (
                              <Button
                                size="sm"
                                variant="destructive"
                                onClick={() => handleBanUser(user.id)}
                              >
                                Ban
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Analytics Tab */}
          <TabsContent value="analytics">
            <Card>
              <CardHeader>
                <CardTitle>System Analytics</CardTitle>
                <CardDescription>Performance metrics and trends</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-96">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={[
                      { name: 'Mon', users: 400, builds: 240 },
                      { name: 'Tue', users: 300, builds: 221 },
                      { name: 'Wed', users: 200, builds: 229 },
                      { name: 'Thu', users: 278, builds: 200 },
                      { name: 'Fri', users: 189, builds: 220 },
                    ]}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="users" stroke="#3b82f6" />
                      <Line type="monotone" dataKey="builds" stroke="#10b981" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Billing Tab */}
          <TabsContent value="billing">
            <Card>
              <CardHeader>
                <CardTitle>Billing & Revenue</CardTitle>
                <CardDescription>Payment and subscription management</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Revenue analytics coming soon...</p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings">
            <Card>
              <CardHeader>
                <CardTitle>System Settings</CardTitle>
                <CardDescription>Configure system parameters</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium">Rate Limit (requests/minute)</label>
                  <Input type="number" defaultValue="100" className="mt-1" />
                </div>
                <div>
                  <label className="text-sm font-medium">Max Build Time (seconds)</label>
                  <Input type="number" defaultValue="300" className="mt-1" />
                </div>
                <Button>Save Settings</Button>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default AdminPanel;
