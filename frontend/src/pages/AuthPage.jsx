import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, Lock, User, ArrowRight, Eye, EyeOff, Check, X } from 'lucide-react';
import { useAuth, API } from '../App';

const AuthPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login, register, user, loginWithToken, verifyMfa } = useAuth();
  
  const [isLogin, setIsLogin] = useState(searchParams.get('mode') !== 'register');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({ name: '', email: '', password: '' });
  const [mfaPending, setMfaPending] = useState(null);
  const [mfaCode, setMfaCode] = useState('');

  useEffect(() => {
    if (user) {
      const redirect = searchParams.get('redirect');
      navigate(redirect && redirect.startsWith('/') ? redirect : '/app');
      return;
    }
    const tokenFromUrl = searchParams.get('token');
    const errorFromUrl = searchParams.get('error');
    if (errorFromUrl) {
      setError(errorFromUrl === 'no_code' ? 'Google sign-in was cancelled.' : errorFromUrl === 'google_failed' ? 'Google sign-in failed. Try again.' : 'Sign-in failed.');
    } else if (tokenFromUrl && loginWithToken) {
      loginWithToken(tokenFromUrl);
    }
  }, [user, searchParams, navigate, loginWithToken]);

  const handleGoogleSignIn = () => {
    const backendUrl = API.replace('/api', '');
    const redirect = searchParams.get('redirect');
    const url = redirect
      ? `${backendUrl}/api/auth/google?redirect=${encodeURIComponent(redirect)}`
      : `${backendUrl}/api/auth/google`;
    window.location.href = url;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      if (isLogin) {
        const data = await login(formData.email, formData.password);
        if (data.status === 'mfa_required' && data.mfa_token) {
          setMfaPending(data.mfa_token);
          setLoading(false);
          return;
        }
      } else {
        await register(formData.email, formData.password, formData.name);
      }
      const redirect = searchParams.get('redirect');
      navigate(redirect && redirect.startsWith('/') ? redirect : '/app');
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  const handleMfaSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await verifyMfa(mfaCode.replace(/\D/g, '').slice(0, 6), mfaPending);
      setMfaPending(null);
      setMfaCode('');
      const redirect = searchParams.get('redirect');
      navigate(redirect && redirect.startsWith('/') ? redirect : '/app');
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid code');
    } finally {
      setLoading(false);
    }
  };

  const benefits = [
    'Plan-first build with 120-agent swarm',
    'The same AI that builds your app runs inside your automations',
    'Web, mobile, agents — one platform (websites, apps, automations)',
    'Describe your automation in plain language — we create it (prompt-to-automation)',
    '99.2% success — measured, not promised',
    '50 free credits to start',
    'No credit card required'
  ];

  const useCases = [
    { label: 'Web apps', desc: 'React, Tailwind, full-stack' },
    { label: 'Mobile apps', desc: 'iOS & Android, Expo, store pack' },
    { label: 'Agents & automation', desc: 'Schedule or webhook, your own agents' },
    { label: 'Dashboards', desc: 'Data, charts, admin' },
    { label: 'E‑commerce', desc: 'Stores, checkout, catalog' },
    { label: 'Landing pages', desc: 'Marketing, waitlist' },
    { label: 'Internal tools', desc: 'CRUD, workflows' },
    { label: 'API & automation', desc: 'Integrations, bots' },
    { label: 'For everyone', desc: 'Web, mobile, no code' },
  ];

  return (
    <div className="min-h-screen bg-gray-100/80 text-gray-900 flex">
      {/* Close X - top right, always visible */}
      <Link
        to="/"
        className="fixed top-4 right-4 z-50 p-2 rounded-lg bg-white/90 hover:bg-white border border-gray-200 text-gray-600 hover:text-gray-900 shadow-sm transition"
        aria-label="Close and return to home"
      >
        <X className="w-5 h-5" />
      </Link>

      <div className="w-full max-w-6xl mx-auto flex min-h-screen bg-white shadow-xl">
      {/* Left Panel - Benefits */}
      <div className="hidden lg:flex lg:w-1/2 bg-gray-50 relative">
        <div className="flex flex-col justify-center w-full p-12 max-w-xl">
          <Link to="/" className="flex items-center gap-2 mb-10">
            <span className="text-3xl font-bold tracking-tight">Crucib<span className="text-[#6366F1]">AI</span></span>
            <span className="text-sm font-medium text-gray-500 ml-1">— Inevitable AI</span>
          </Link>
          
          <h2 className="text-3xl font-bold mb-3 tracking-tight">Make your outcome inevitable</h2>
          <p className="text-gray-600 mb-4">
            Describe your vision. Agentic automation, plan-first flow, full transparency, and production-ready code—no black boxes.
          </p>
          
          <div className="space-y-4">
            {benefits.map((benefit, i) => (
              <motion.div
                key={benefit}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="flex items-center gap-3"
              >
                <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center">
                  <Check className="w-4 h-4 text-green-600" />
                </div>
                <span className="text-gray-700">{benefit}</span>
              </motion.div>
            ))}
          </div>
          
          <div className="mt-10 grid grid-cols-2 gap-4">
            {[
              { label: 'Agent swarm', value: '120' },
              { label: 'Success rate', value: '99.2%' },
              { label: 'Typical delivery', value: '<72 hrs' },
              { label: 'Transparency', value: 'Full' }
            ].map(stat => (
              <div key={stat.label} className="p-4 bg-white rounded-xl border border-gray-200">
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                <p className="text-sm text-gray-500">{stat.label}</p>
              </div>
            ))}
          </div>

          {/* Use cases — 8 examples, 4×2 */}
          <div className="mt-10">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">What you can build</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {useCases.map((uc) => (
                <div key={uc.label} className="p-3 bg-white rounded-lg border border-gray-100">
                  <p className="text-sm font-medium text-gray-900">{uc.label}</p>
                  <p className="text-xs text-gray-500">{uc.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      
      {/* Right Panel - Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          <div className="lg:hidden flex items-center justify-center mb-6">
            <Link to="/" className="flex items-center gap-2">
              <span className="text-2xl font-bold tracking-tight">Crucib<span className="text-[#6366F1]">AI</span></span>
              <span className="text-xs font-medium text-gray-500 ml-1">Inevitable AI</span>
            </Link>
          </div>
          
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-2 tracking-tight">
              {mfaPending ? 'Two-factor authentication' : isLogin ? 'Welcome back' : 'Create your account'}
            </h1>
            <p className="text-gray-600">
              {mfaPending ? 'Enter the 6-digit code from your authenticator app' : isLogin ? 'Sign in to continue building' : 'Start with 50 free credits — no credit card required'}
            </p>
          </div>
          
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm" data-testid="auth-error">
              {error}
            </div>
          )}

          {!mfaPending && (
          <button
            type="button"
            onClick={handleGoogleSignIn}
            className="w-full py-3.5 bg-white hover:bg-gray-50 border border-gray-300 rounded-xl font-medium transition flex items-center justify-center gap-2 text-gray-800 mb-5"
            data-testid="auth-google-btn"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Sign in with Google
          </button>
          )}
          {!mfaPending && (
          <div className="relative mb-5">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-gray-200"/></div>
            <div className="relative flex justify-center text-sm"><span className="px-2 bg-white text-gray-500">or</span></div>
          </div>
          )}
          
          {mfaPending ? (
            <form onSubmit={handleMfaSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-700">Verification code</label>
                <input
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition text-center text-2xl tracking-[0.5em] font-mono"
                  placeholder="000000"
                  maxLength={6}
                  autoFocus
                />
              </div>
              <button
                type="submit"
                disabled={loading || mfaCode.length !== 6}
                className="w-full py-3.5 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl font-medium transition"
              >
                {loading ? <span className="inline-block w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : 'Verify'}
              </button>
              <button
                type="button"
                onClick={() => { setMfaPending(null); setMfaCode(''); setError(''); }}
                className="w-full py-2 text-gray-500 hover:text-gray-700 text-sm"
              >
                Back to sign in
              </button>
            </form>
          ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            {!isLogin && (
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-700">Name</label>
                <div className="relative">
                  <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full pl-12 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition"
                    placeholder="Your name"
                    required={!isLogin}
                    data-testid="auth-name-input"
                  />
                </div>
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium mb-2 text-gray-700">Email</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full pl-12 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition"
                  placeholder="you@example.com"
                  required
                  data-testid="auth-email-input"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2 text-gray-700">Password</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full pl-12 pr-12 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition"
                  placeholder="••••••••"
                  required
                  minLength={6}
                  data-testid="auth-password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>
            
            {!isLogin && (
              <p className="text-xs text-gray-500 text-center">
                By creating an account you agree to our{' '}
                <Link to="/terms" className="text-[#6366F1] hover:underline" target="_blank" rel="noopener noreferrer">Terms</Link>
                {' '}and{' '}
                <Link to="/privacy" className="text-[#6366F1] hover:underline" target="_blank" rel="noopener noreferrer">Privacy Policy</Link>
                .
              </p>
            )}
            
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl font-medium transition flex items-center justify-center gap-2"
              data-testid="auth-submit-btn"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  {isLogin ? 'Sign In' : 'Create Account'}
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </form>
          )}
          
          {!mfaPending && (
          <p className="mt-8 text-center text-gray-600">
            {isLogin ? "Don't have an account?" : 'Already have an account?'}{' '}
            <button
              onClick={() => setIsLogin(!isLogin)}
              className="text-[#6366F1] hover:text-[#4F46E5] font-medium"
              data-testid="auth-toggle-btn"
            >
              {isLogin ? 'Sign up' : 'Sign in'}
            </button>
          </p>
          )}
        </motion.div>
      </div>
      </div>
    </div>
  );
};

export default AuthPage;
