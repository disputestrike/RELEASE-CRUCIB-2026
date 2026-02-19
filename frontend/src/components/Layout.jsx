import { useState, useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth, API } from '../App';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Sparkles, LayoutDashboard, FolderPlus, Coins, FileOutput, 
  Library, Settings, LogOut, Menu, X, ChevronRight,
  Zap, Bell, MessageSquare, LayoutGrid, BookOpen, Key, Keyboard, CreditCard, FileText, Shield, ScrollText, BarChart3, Code2
} from 'lucide-react';

const Layout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [backendOk, setBackendOk] = useState(null);

  const checkBackend = () => {
    setBackendOk(null);
    axios.get(`${API}/health`, { timeout: 5000 })
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false));
  };

  useEffect(() => {
    checkBackend();
  }, []);

  const navigation = [
    { name: 'Dashboard', href: '/app', icon: LayoutDashboard },
    { name: 'Workspace', href: '/app/workspace', icon: Code2 },
    { name: 'New Project', href: '/app/projects/new', icon: FolderPlus },
    { name: 'Agents', href: '/app/agents', icon: Zap },
    { name: 'Credit Center', href: '/app/tokens', icon: Coins },
    { name: 'Exports', href: '/app/exports', icon: FileOutput },
    { name: 'Docs / Slides / Sheets', href: '/app/generate', icon: FileText },
    { name: 'Patterns', href: '/app/patterns', icon: Library },
    { name: 'Templates', href: '/app/templates', icon: LayoutGrid },
    { name: 'Prompt Library', href: '/app/prompts', icon: BookOpen },
    { name: 'Learn', href: '/app/learn', icon: BookOpen },
    { name: 'Env', href: '/app/env', icon: Key },
    { name: 'Shortcuts', href: '/app/shortcuts', icon: Keyboard },
    { name: 'Benchmarks', href: '/benchmarks', icon: BarChart3 },
    { name: 'Add payments', href: '/app/payments-wizard', icon: CreditCard },
    { name: 'Settings', href: '/app/settings', icon: Settings },
    { name: 'Audit Log', href: '/app/audit-log', icon: ScrollText }
  ];
  const adminNav = user?.admin_role
    ? [{ name: 'Admin', href: '/app/admin', icon: Shield }]
    : [];
  const navigationWithAdmin = [...navigation, ...adminNav];

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const NavItem = ({ item, mobile = false }) => {
    const isActive = location.pathname === item.href;
    return (
      <Link
        to={item.href}
        onClick={() => mobile && setMobileMenuOpen(false)}
        className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
          isActive 
            ? 'bg-blue-500/20 text-blue-400 border-l-2 border-blue-500' 
            : 'text-[#666666] hover:text-[#1A1A1A] hover:bg-white/5'
        }`}
        data-testid={`nav-${item.name.toLowerCase().replace(' ', '-')}`}
      >
        <item.icon className="w-5 h-5" />
        <span className={`${!sidebarOpen && !mobile ? 'hidden' : ''}`}>{item.name}</span>
      </Link>
    );
  };

  return (
    <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A] dark">
      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 h-16 glass z-50 flex items-center justify-between px-4">
        <Link to="/app" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <Sparkles className="w-5 h-5" />
          </div>
          <span className="font-bold">CrucibAI</span>
        </Link>
        <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} data-testid="mobile-menu-btn">
          {mobileMenuOpen ? <X /> : <Menu />}
        </button>
      </header>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, x: '100%' }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: '100%' }}
            className="lg:hidden fixed inset-0 z-40 bg-[#FAFAF8] pt-16"
          >
            <div className="p-4 space-y-2">
              {navigationWithAdmin.map(item => <NavItem key={item.name} item={item} mobile />)}
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-3 px-4 py-3 text-red-400 hover:bg-red-500/10 rounded-lg transition"
                data-testid="mobile-logout-btn"
              >
                <LogOut className="w-5 h-5" />
                <span>Logout</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Desktop Sidebar */}
      <aside className={`hidden lg:flex flex-col fixed left-0 top-0 bottom-0 z-40 glass transition-all duration-300 ${
        sidebarOpen ? 'w-64' : 'w-20'
      }`}>
        <div className="h-16 flex items-center justify-between px-4 border-b border-white/10">
          <Link to="/app" className="flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <Sparkles className="w-6 h-6" />
            </div>
            {sidebarOpen && (
              <span className="flex flex-col">
                <span className="text-xl font-bold">CrucibAI</span>
                <span className="text-xs text-zinc-400">Inevitable AI</span>
              </span>
            )}
          </Link>
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1 hover:bg-white/10 rounded"
            data-testid="toggle-sidebar-btn"
          >
            <ChevronRight className={`w-5 h-5 transition-transform ${sidebarOpen ? 'rotate-180' : ''}`} />
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          {navigationWithAdmin.map(item => <NavItem key={item.name} item={item} />)}
        </nav>

        {/* Credits & plan (Base44-style) */}
        <div className={`p-4 border-t border-white/10 ${!sidebarOpen ? 'hidden' : ''}`}>
          <div className="p-4 bg-blue-500/10 rounded-lg border border-blue-500/30">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-[#666666]">Token balance</span>
              <Zap className="w-4 h-4 text-blue-400" />
            </div>
            <p className="text-2xl font-bold text-blue-400" data-testid="sidebar-token-balance">
              {(user?.token_balance ?? 0).toLocaleString()}
            </p>
            <div className="mt-2 space-y-1">
              <Link to="/app/tokens" className="text-xs text-blue-400 hover:text-blue-300 block">
                Buy more tokens →
              </Link>
              <Link to="/pricing" className="text-xs text-blue-400 hover:text-blue-300 block">
                Pricing plans
              </Link>
              <Link to="/app/learn" className="text-xs text-[#666666] hover:text-[#1A1A1A] block">
                Documentation
              </Link>
              <a href="mailto:support@crucibai.com" className="text-xs text-[#666666] hover:text-[#1A1A1A] block">
                Get help
              </a>
            </div>
          </div>
        </div>

        {/* User Section */}
        <div className="p-4 border-t border-white/10">
          <div className={`flex items-center gap-3 ${!sidebarOpen ? 'justify-center' : ''}`}>
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center font-bold">
              {user?.name?.[0]?.toUpperCase() || 'U'}
            </div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate" data-testid="sidebar-user-name">{user?.name}</p>
                <p className="text-xs text-gray-500 truncate">{user?.email}</p>
                <Link to="/pricing" className="text-xs text-blue-400 hover:text-blue-300 truncate block mt-0.5" title="View plans">
                  Plan: {user?.plan ? String(user.plan).charAt(0).toUpperCase() + String(user.plan).slice(1) : 'Free'}
                </Link>
              </div>
            )}
            <button 
              onClick={handleLogout}
              className="p-2 hover:bg-red-500/10 text-[#666666] hover:text-red-400 rounded-lg transition"
              title="Logout"
              data-testid="desktop-logout-btn"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className={`min-h-screen pt-16 lg:pt-0 transition-all duration-300 bg-[#FAF9F7] ${
        sidebarOpen ? 'lg:pl-64' : 'lg:pl-20'
      }`}>
        {user?.internal_team && (
          <div className="bg-amber-100 border-b border-amber-300 px-4 py-2 text-center text-sm text-amber-900 font-medium" data-testid="internal-watermark">
            {user?.internal_label || '[INTERNAL]'} — Internal use only
          </div>
        )}
        <div className="p-6">
          <Outlet />
        </div>
        {/* Footer: backend status + Privacy | Terms */}
        <footer className="px-6 py-3 border-t border-gray-200 flex items-center justify-between text-xs text-gray-500">
          <span className="flex items-center gap-2">
            {backendOk === true && <span className="text-green-600">Backend connected</span>}
            {backendOk === false && (
              <>
                <span className="text-amber-600">Backend unavailable</span>
                <button type="button" onClick={checkBackend} className="text-blue-600 hover:text-blue-800 font-medium">Retry</button>
              </>
            )}
            {backendOk === null && <span>Checking…</span>}
          </span>
          <span className="flex gap-4">
            <Link to="/about" className="hover:text-gray-800">About</Link>
            <Link to="/privacy" className="hover:text-gray-800">Privacy</Link>
            <Link to="/terms" className="hover:text-gray-800">Terms</Link>
            <Link to="/aup" className="hover:text-gray-800">Acceptable Use</Link>
            <Link to="/dmca" className="hover:text-gray-800">DMCA</Link>
            <Link to="/cookies" className="hover:text-gray-800">Cookies</Link>
          </span>
        </footer>
      </main>
    </div>
  );
};

export default Layout;