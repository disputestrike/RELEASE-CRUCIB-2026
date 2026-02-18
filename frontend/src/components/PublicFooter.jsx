import { Link, useNavigate } from 'react-router-dom';

export default function PublicFooter() {
  const navigate = useNavigate();
  return (
    <footer className="mt-24 py-12 px-6 border-t border-white/10 bg-kimi-bg">
      {/* Footer CTA — Kimi-style */}
      <div className="max-w-2xl mx-auto text-center mb-16">
        <h2 className="text-2xl md:text-3xl font-bold text-kimi-text mb-3">Make your idea inevitable</h2>
        <p className="text-kimi-muted mb-6">Describe your vision. Watch it become inevitable. No code required.</p>
        <div className="flex flex-wrap justify-center gap-4">
          <button onClick={() => navigate('/auth?mode=register')} className="px-6 py-3 bg-white text-black font-medium rounded-lg hover:bg-zinc-200 transition border border-black/10">
            Make It Inevitable
          </button>
          <Link to="/learn" className="px-6 py-3 bg-transparent text-kimi-text font-medium rounded-lg border border-white/30 hover:border-white/50 transition">
            View Documentation
          </Link>
        </div>
      </div>
      <div className="max-w-6xl mx-auto">
        <div className="grid md:grid-cols-4 gap-12 mb-12">
          <div>
            <div className="text-lg font-semibold text-kimi-text mb-4">CrucibAI — Inevitable AI</div>
            <p className="text-sm text-kimi-muted mb-3">Turn ideas into inevitable outcomes. No code required.</p>
            <ul className="space-y-2 text-sm">
              <li><Link to="/about" className="text-kimi-muted hover:text-kimi-text transition">About us</Link></li>
            </ul>
          </div>
          <div>
            <div className="text-xs text-kimi-muted uppercase tracking-wider mb-4">Product</div>
            <ul className="space-y-3 text-sm">
              <li><Link to="/features" className="text-kimi-muted hover:text-kimi-text transition">Features</Link></li>
              <li><Link to="/pricing" className="text-kimi-muted hover:text-kimi-text transition">Pricing</Link></li>
              <li><Link to="/templates" className="text-kimi-muted hover:text-kimi-text transition">Templates</Link></li>
              <li><Link to="/patterns" className="text-kimi-muted hover:text-kimi-text transition">Patterns</Link></li>
              <li><Link to="/enterprise" className="text-kimi-muted hover:text-kimi-text transition">Enterprise</Link></li>
            </ul>
          </div>
          <div>
            <div className="text-xs text-kimi-muted uppercase tracking-wider mb-4">Resources</div>
            <ul className="space-y-3 text-sm">
              <li><Link to="/learn" className="text-kimi-muted hover:text-kimi-text transition">Learn</Link></li>
              <li><Link to="/shortcuts" className="text-kimi-muted hover:text-kimi-text transition">Shortcuts</Link></li>
              <li><Link to="/benchmarks" className="text-kimi-muted hover:text-kimi-text transition">Benchmarks</Link></li>
              <li><Link to="/prompts" className="text-kimi-muted hover:text-kimi-text transition">Prompt Library</Link></li>
              <li><a href="/#who-builds-better" className="text-kimi-muted hover:text-kimi-text transition">Why CrucibAI</a></li>
            </ul>
          </div>
          <div>
            <div className="text-xs text-kimi-muted uppercase tracking-wider mb-4">Legal</div>
            <ul className="space-y-3 text-sm">
              <li><Link to="/privacy" className="text-kimi-muted hover:text-kimi-text transition">Privacy</Link></li>
              <li><Link to="/terms" className="text-kimi-muted hover:text-kimi-text transition">Terms</Link></li>
              <li><Link to="/aup" className="text-kimi-muted hover:text-kimi-text transition">Acceptable Use</Link></li>
              <li><Link to="/dmca" className="text-kimi-muted hover:text-kimi-text transition">DMCA</Link></li>
              <li><Link to="/cookies" className="text-kimi-muted hover:text-kimi-text transition">Cookies</Link></li>
            </ul>
          </div>
        </div>
        <div className="pt-8 border-t border-white/10 text-center">
          <p className="text-xs text-kimi-muted">© 2026 CrucibAI. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
