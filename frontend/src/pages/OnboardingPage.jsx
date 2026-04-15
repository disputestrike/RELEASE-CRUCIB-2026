import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Code } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import Logo from '../components/Logo';

/**
 * OnboardingPage — Mode selection for new users.
 * Fullscreen, no sidebar/header/footer. Three outcomes: build, improve code, or automate.
 */
export default function OnboardingPage() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [loading, setLoading] = useState(null);
  const [error, setError] = useState('');

  const selectMode = async (card) => {
    const mode = card.mode;
    setError('');
    setLoading(mode);
    const token = localStorage.getItem('token');
    if (!token) {
      setError('Session expired. Please sign in again.');
      setLoading(null);
      return;
    }
    try {
      await axios.post(`${API}/user/workspace-mode`, { mode }, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 5000,
      });
      localStorage.removeItem('crucibai_workspace_mode'); // clear fallback
      if (refreshUser) await refreshUser();
      navigate('/app', { state: card.state || {} });
    } catch (err) {
      // Fallback: save locally and still go to dashboard so user isn't stuck
      localStorage.setItem('crucibai_workspace_mode', mode);
      if (refreshUser) await refreshUser();
      navigate('/app', { state: card.state || {} });
    } finally {
      setLoading(null);
    }
  };

  const cards = [
    {
      mode: 'simple',
      icon: User,
      title: 'Build new app',
      subtitle: 'Describe the outcome, approve the plan, preview it, and publish.',
      state: { newProject: true },
    },
    {
      mode: 'developer',
      icon: Code,
      title: 'Improve existing code',
      subtitle: 'Import files, inspect the diff, run proof, and keep full code ownership.',
      state: { openImport: true },
    },
    {
      mode: 'simple',
      icon: User,
      title: 'Automate workflow',
      subtitle: 'Turn recurring work into an agent flow that can call the build AI.',
      state: { suggestedPrompt: 'Create an automation that runs every weekday and uses the build agent to improve a project from new feedback.' },
    },
  ];

  return (
    <div className="min-h-screen w-full bg-white flex flex-col items-center justify-center p-8">
      <Logo variant="full" height={40} href="/app" className="logo-surface-light mb-8" showTagline={false} />
      <h1 className="text-2xl font-semibold text-[#1A1A1A] mb-8">
        How do you want to use CrucibAI?
      </h1>
      <div className="flex flex-wrap justify-center gap-6 max-w-2xl">
        {cards.map((card) => {
          const { mode, icon: Icon, title, subtitle } = card;
          return (
          <button
            key={title}
            type="button"
            onClick={() => selectMode(card)}
            disabled={loading != null}
            className="w-full max-w-xs p-6 rounded-xl border border-gray-200 bg-white hover:border-neutral-400 transition-all text-left flex flex-col items-start gap-4 disabled:opacity-70"
          >
            <Icon className="w-10 h-10 text-[#1A1A1A]" />
            <div>
              <h2 className="text-lg font-semibold text-[#1A1A1A]">{title}</h2>
              <p className="text-sm text-gray-600 mt-1">{subtitle}</p>
            </div>
            {loading === mode ? (
              <div className="w-5 h-5 border-2 border-gray-300 border-t-[#1A1A1A] rounded-full animate-spin" />
            ) : null}
          </button>
          );
        })}
      </div>
      {error && (
        <p className="mt-6 text-sm text-red-600">{error}</p>
      )}
    </div>
  );
}
