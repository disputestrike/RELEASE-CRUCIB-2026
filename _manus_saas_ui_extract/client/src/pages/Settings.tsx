/**
 * Settings Page — Arctic Clarity Design System
 * Profile, notifications, security, billing, integrations tabs
 */

import { useState } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  User,
  Bell,
  Shield,
  CreditCard,
  Puzzle,
  Camera,
  Trash2,
  Key,
  Smartphone,
  Globe,
  Zap,
  Check,
} from "lucide-react";
import { toast } from "sonner";

const tabs = [
  { id: "profile", label: "Profile", icon: User },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "security", label: "Security", icon: Shield },
  { id: "billing", label: "Billing", icon: CreditCard },
  { id: "integrations", label: "Integrations", icon: Puzzle },
];

const integrations = [
  { name: "Slack", desc: "Send notifications to Slack channels", icon: "💬", connected: true },
  { name: "GitHub", desc: "Link commits and PRs to tasks", icon: "🐙", connected: true },
  { name: "Stripe", desc: "Track revenue and subscription data", icon: "💳", connected: false },
  { name: "HubSpot", desc: "Sync contacts and deal pipeline", icon: "🔶", connected: false },
  { name: "Jira", desc: "Sync issues and project boards", icon: "🔵", connected: false },
  { name: "Salesforce", desc: "Import CRM data and contacts", icon: "☁️", connected: false },
];

export default function Settings() {
  const [activeTab, setActiveTab] = useState("profile");
  const [saved, setSaved] = useState(false);
  const handleComingSoon = () => toast.info("Feature coming soon!");

  const handleSave = () => {
    setSaved(true);
    toast.success("Settings saved successfully!");
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <DashboardLayout
      breadcrumb={[
        { label: "FlowDesk", href: "/dashboard" },
        { label: "Settings" },
      ]}
    >
      <div className="p-4 lg:p-6">
        <div className="mb-6">
          <h1
            className="text-xl font-bold text-foreground"
            style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
          >
            Settings
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Manage your account preferences and workspace configuration.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-6">
          {/* Sidebar tabs */}
          <nav className="flex lg:flex-col gap-1 overflow-x-auto lg:overflow-visible lg:w-52 flex-shrink-0">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                  activeTab === id
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
                }`}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                {label}
              </button>
            ))}
          </nav>

          {/* Content */}
          <div className="flex-1 min-w-0 space-y-5">
            {/* ── Profile ── */}
            {activeTab === "profile" && (
              <>
                <div className="card-elevated rounded-2xl p-6">
                  <h2 className="text-sm font-bold text-foreground mb-5" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                    Personal Information
                  </h2>
                  <div className="flex items-center gap-5 mb-6 pb-6 border-b border-border">
                    <div className="relative">
                      <Avatar className="w-16 h-16">
                        <AvatarImage src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=64&h=64&fit=crop&crop=face" />
                        <AvatarFallback className="bg-indigo-600 text-white text-lg font-bold">JD</AvatarFallback>
                      </Avatar>
                      <button
                        className="absolute -bottom-1 -right-1 w-7 h-7 bg-indigo-600 rounded-full flex items-center justify-center hover:bg-indigo-700 transition-colors"
                        onClick={handleComingSoon}
                      >
                        <Camera className="w-3.5 h-3.5 text-white" />
                      </button>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-foreground">John Doe</p>
                      <p className="text-xs text-muted-foreground mb-2">john@flowdesk.io</p>
                      <Button variant="outline" size="sm" className="text-xs" onClick={handleComingSoon}>
                        Change photo
                      </Button>
                    </div>
                  </div>

                  <div className="grid sm:grid-cols-2 gap-4">
                    {[
                      { label: "First name", value: "John", type: "text" },
                      { label: "Last name", value: "Doe", type: "text" },
                      { label: "Email address", value: "john@flowdesk.io", type: "email" },
                      { label: "Job title", value: "Head of Product", type: "text" },
                    ].map(({ label, value, type }) => (
                      <div key={label}>
                        <label className="text-xs font-semibold text-muted-foreground mb-1.5 block uppercase tracking-wide">
                          {label}
                        </label>
                        <Input type={type} defaultValue={value} />
                      </div>
                    ))}
                    <div className="sm:col-span-2">
                      <label className="text-xs font-semibold text-muted-foreground mb-1.5 block uppercase tracking-wide">
                        Timezone
                      </label>
                      <Select defaultValue="pst">
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="pst">Pacific Time (UTC-8)</SelectItem>
                          <SelectItem value="est">Eastern Time (UTC-5)</SelectItem>
                          <SelectItem value="utc">UTC</SelectItem>
                          <SelectItem value="cet">Central European Time (UTC+1)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                <div className="card-elevated rounded-2xl p-6">
                  <h2 className="text-sm font-bold text-foreground mb-5" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                    Workspace
                  </h2>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-semibold text-muted-foreground mb-1.5 block uppercase tracking-wide">
                        Workspace name
                      </label>
                      <Input defaultValue="FlowDesk HQ" />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-muted-foreground mb-1.5 block uppercase tracking-wide">
                        Workspace URL
                      </label>
                      <div className="flex">
                        <span className="inline-flex items-center px-3 text-xs text-muted-foreground bg-muted border border-r-0 border-input rounded-l-md">
                          flowdesk.io/
                        </span>
                        <Input defaultValue="flowdesk-hq" className="rounded-l-none" />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-3">
                  <Button variant="outline" onClick={handleComingSoon}>Discard changes</Button>
                  <Button
                    className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2"
                    onClick={handleSave}
                  >
                    {saved ? <><Check className="w-4 h-4" /> Saved</> : "Save changes"}
                  </Button>
                </div>
              </>
            )}

            {/* ── Notifications ── */}
            {activeTab === "notifications" && (
              <div className="card-elevated rounded-2xl p-6">
                <h2 className="text-sm font-bold text-foreground mb-5" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                  Notification Preferences
                </h2>
                <div className="space-y-5">
                  {[
                    { label: "New team member joins", desc: "Get notified when someone accepts your invitation", defaultOn: true },
                    { label: "Revenue milestones", desc: "Alerts when your MRR hits a new high", defaultOn: true },
                    { label: "Anomaly detection", desc: "Unusual traffic or conversion rate changes", defaultOn: true },
                    { label: "Weekly digest", desc: "A summary of your workspace activity every Monday", defaultOn: false },
                    { label: "Product updates", desc: "New features and improvements from FlowDesk", defaultOn: false },
                    { label: "Marketing emails", desc: "Tips, case studies, and best practices", defaultOn: false },
                  ].map(({ label, desc, defaultOn }) => (
                    <div key={label} className="flex items-start justify-between gap-4 pb-5 border-b border-border last:border-0 last:pb-0">
                      <div>
                        <p className="text-sm font-medium text-foreground">{label}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
                      </div>
                      <Switch defaultChecked={defaultOn} />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Security ── */}
            {activeTab === "security" && (
              <>
                <div className="card-elevated rounded-2xl p-6">
                  <h2 className="text-sm font-bold text-foreground mb-5" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                    Password
                  </h2>
                  <div className="space-y-4 max-w-sm">
                    {["Current password", "New password", "Confirm new password"].map((label) => (
                      <div key={label}>
                        <label className="text-xs font-semibold text-muted-foreground mb-1.5 block uppercase tracking-wide">
                          {label}
                        </label>
                        <Input type="password" placeholder="••••••••" />
                      </div>
                    ))}
                    <Button className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2" onClick={handleComingSoon}>
                      <Key className="w-4 h-4" />
                      Update password
                    </Button>
                  </div>
                </div>

                <div className="card-elevated rounded-2xl p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h2 className="text-sm font-bold text-foreground mb-1" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                        Two-factor authentication
                      </h2>
                      <p className="text-xs text-muted-foreground">Add an extra layer of security to your account.</p>
                    </div>
                    <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100 border-0 text-xs">Not enabled</Badge>
                  </div>
                  <div className="mt-5 flex gap-3">
                    <Button variant="outline" className="gap-2" onClick={handleComingSoon}>
                      <Smartphone className="w-4 h-4" />
                      Set up authenticator app
                    </Button>
                  </div>
                </div>

                <div className="card-elevated rounded-2xl p-6">
                  <h2 className="text-sm font-bold text-foreground mb-4" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                    Active Sessions
                  </h2>
                  {[
                    { device: "MacBook Pro — Chrome", location: "San Francisco, CA", time: "Current session", current: true },
                    { device: "iPhone 15 — Safari", location: "San Francisco, CA", time: "2 hours ago", current: false },
                    { device: "Windows PC — Firefox", location: "New York, NY", time: "3 days ago", current: false },
                  ].map(({ device, location, time, current }) => (
                    <div key={device} className="flex items-center justify-between py-3 border-b border-border last:border-0">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 bg-slate-100 rounded-lg flex items-center justify-center">
                          <Globe className="w-4 h-4 text-slate-500" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-foreground">{device}</p>
                          <p className="text-xs text-muted-foreground">{location} · {time}</p>
                        </div>
                      </div>
                      {current ? (
                        <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 border-0 text-xs">Active</Badge>
                      ) : (
                        <Button variant="ghost" size="sm" className="text-xs text-destructive hover:text-destructive" onClick={handleComingSoon}>
                          Revoke
                        </Button>
                      )}
                    </div>
                  ))}
                </div>

                <div className="card-elevated rounded-2xl p-6 border-destructive/20">
                  <h2 className="text-sm font-bold text-destructive mb-2" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                    Danger Zone
                  </h2>
                  <p className="text-xs text-muted-foreground mb-4">
                    Once you delete your account, there is no going back. Please be certain.
                  </p>
                  <Button variant="outline" className="border-destructive/50 text-destructive hover:bg-destructive/5 gap-2" onClick={handleComingSoon}>
                    <Trash2 className="w-4 h-4" />
                    Delete account
                  </Button>
                </div>
              </>
            )}

            {/* ── Billing ── */}
            {activeTab === "billing" && (
              <>
                <div className="card-elevated rounded-2xl p-6">
                  <div className="flex items-start justify-between mb-5">
                    <div>
                      <h2 className="text-sm font-bold text-foreground" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                        Current Plan
                      </h2>
                      <p className="text-xs text-muted-foreground mt-0.5">You are on the Pro plan.</p>
                    </div>
                    <Badge className="bg-indigo-100 text-indigo-700 hover:bg-indigo-100 border-0">Pro</Badge>
                  </div>
                  <div className="bg-slate-50 rounded-xl p-4 mb-5">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-slate-600">Seats used</span>
                      <span className="text-sm font-semibold text-foreground">6 / 25</span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-2">
                      <div className="bg-indigo-600 h-2 rounded-full" style={{ width: "24%" }} />
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <Button className="bg-indigo-600 hover:bg-indigo-700 text-white" onClick={handleComingSoon}>
                      Upgrade to Enterprise
                    </Button>
                    <Button variant="outline" onClick={handleComingSoon}>Manage plan</Button>
                  </div>
                </div>

                <div className="card-elevated rounded-2xl p-6">
                  <h2 className="text-sm font-bold text-foreground mb-4" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                    Payment Method
                  </h2>
                  <div className="flex items-center gap-4 p-4 border border-border rounded-xl mb-4">
                    <div className="w-12 h-8 bg-slate-900 rounded-md flex items-center justify-center">
                      <span className="text-white text-xs font-bold">VISA</span>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">Visa ending in 4242</p>
                      <p className="text-xs text-muted-foreground">Expires 12/2027</p>
                    </div>
                    <Button variant="ghost" size="sm" className="ml-auto text-xs" onClick={handleComingSoon}>
                      Update
                    </Button>
                  </div>
                </div>

                <div className="card-elevated rounded-2xl overflow-hidden">
                  <div className="px-5 py-4 border-b border-border">
                    <h2 className="text-sm font-bold text-foreground" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                      Billing History
                    </h2>
                  </div>
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-border bg-muted/30">
                        <th className="text-left text-xs font-semibold text-muted-foreground px-5 py-3">Date</th>
                        <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Description</th>
                        <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Amount</th>
                        <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { date: "Apr 1, 2026", desc: "Pro Plan — Monthly", amount: "$49.00", status: "Paid" },
                        { date: "Mar 1, 2026", desc: "Pro Plan — Monthly", amount: "$49.00", status: "Paid" },
                        { date: "Feb 1, 2026", desc: "Pro Plan — Monthly", amount: "$49.00", status: "Paid" },
                      ].map(({ date, desc, amount, status }) => (
                        <tr key={date} className="border-b border-border last:border-0 hover:bg-muted/20 transition-colors">
                          <td className="px-5 py-3 text-sm text-muted-foreground">{date}</td>
                          <td className="px-4 py-3 text-sm text-foreground">{desc}</td>
                          <td className="px-4 py-3 text-sm font-medium text-foreground">{amount}</td>
                          <td className="px-4 py-3">
                            <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 border-0 text-xs">{status}</Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            {/* ── Integrations ── */}
            {activeTab === "integrations" && (
              <div className="card-elevated rounded-2xl p-6">
                <h2 className="text-sm font-bold text-foreground mb-5" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                  Connected Apps
                </h2>
                <div className="grid sm:grid-cols-2 gap-4">
                  {integrations.map(({ name, desc, icon, connected }) => (
                    <div key={name} className="border border-border rounded-xl p-4 flex items-start gap-4">
                      <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center text-xl flex-shrink-0">
                        {icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <p className="text-sm font-semibold text-foreground">{name}</p>
                          {connected && (
                            <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 border-0 text-xs">Connected</Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mb-3">{desc}</p>
                        <Button
                          variant={connected ? "outline" : "default"}
                          size="sm"
                          className={`text-xs ${!connected ? "bg-indigo-600 hover:bg-indigo-700 text-white" : ""}`}
                          onClick={handleComingSoon}
                        >
                          {connected ? "Disconnect" : "Connect"}
                          {!connected && <Zap className="w-3 h-3 ml-1.5" />}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
