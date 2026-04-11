import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import Logo from './Logo';
import SolutionsNavDropdown from './SolutionsNavDropdown';

export default function PublicNav() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const navBg = 'bg-[var(--kimi-bg)] border-b border-white/10';
  const linkClass = 'text-kimi-nav text-kimi-muted hover:text-kimi-text transition flex items-center gap-2';
  const ctaClass = 'px-4 py-2 bg-white text-zinc-900 text-sm font-medium rounded-lg hover:bg-zinc-200 transition';

  return (
    <nav className={navBg}>
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <Logo variant="full" height={32} href="/" className="shrink-0" />
        <div className="flex items-center gap-6">
          <div className="hidden sm:flex items-center">
            <SolutionsNavDropdown />
          </div>
          <Link to="/pricing" className={`${linkClass} hidden sm:flex`}>Pricing</Link>
          <Link to="/our-projects" className={`${linkClass} hidden sm:flex`}>Our Project</Link>
          {user ? (
            <>
              <Link to="/app" className="px-4 py-2 bg-black text-white text-sm font-medium rounded-full hover:bg-black/90 transition">Dashboard</Link>
              <button onClick={() => navigate('/app/workspace')} className={ctaClass}>Get Started</button>
            </>
          ) : (
            <>
              <Link to="/auth" className={`${linkClass} hidden sm:flex`}>Log in</Link>
              <Link to="/auth?mode=register" className="px-4 py-2 bg-black text-white text-sm font-medium rounded-full hover:bg-black/90 transition">Sign up</Link>
              <button onClick={() => navigate('/app/workspace')} className={ctaClass}>Get Started</button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
