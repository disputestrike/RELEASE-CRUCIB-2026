import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Code2 } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import Logo from '../components/Logo';

/**
 * OnboardingPage — CF24
 * Two-way fork for brand new users: Developer vs Builder (non-developer).
 * This choice determines which tabs appear in the 3-pane workspace.
 */
export default function OnboardingPage() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth() || {};
  const [loading, setLoading] = useState(null);
  const [error, setError] = useState('');

  const pickRole = async (mode) => {
    setError('');
    setLoading(mode);
    const token = localStorage.getItem('token');
    localStorage.setItem('crucibai_workspace_mode', mode);
    try {
      if (token) {
        await axios.post(`${API}/user/workspace-mode`, { mode }, {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 5000,
        });
      }
      if (refreshUser) await refreshUser();
    } catch {
      /* localStorage fallback already set above */
    }
    setLoading(null);
    navigate('/app/workspace');
  };

  const cards = [
    {
      mode: 'developer',
      icon: Code2,
      title: 'Developer',
      subtitle: 'See code, diffs, logs, and full runtime internals. Best if you want to ship production software.',
      bullets: ['Raw logs + diffs', 'Code editor tabs', 'Full capability audit'],
    },
    {
      mode: 'simple',
      icon: User,
      title: 'Builder (non-developer)',
      subtitle: 'Describe what you want, approve the plan, and we build it. No code required.',
      bullets: ['Visual preview only', 'Plain-English plans', 'Safe defaults'],
    },
  ];

  return (
    <div className="min-h-screen w-full bg-white flex flex-col items-center justify-center p-8">
      <Logo variant="full" height={40} href="/app/workspace" className="logo-surface-light mb-8" showTagline={false} />
      <h1 className="text-2xl font-semibold text-[#1A1A1A] mb-2">Who are you building with CrucibAI?</h1>
      <p className="text-sm text-gray-600 mb-8">Pick a starting view. You can switch later in Settings.</p>
      <div className="flex flex-wrap justify-center gap-6 max-w-4xl">
        {cards.map((card) => {
          const { mode, icon: Icon, title, subtitle, bullets } = card;
          return (
            <button
              key={mode}
              type="button"
              onClick={() => pickRole(mode)}
              disabled={loading != null}
              data-testid={`onboarding-${mode}`}
              className="w-full max-w-sm p-8 rounded-2xl border border-gray-200 bg-white hover:border-neutral-500 hover:shadow-sm transition-all text-left flex flex-col items-start gap-5 disabled:opacity-70"
            >
              <Icon className="w-12 h-12 text-[#1A1A1A]" />
              <div>
                <h2 className="text-xl font-semibold text-[#1A1A1A]">{title}</h2>
                <p className="text-sm text-gray-600 mt-2 leading-relaxed">{subtitle}</p>
              </div>
              <ul className="text-xs text-gray-500 space-y-1">
                {bullets.map((b) => (<li key={b}>• {b}</li>))}
              </ul>
              {loading === mode ? (
                <div className="w-5 h-5 border-2 border-gray-300 border-t-[#1A1A1A] rounded-full animate-spin" />
              ) : null}
            </button>
          );
        })}
      </div>
      {error && <p className="mt-6 text-sm text-red-600">{error}</p>}
    </div>
  );
}
