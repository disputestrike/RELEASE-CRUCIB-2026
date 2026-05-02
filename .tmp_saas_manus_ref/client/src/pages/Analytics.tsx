/**
 * Analytics Page — Arctic Clarity Design System
 * Detailed analytics with multiple chart types and KPI breakdowns
 */

import { useState } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Legend,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, ArrowUpRight } from "lucide-react";
import { toast } from "sonner";

const monthlyRevenue = [
  { month: "Jan", mrr: 28400, arr: 340800, churn: 2.1 },
  { month: "Feb", mrr: 31200, arr: 374400, churn: 1.8 },
  { month: "Mar", mrr: 29800, arr: 357600, churn: 2.3 },
  { month: "Apr", mrr: 34500, arr: 414000, churn: 1.6 },
  { month: "May", mrr: 38200, arr: 458400, churn: 1.4 },
  { month: "Jun", mrr: 36800, arr: 441600, churn: 1.9 },
  { month: "Jul", mrr: 41200, arr: 494400, churn: 1.2 },
  { month: "Aug", mrr: 39600, arr: 475200, churn: 1.5 },
  { month: "Sep", mrr: 44100, arr: 529200, churn: 1.1 },
  { month: "Oct", mrr: 46800, arr: 561600, churn: 1.0 },
  { month: "Nov", mrr: 45200, arr: 542400, churn: 1.3 },
  { month: "Dec", mrr: 48200, arr: 578400, churn: 0.9 },
];

const conversionFunnel = [
  { stage: "Visitors", count: 48200, pct: 100 },
  { stage: "Sign-ups", count: 9640, pct: 20 },
  { stage: "Activated", count: 4820, pct: 10 },
  { stage: "Paid", count: 1446, pct: 3 },
  { stage: "Retained", count: 1157, pct: 2.4 },
];

const cohortData = [
  { cohort: "Jan '26", m0: 100, m1: 82, m2: 71, m3: 65, m4: 60, m5: 57 },
  { cohort: "Feb '26", m0: 100, m1: 85, m2: 74, m3: 68, m4: 63, m5: null },
  { cohort: "Mar '26", m0: 100, m1: 88, m2: 77, m3: 71, m4: null, m5: null },
  { cohort: "Apr '26", m0: 100, m1: 86, m2: 75, m3: null, m4: null, m5: null },
];

const topPages = [
  { page: "/dashboard", views: 24800, bounce: "18%", time: "4m 32s" },
  { page: "/analytics", views: 18200, bounce: "22%", time: "3m 45s" },
  { page: "/pricing", views: 12400, bounce: "45%", time: "2m 10s" },
  { page: "/settings", views: 8900, bounce: "28%", time: "5m 12s" },
  { page: "/team", views: 6200, bounce: "31%", time: "3m 08s" },
];

const ranges = ["7D", "30D", "90D", "1Y", "All"];

function CustomTooltip({ active, payload, label }: any) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl shadow-lg px-4 py-3 text-xs">
        <p className="font-semibold text-slate-500 mb-1.5">{label}</p>
        {payload.map((p: any) => (
          <p key={p.dataKey} className="font-bold" style={{ color: p.color }}>
            {p.dataKey === "mrr" || p.dataKey === "arr"
              ? `$${p.value.toLocaleString()}`
              : p.dataKey === "churn"
              ? `${p.value}%`
              : p.value.toLocaleString()}
            <span className="font-normal text-slate-500 ml-1">{p.name}</span>
          </p>
        ))}
      </div>
    );
  }
  return null;
}

export default function Analytics() {
  const [range, setRange] = useState("1Y");
  const handleComingSoon = () => toast.info("Feature coming soon!");

  return (
    <DashboardLayout
      breadcrumb={[
        { label: "FlowDesk", href: "/dashboard" },
        { label: "Analytics" },
      ]}
    >
      <div className="p-4 lg:p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1
              className="text-xl font-bold text-foreground"
              style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
            >
              Analytics
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Deep-dive into your product metrics and growth trends.
            </p>
          </div>
          <div className="flex items-center gap-1 bg-muted/60 rounded-lg p-1">
            {ranges.map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                  range === r
                    ? "bg-white shadow text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: "MRR", value: "$48,200", change: "+18.4%", pos: true, sub: "Monthly Recurring Revenue" },
            { label: "ARR", value: "$578,400", change: "+22.1%", pos: true, sub: "Annual Run Rate" },
            { label: "Churn Rate", value: "0.9%", change: "-0.4pp", pos: true, sub: "Monthly churn" },
            { label: "LTV", value: "$2,840", change: "+11.2%", pos: true, sub: "Avg. lifetime value" },
          ].map(({ label, value, change, pos, sub }) => (
            <div key={label} className="card-elevated rounded-2xl p-5">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">{label}</p>
              <p
                className="text-2xl font-extrabold text-foreground mb-1"
                style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
              >
                {value}
              </p>
              <div className="flex items-center gap-1.5">
                <span className={pos ? "badge-success" : "badge-danger"}>
                  {pos ? <TrendingUp className="w-3 h-3 inline mr-0.5" /> : <TrendingDown className="w-3 h-3 inline mr-0.5" />}
                  {change}
                </span>
                <span className="text-xs text-muted-foreground">{sub}</span>
              </div>
            </div>
          ))}
        </div>

        {/* MRR + Churn charts */}
        <div className="grid lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 card-elevated rounded-2xl p-5">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="text-sm font-bold text-foreground" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                  MRR Growth
                </h2>
                <p className="text-xs text-muted-foreground mt-0.5">Monthly recurring revenue trend</p>
              </div>
              <Badge className="badge-success">
                <TrendingUp className="w-3 h-3 inline mr-1" />+18.4%
              </Badge>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={monthlyRevenue} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="mrrGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.18} />
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
                  dataKey="mrr"
                  name="MRR"
                  stroke="#4F46E5"
                  strokeWidth={2.5}
                  fill="url(#mrrGrad)"
                  dot={false}
                  activeDot={{ r: 5, fill: "#4F46E5", strokeWidth: 2, stroke: "white" }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="card-elevated rounded-2xl p-5">
            <div className="mb-5">
              <h2 className="text-sm font-bold text-foreground" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                Churn Rate
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">Monthly churn % over time</p>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={monthlyRevenue} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                <YAxis
                  tick={{ fontSize: 11, fill: "#94a3b8" }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `${v}%`}
                  width={35}
                  domain={[0, 3]}
                />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="churn"
                  name="Churn"
                  stroke="#EF4444"
                  strokeWidth={2.5}
                  dot={false}
                  activeDot={{ r: 5, fill: "#EF4444", strokeWidth: 2, stroke: "white" }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Conversion funnel + Top pages */}
        <div className="grid lg:grid-cols-2 gap-4">
          {/* Funnel */}
          <div className="card-elevated rounded-2xl p-5">
            <h2 className="text-sm font-bold text-foreground mb-5" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
              Conversion Funnel
            </h2>
            <div className="space-y-3">
              {conversionFunnel.map(({ stage, count, pct }, i) => (
                <div key={stage}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-medium text-foreground">{stage}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-muted-foreground">{count.toLocaleString()}</span>
                      <span className="text-xs font-semibold text-foreground w-10 text-right">{pct}%</span>
                    </div>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2">
                    <div
                      className="h-2 rounded-full transition-all"
                      style={{
                        width: `${pct}%`,
                        background: `oklch(${0.511 + i * 0.04} ${0.262 - i * 0.03} 276.966)`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Top pages */}
          <div className="card-elevated rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-border">
              <h2 className="text-sm font-bold text-foreground" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                Top Pages
              </h2>
            </div>
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="text-left text-xs font-semibold text-muted-foreground px-5 py-2.5">Page</th>
                  <th className="text-right text-xs font-semibold text-muted-foreground px-4 py-2.5">Views</th>
                  <th className="text-right text-xs font-semibold text-muted-foreground px-4 py-2.5 hidden sm:table-cell">Bounce</th>
                  <th className="text-right text-xs font-semibold text-muted-foreground px-4 py-2.5 hidden md:table-cell">Avg. Time</th>
                </tr>
              </thead>
              <tbody>
                {topPages.map(({ page, views, bounce, time }) => (
                  <tr key={page} className="border-b border-border last:border-0 hover:bg-muted/20 transition-colors">
                    <td className="px-5 py-3">
                      <span className="text-xs font-mono text-indigo-600">{page}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-xs font-semibold text-foreground">{views.toLocaleString()}</span>
                    </td>
                    <td className="px-4 py-3 text-right hidden sm:table-cell">
                      <span className="text-xs text-muted-foreground">{bounce}</span>
                    </td>
                    <td className="px-4 py-3 text-right hidden md:table-cell">
                      <span className="text-xs text-muted-foreground">{time}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Cohort retention */}
        <div className="card-elevated rounded-2xl p-5">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-sm font-bold text-foreground" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                Cohort Retention
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">% of users retained by month after signup</p>
            </div>
            <Button variant="outline" size="sm" className="text-xs" onClick={handleComingSoon}>
              <ArrowUpRight className="w-3.5 h-3.5 mr-1.5" />
              Export
            </Button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr>
                  <th className="text-left font-semibold text-muted-foreground pb-3 pr-4">Cohort</th>
                  {["M0", "M1", "M2", "M3", "M4", "M5"].map((m) => (
                    <th key={m} className="text-center font-semibold text-muted-foreground pb-3 px-2 min-w-[60px]">{m}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cohortData.map(({ cohort, m0, m1, m2, m3, m4, m5 }) => (
                  <tr key={cohort}>
                    <td className="py-2 pr-4 font-medium text-foreground">{cohort}</td>
                    {[m0, m1, m2, m3, m4, m5].map((val, i) => (
                      <td key={i} className="py-2 px-2 text-center">
                        {val !== null ? (
                          <div
                            className="inline-flex items-center justify-center w-12 h-8 rounded-lg text-xs font-semibold"
                            style={{
                              background: `oklch(${0.511 + (val / 100) * 0.1} ${0.262 * (val / 100)} 276.966 / ${0.1 + (val / 100) * 0.4})`,
                              color: val > 50 ? "oklch(0.3 0.2 276.966)" : "oklch(0.5 0.15 276.966)",
                            }}
                          >
                            {val}%
                          </div>
                        ) : (
                          <span className="text-muted-foreground/30">—</span>
                        )}
                      </td>
                    ))}
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
