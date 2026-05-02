/**
 * DashboardLayout — Arctic Clarity Design System
 * Dark slate-900 sidebar with indigo accents, white main content area
 * Responsive: sidebar collapses to icon-only on mobile
 */

import { useState } from "react";
import { Link, useLocation } from "wouter";
import {
  LayoutDashboard,
  BarChart3,
  Users,
  CreditCard,
  Settings,
  Bell,
  Search,
  ChevronDown,
  Menu,
  X,
  Zap,
  HelpCircle,
  LogOut,
  Moon,
  Sun,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { toast } from "sonner";
import { useTheme } from "@/contexts/ThemeContext";

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/dashboard" },
  { icon: BarChart3, label: "Analytics", href: "/analytics" },
  { icon: Users, label: "Team", href: "/team" },
  { icon: CreditCard, label: "Pricing", href: "/pricing" },
  { icon: Settings, label: "Settings", href: "/settings" },
];

interface DashboardLayoutProps {
  children: React.ReactNode;
  title?: string;
  breadcrumb?: { label: string; href?: string }[];
}

export default function DashboardLayout({ children, title, breadcrumb }: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [location] = useLocation();
  const { theme, toggleTheme } = useTheme();

  const handleComingSoon = () => toast.info("Feature coming soon!");

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-50 lg:z-auto
          w-64 flex flex-col
          bg-sidebar text-sidebar-foreground
          transition-transform duration-300 ease-in-out
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
        `}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 h-16 border-b border-sidebar-border flex-shrink-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center flex-shrink-0">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-lg text-white tracking-tight" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
            FlowDesk
          </span>
          <button
            className="ml-auto lg:hidden text-sidebar-foreground/60 hover:text-sidebar-foreground"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <p className="text-xs font-semibold text-sidebar-foreground/40 uppercase tracking-widest px-3 mb-3">
            Main Menu
          </p>
          {navItems.map(({ icon: Icon, label, href }) => {
            const isActive = location === href || (href === "/dashboard" && location === "/");
            return (
              <Link key={href} href={href}>
                <a className={`nav-item ${isActive ? "active" : ""}`}>
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span>{label}</span>
                  {label === "Analytics" && (
                    <Badge className="ml-auto text-[10px] py-0 px-1.5 bg-indigo-500/20 text-indigo-300 border-0 hover:bg-indigo-500/20">
                      New
                    </Badge>
                  )}
                </a>
              </Link>
            );
          })}

          <div className="pt-4 mt-4 border-t border-sidebar-border">
            <p className="text-xs font-semibold text-sidebar-foreground/40 uppercase tracking-widest px-3 mb-3">
              Support
            </p>
            <button className="nav-item w-full" onClick={handleComingSoon}>
              <HelpCircle className="w-4 h-4 flex-shrink-0" />
              <span>Help Center</span>
            </button>
          </div>
        </nav>

        {/* Upgrade CTA */}
        <div className="px-3 pb-3">
          <div className="rounded-xl bg-gradient-to-br from-indigo-600/30 to-violet-600/20 border border-indigo-500/20 p-4">
            <p className="text-sm font-semibold text-white mb-1">Upgrade to Pro</p>
            <p className="text-xs text-sidebar-foreground/60 mb-3">Unlock advanced analytics and unlimited seats.</p>
            <Link href="/pricing">
              <a className="block w-full text-center text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white py-2 px-3 rounded-lg transition-colors">
                View Plans
              </a>
            </Link>
          </div>
        </div>

        {/* User */}
        <div className="px-3 pb-4 border-t border-sidebar-border pt-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-3 w-full px-2 py-2 rounded-lg hover:bg-sidebar-accent transition-colors">
                <Avatar className="w-8 h-8 flex-shrink-0">
                  <AvatarImage src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=32&h=32&fit=crop&crop=face" />
                  <AvatarFallback className="bg-indigo-600 text-white text-xs">JD</AvatarFallback>
                </Avatar>
                <div className="flex-1 text-left min-w-0">
                  <p className="text-sm font-medium text-white truncate">John Doe</p>
                  <p className="text-xs text-sidebar-foreground/50 truncate">john@flowdesk.io</p>
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-sidebar-foreground/40 flex-shrink-0" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent side="top" align="start" className="w-52">
              <DropdownMenuItem onClick={handleComingSoon}>Profile Settings</DropdownMenuItem>
              <DropdownMenuItem onClick={handleComingSoon}>Billing</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleComingSoon} className="text-destructive">
                <LogOut className="w-4 h-4 mr-2" />
                Sign Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top header */}
        <header className="h-16 border-b border-border bg-card flex items-center px-4 lg:px-6 gap-4 flex-shrink-0">
          <button
            className="lg:hidden text-muted-foreground hover:text-foreground"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Breadcrumb */}
          <div className="flex items-center gap-1.5 text-sm">
            {breadcrumb ? (
              breadcrumb.map((crumb, i) => (
                <span key={i} className="flex items-center gap-1.5">
                  {i > 0 && <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />}
                  {crumb.href ? (
                    <Link href={crumb.href}>
                      <a className="text-muted-foreground hover:text-foreground transition-colors">{crumb.label}</a>
                    </Link>
                  ) : (
                    <span className="font-semibold text-foreground">{crumb.label}</span>
                  )}
                </span>
              ))
            ) : (
              <span className="font-semibold text-foreground">{title || "Dashboard"}</span>
            )}
          </div>

          <div className="ml-auto flex items-center gap-2">
            {/* Search */}
            <button
              className="hidden sm:flex items-center gap-2 text-sm text-muted-foreground bg-muted/60 hover:bg-muted rounded-lg px-3 py-2 transition-colors"
              onClick={handleComingSoon}
            >
              <Search className="w-4 h-4" />
              <span className="hidden md:inline">Search...</span>
              <kbd className="hidden md:inline text-xs bg-background border border-border rounded px-1.5 py-0.5 font-mono">⌘K</kbd>
            </button>

            {/* Theme toggle */}
            <Button variant="ghost" size="icon" onClick={toggleTheme} className="text-muted-foreground">
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </Button>

            {/* Notifications */}
            <Button variant="ghost" size="icon" className="relative text-muted-foreground" onClick={handleComingSoon}>
              <Bell className="w-4 h-4" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-indigo-500 rounded-full" />
            </Button>

            {/* Avatar */}
            <Avatar className="w-8 h-8">
              <AvatarImage src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=32&h=32&fit=crop&crop=face" />
              <AvatarFallback className="bg-indigo-600 text-white text-xs">JD</AvatarFallback>
            </Avatar>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div className="page-enter">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
