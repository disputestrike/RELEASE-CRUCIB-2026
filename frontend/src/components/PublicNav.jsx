import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { Sparkles, CreditCard, Layout, FileText, BookOpen } from 'lucide-react';

export default function PublicNav() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const navBg = 'bg-[var(--kimi-bg)] border-b border-white/10';
  const linkClass = 'text-kimi-nav text-kimi-muted hover:text-kimi-text transition flex items-center gap-2';
  const ctaClass = 'px-4 py-2 bg-white text-zinc-900 text-sm font-medium rounded-lg hover:bg-zinc-200 transition';

  return (
    <nav className={navBg}>
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link to="/" className="text-xl font-semibold tracking-tight text-kimi-text">CrucibAI <span className="text-kimi-muted font-normal text-base">— Inevitable AI</span></Link>
        <div className="flex items-center gap-6">
          <Link to="/features" className={`${linkClass} hidden sm:flex`}><Sparkles className="w-4 h-4" /> Features</Link>
          <Link to="/pricing" className={`${linkClass} hidden sm:flex`}><CreditCard className="w-4 h-4" /> Pricing</Link>
          <Link to="/templates" className={`${linkClass} hidden sm:flex`}><Layout className="w-4 h-4" /> Templates</Link>
          <Link to="/prompts" className={`${linkClass} hidden sm:flex`}><FileText className="w-4 h-4" /> Prompts</Link>
          <Link to="/learn" className={`${linkClass} hidden sm:flex`}><BookOpen className="w-4 h-4" /> Documentation</Link>
          <Link to="/blog" className={`${linkClass} hidden sm:flex`}>Blog</Link>
          {user ? (
            <Link to="/app" className={ctaClass}>Dashboard</Link>
          ) : (
            <>
              <Link to="/auth" className={linkClass}>Sign in</Link>
              <button onClick={() => navigate('/auth?mode=register')} className={ctaClass}>
                Get started free
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
