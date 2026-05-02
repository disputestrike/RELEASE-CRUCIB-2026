/**
 * Team Page — Arctic Clarity Design System
 * Member grid, roles, invite modal, activity
 */

import { useState } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  UserPlus,
  MoreHorizontal,
  Shield,
  Edit3,
  Eye,
  Crown,
  Search,
  Mail,
} from "lucide-react";
import { toast } from "sonner";

const members = [
  {
    name: "John Doe",
    email: "john@flowdesk.io",
    role: "Owner",
    status: "active",
    lastActive: "Now",
    avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=48&h=48&fit=crop&crop=face",
    joined: "Jan 2024",
    tasks: 142,
  },
  {
    name: "Sarah Johnson",
    email: "sarah@flowdesk.io",
    role: "Admin",
    status: "active",
    lastActive: "2h ago",
    avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=48&h=48&fit=crop&crop=face",
    joined: "Feb 2024",
    tasks: 98,
  },
  {
    name: "Marcus Chen",
    email: "marcus@flowdesk.io",
    role: "Editor",
    status: "active",
    lastActive: "5h ago",
    avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=48&h=48&fit=crop&crop=face",
    joined: "Mar 2024",
    tasks: 76,
  },
  {
    name: "Priya Patel",
    email: "priya@flowdesk.io",
    role: "Editor",
    status: "active",
    lastActive: "1d ago",
    avatar: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=48&h=48&fit=crop&crop=face",
    joined: "Mar 2024",
    tasks: 54,
  },
  {
    name: "David Kim",
    email: "david@flowdesk.io",
    role: "Viewer",
    status: "inactive",
    lastActive: "3d ago",
    avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=48&h=48&fit=crop&crop=face",
    joined: "Apr 2024",
    tasks: 12,
  },
  {
    name: "Emma Wilson",
    email: "emma@flowdesk.io",
    role: "Viewer",
    status: "active",
    lastActive: "6h ago",
    avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=48&h=48&fit=crop&crop=face",
    joined: "Apr 2024",
    tasks: 31,
  },
];

const roleConfig: Record<string, { icon: React.ReactNode; color: string; bg: string }> = {
  Owner: { icon: <Crown className="w-3 h-3" />, color: "text-amber-700", bg: "bg-amber-100" },
  Admin: { icon: <Shield className="w-3 h-3" />, color: "text-violet-700", bg: "bg-violet-100" },
  Editor: { icon: <Edit3 className="w-3 h-3" />, color: "text-indigo-700", bg: "bg-indigo-100" },
  Viewer: { icon: <Eye className="w-3 h-3" />, color: "text-slate-600", bg: "bg-slate-100" },
};

export default function Team() {
  const [search, setSearch] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("Editor");
  const [dialogOpen, setDialogOpen] = useState(false);
  const handleComingSoon = () => toast.info("Feature coming soon!");

  const filtered = members.filter(
    (m) =>
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      m.email.toLowerCase().includes(search.toLowerCase())
  );

  const handleInvite = () => {
    if (!inviteEmail) return;
    toast.success(`Invitation sent to ${inviteEmail}`);
    setInviteEmail("");
    setDialogOpen(false);
  };

  return (
    <DashboardLayout
      breadcrumb={[
        { label: "FlowDesk", href: "/dashboard" },
        { label: "Team" },
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
              Team Members
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Manage your team and their access levels.
            </p>
          </div>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2">
                <UserPlus className="w-4 h-4" />
                Invite member
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                  Invite a team member
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-2">
                <div>
                  <label className="text-sm font-medium text-foreground mb-1.5 block">Email address</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      type="email"
                      placeholder="colleague@company.com"
                      className="pl-9"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                    />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground mb-1.5 block">Role</label>
                  <Select value={inviteRole} onValueChange={setInviteRole}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Admin">Admin — Full access</SelectItem>
                      <SelectItem value="Editor">Editor — Can edit dashboards</SelectItem>
                      <SelectItem value="Viewer">Viewer — Read-only access</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="bg-slate-50 rounded-xl p-4 text-xs text-slate-500">
                  The invitee will receive an email with a link to join your workspace.
                </div>
                <div className="flex gap-3 pt-1">
                  <Button variant="outline" className="flex-1" onClick={() => setDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white" onClick={handleInvite}>
                    Send invite
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: "Total members", value: members.length.toString(), color: "text-indigo-600" },
            { label: "Active now", value: members.filter((m) => m.status === "active").length.toString(), color: "text-emerald-600" },
            { label: "Admins", value: members.filter((m) => m.role === "Admin" || m.role === "Owner").length.toString(), color: "text-violet-600" },
            { label: "Seats used", value: `${members.length}/25`, color: "text-amber-600" },
          ].map(({ label, value, color }) => (
            <div key={label} className="card-elevated rounded-xl p-4">
              <p className={`text-2xl font-extrabold ${color} mb-0.5`} style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                {value}
              </p>
              <p className="text-xs text-muted-foreground">{label}</p>
            </div>
          ))}
        </div>

        {/* Search + filter */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search members..."
              className="pl-9"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Button variant="outline" size="sm" onClick={handleComingSoon}>
            Filter by role
          </Button>
        </div>

        {/* Member cards grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(({ name, email, role, status, lastActive, avatar, joined, tasks }) => {
            const rc = roleConfig[role];
            return (
              <div key={email} className="card-elevated rounded-2xl p-5">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <Avatar className="w-11 h-11">
                        <AvatarImage src={avatar} />
                        <AvatarFallback className="bg-indigo-100 text-indigo-700 font-semibold text-sm">
                          {name.split(" ").map((n) => n[0]).join("")}
                        </AvatarFallback>
                      </Avatar>
                      <div
                        className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white ${
                          status === "active" ? "bg-emerald-500" : "bg-slate-400"
                        }`}
                      />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-foreground truncate">{name}</p>
                      <p className="text-xs text-muted-foreground truncate">{email}</p>
                    </div>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="w-7 h-7 text-muted-foreground flex-shrink-0">
                        <MoreHorizontal className="w-4 h-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={handleComingSoon}>View profile</DropdownMenuItem>
                      <DropdownMenuItem onClick={handleComingSoon}>Change role</DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={handleComingSoon} className="text-destructive">
                        Remove from team
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <div className="flex items-center justify-between mb-4">
                  <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full ${rc.bg} ${rc.color}`}>
                    {rc.icon}
                    {role}
                  </span>
                  <span className="text-xs text-muted-foreground">{lastActive}</span>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-4 border-t border-border">
                  <div>
                    <p className="text-xs text-muted-foreground">Joined</p>
                    <p className="text-sm font-medium text-foreground">{joined}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Tasks done</p>
                    <p className="text-sm font-medium text-foreground">{tasks}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Pending invites */}
        <div className="card-elevated rounded-2xl overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h2 className="text-sm font-bold text-foreground" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
              Pending Invitations
            </h2>
          </div>
          <div className="p-5">
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <div className="w-12 h-12 bg-slate-100 rounded-2xl flex items-center justify-center mb-3">
                <Mail className="w-5 h-5 text-slate-400" />
              </div>
              <p className="text-sm font-medium text-foreground mb-1">No pending invitations</p>
              <p className="text-xs text-muted-foreground">Invite a team member to get started.</p>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
