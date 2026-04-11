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
  const quietClass = 'text-sm text-kimi-nav text-kimi-muted hover:text-kimi-text transition';
  const ctaPrimary = 'px-4 py-2 bg-white text-zinc-900 text-sm font-medium rounded-lg hover:bg-zinc-200 transition';

  return (
    <nav className={navBg}>
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-6">
        <Logo variant="full" height={32} href="/" className="shrink-0" />
        <div className="hidden sm:flex flex-1 items-center justify-center gap-8 min-w-0">
          <SolutionsNavDropdown />
          <Link to="/pricing" className={linkClass}>Pricing</Link>
          <Link to="/our-projects" className={linkClass}>Our Project</Link>
        </div>
        <div className="flex items-center gap-3 sm:gap-4 ml-auto shrink-0">
          <Link to="/app" className={`${quietClass} hidden sm:inline`}>Dashboard</Link>
          {!user && (
            <Link to="/auth" className={`${quietClass} hidden sm:inline`}>Log in</Link>
          )}
          <button type="button" onClick={() => navigate('/app/workspace')} className={ctaPrimary}>
            Get started
          </button>
        </div>
      </div>
    </nav>
  );
}
