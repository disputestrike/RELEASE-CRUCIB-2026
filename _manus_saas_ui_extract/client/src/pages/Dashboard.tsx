/**
 * Dashboard Page — Arctic Clarity Design System
 * Stat cards, area chart, donut chart, recent users table, activity feed
 */

import DashboardLayout from "@/components/DashboardLayout";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend,
} from "recharts";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Users,
  MousePointerClick,
  Activity,
  MoreHorizontal,
  ArrowUpRight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";

// ── Data ──────────────────────────────────────────────────────────────────────

const revenueData = [
  { month: "Jan", revenue: 28400, users: 8200 },
  { month: "Feb", revenue: 31200, users: 8900 },
  { month: "Mar", revenue: 29800, users: 9100 },
  { month: "Apr", revenue: 34500, users: 9800 },
  { month: "May", revenue: 38200, users: 10400 },
  { month: "Jun", revenue: 36800, users: 10900 },
  { month: "Jul", revenue: 41200, users: 11200 },
  { month: "Aug", revenue: 39600, users: 11600 },
  { month: "Sep", revenue: 44100, users: 11900 },
  { month: "Oct", revenue: 46800, users: 12100 },
  { month: "Nov", revenue: 45200, users: 12300 },
  { month: "Dec", revenue: 48200, users: 12450 },
];

const trafficData = [
  { name: "Organic", value: 38, color: "#4F46E5" },
  { name: "Direct", value: 27, color: "#7C3AED" },
  { name: "Referral", value: 18, color: "#06B6D4" },
  { name: "Social", value: 12, color: "#10B981" },
  { name: "Email", value: 5, color: "#F59E0B" },
];

const weeklyData = [
  { day: "Mon", new: 142, returning: 380 },
  { day: "Tue", new: 198, returning: 420 },
  { day: "Wed", new: 165, returning: 390 },
  { day: "Thu", new: 220, returning: 450 },
  { day: "Fri", new: 185, returning: 410 },
  { day: "Sat", new: 98, returning: 280 },
  { day: "Sun", new: 76, returning: 240 },
];

const recentUsers = [
  { name: "Sarah Johnson", email: "sarah@acme.com", plan: "Pro", status: "active", revenue: "$1,250", joined: "2h ago", avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=32&h=32&fit=crop&crop=face" },
  { name: "Marcus Chen", email: "marcus@linear.app", plan: "Enterprise", status: "active", revenue: "$4,800", joined: "5h ago", avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=32&h=32&fit=crop&crop=face" },
  { name: "Priya Patel", email: "priya@vercel.com", plan: "Pro", status: "active", revenue: "$980", joined: "1d ago", avatar: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=32&h=32&fit=crop&crop=face" },
  { name: "David Kim", email: "david@notion.so", plan: "Starter", status: "inactive", revenue: "$0", joined: "2d ago", avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=32&h=32&fit=crop&crop=face" },
  { name: "Emma Wilson", email: "emma@stripe.com", plan: "Pro", status: "active", revenue: "$1,100", joined: "3d ago", avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=32&h=32&fit=crop&crop=face" },
];

const activity = [
  { icon: "💳", text: "New Enterprise subscription from Acme Corp", time: "2 min ago", type: "revenue" },
  { icon: "👤", text: "Sarah Johnson upgraded from Starter to Pro", time: "18 min ago", type: "upgrade" },
  { icon: "⚠️", text: "Unusual traffic spike detected in EU region", time: "1h ago", type: "alert" },
  { icon: "✅", text: "Automated report sent to 12 team members", time: "2h ago", type: "info" },
  { icon: "🔗", text: "Slack integration connected by Marcus Chen", time: "4h ago", type: "integration" },
];

// ── Stat Card ─────────────────────────────────────────────────────────────────

interface StatCardProps {
  icon: React.ReactNode;
  iconBg: string;
  label: string;
  value: string;
  change: string;
  positive: boolean;
  sub?: string;
}

function StatCard({ icon, iconBg, label, value, change, positive, sub }: StatCardProps) {
  return (
    <div className="card-elevated rounded-2xl p-5">
      <div className="flex items-start justify-between mb-4">
        <div className={`w-10 h-10 rounded-xl ${iconBg} flex items-center justify-center`}>
          {icon}
        </div>
        <span className={positive ? "badge-success" : "badge-danger"}>
          {positive ? <TrendingUp className="w-3 h-3 inline mr-1" /> : <TrendingDown className="w-3 h-3 inline mr-1" />}
          {change}
        </span>
      </div>
      <p className="text-2xl font-extrabold text-slate-900 mb-0.5" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
        {value}
      </p>
      <p className="text-sm text-slate-500">{label}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  );
}

// ── Custom Tooltip ─────────────────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }: any) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl shadow-lg px-4 py-3">
        <p className="text-xs font-semibold text-slate-500 mb-2">{label}</p>
        {payload.map((p: any) => (
          <p key={p.dataKey} className="text-sm font-bold" style={{ color: p.color }}>
            {p.dataKey === "revenue" ? `$${p.value.toLocaleString()}` : p.value.toLocaleString()}
            <span className="text-xs font-normal text-slate-500 ml-1">{p.dataKey}</span>
          </p>
        ))}
      </div>
    );
  }
  return null;
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const handleComingSoon = () => toast.info("Feature coming soon!");

  return (
    <DashboardLayout
      breadcrumb={[{ label: "FlowDesk" }, { label: "Dashboard" }]}
    >
      <div className="p-4 lg:p-6 space-y-6">
        {/* Page header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1
              className="text-xl font-bold text-foreground"
              style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
            >
              Good morning, John 👋
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">Here's what's happening with your workspace today.</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleComingSoon}>
              Export
            </Button>
            <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700 text-white" onClick={handleComingSoon}>
              <ArrowUpRight className="w-3.5 h-3.5 mr-1.5" />
              New Report
            </Button>
          </div>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            icon={<DollarSign className="w-5 h-5 text-indigo-600" />}
            iconBg="bg-indigo-50"
            label="Total Revenue"
            value="$48,200"
            change="+18.4%"
            positive={true}
            sub="vs last month"
          />
          <StatCard
            icon={<Users className="w-5 h-5 text-emerald-600" />}
            iconBg="bg-emerald-50"
            label="Active Users"
            value="12,450"
            change="+8.3%"
            positive={true}
            sub="vs last month"
          />
          <StatCard
            icon={<MousePointerClick className="w-5 h-5 text-amber-600" />}
            iconBg="bg-amber-50"
            label="Conversion Rate"
            value="3.24%"
            change="-0.6pp"
            positive={false}
            sub="vs last month"
          />
          <StatCard
            icon={<Activity className="w-5 h-5 text-violet-600" />}
            iconBg="bg-violet-50"
            label="Avg. Session"
            value="4m 32s"
            change="+12.1%"
            positive={true}
            sub="vs last month"
          />
        </div>

        {/* Charts row */}
        <div className="grid lg:grid-cols-3 gap-4">
          {/* Revenue area chart */}
          <div className="lg:col-span-2 card-elevated rounded-2xl p-5">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="text-sm font-bold text-foreground" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                  Revenue Over Time
                </h2>
                <p className="text-xs text-muted-foreground mt-0.5">Monthly revenue for the past 12 months</p>
              </div>
              <Button variant="ghost" size="sm" className="text-xs text-muted-foreground" onClick={handleComingSoon}>
                Monthly ▾
              </Button>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={revenueData} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#4F46E5" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                <YAxis
                  tick={{ fontSize: 11, fill: "#94a3b8" }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                  width={40}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="revenue"
                  stroke="#4F46E5"
                  strokeWidth={2.5}
                  fill="url(#revenueGrad)"
                  dot={false}
                  activeDot={{ r: 5, fill: "#4F46E5", strokeWidth: 2, stroke: "white" }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Traffic sources donut */}
          <div className="card-elevated rounded-2xl p-5">
            <div className="mb-5">
              <h2 className="text-sm font-bold text-foreground" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                Traffic Sources
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">Where your users come from</p>
            </div>
            <ResponsiveContainer width="100%" height={140}>
              <PieChart>
                <Pie
                  data={trafficData}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={65}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {trafficData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => [`${value}%`, ""]} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-2 mt-2">
              {trafficData.map(({ name, value, color }) => (
                <div key={name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color }} />
                    <span className="text-xs text-muted-foreground">{name}</span>
                  </div>
                  <span className="text-xs font-semibold text-foreground">{value}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Weekly users bar chart + Activity feed */}
        <div className="grid lg:grid-cols-3 gap-4">
          {/* Bar chart */}
          <div className="lg:col-span-2 card-elevated rounded-2xl p-5">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="text-sm font-bold text-foreground" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                  Weekly Active Users
                </h2>
                <p className="text-xs text-muted-foreground mt-0.5">New vs returning users this week</p>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={weeklyData} barGap={4} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} width={35} />
                <Tooltip
                  contentStyle={{ borderRadius: "12px", border: "1px solid #e2e8f0", fontSize: "12px" }}
                  cursor={{ fill: "#f8fafc" }}
                />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
                />
                <Bar dataKey="new" name="New Users" fill="#4F46E5" radius={[4, 4, 0, 0]} />
                <Bar dataKey="returning" name="Returning" fill="#C7D2FE" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Activity feed */}
          <div className="card-elevated rounded-2xl p-5">
            <h2 className="text-sm font-bold text-foreground mb-4" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
              Recent Activity
            </h2>
            <div className="space-y-4">
              {activity.map(({ icon, text, time }, i) => (
                <div key={i} className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-sm flex-shrink-0">
                    {icon}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-foreground leading-snug">{text}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{time}</p>
                  </div>
                </div>
              ))}
            </div>
            <Button variant="ghost" size="sm" className="w-full mt-4 text-xs text-muted-foreground" onClick={handleComingSoon}>
              View all activity
            </Button>
          </div>
        </div>

        {/* Recent users table */}
        <div className="card-elevated rounded-2xl overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <div>
              <h2 className="text-sm font-bold text-foreground" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                Recent Users
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">Latest signups and their activity</p>
            </div>
            <Button variant="outline" size="sm" className="text-xs" onClick={handleComingSoon}>
              View all
            </Button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="text-left text-xs font-semibold text-muted-foreground px-5 py-3">User</th>
                  <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3 hidden md:table-cell">Plan</th>
                  <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3 hidden lg:table-cell">Status</th>
                  <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3 hidden lg:table-cell">Revenue</th>
                  <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Joined</th>
                  <th className="px-4 py-3 w-10" />
                </tr>
              </thead>
              <tbody>
                {recentUsers.map(({ name, email, plan, status, revenue, joined, avatar }) => (
                  <tr key={email} className="border-b border-border last:border-0 hover:bg-muted/20 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <img src={avatar} alt={name} className="w-8 h-8 rounded-full object-cover flex-shrink-0" />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-foreground truncate">{name}</p>
                          <p className="text-xs text-muted-foreground truncate">{email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 hidden md:table-cell">
                      <Badge
                        variant="secondary"
                        className={`text-xs ${
                          plan === "Enterprise"
                            ? "bg-violet-100 text-violet-700 hover:bg-violet-100"
                            : plan === "Pro"
                            ? "bg-indigo-100 text-indigo-700 hover:bg-indigo-100"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-100"
                        }`}
                      >
                        {plan}
                      </Badge>
                    </td>
                    <td className="px-4 py-3.5 hidden lg:table-cell">
                      <div className="flex items-center gap-1.5">
                        <div className={`w-1.5 h-1.5 rounded-full ${status === "active" ? "bg-emerald-500" : "bg-slate-400"}`} />
                        <span className="text-xs text-muted-foreground capitalize">{status}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 hidden lg:table-cell">
                      <span className="text-sm font-medium text-foreground">{revenue}</span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="text-xs text-muted-foreground">{joined}</span>
                    </td>
                    <td className="px-4 py-3.5">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="w-7 h-7 text-muted-foreground">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={handleComingSoon}>View profile</DropdownMenuItem>
                          <DropdownMenuItem onClick={handleComingSoon}>Send message</DropdownMenuItem>
                          <DropdownMenuItem onClick={handleComingSoon} className="text-destructive">Remove user</DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
