import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, Lock, User, Eye, EyeOff, Check, X, ArrowLeft, Github } from 'lucide-react';
import { useAuth, API } from '../App';

/**
 * AuthPage — Redesigned login/signup
 * 
 * Inspired by: Devin (minimal dark), Manus (OAuth-first), Bubble (inline validation),
 * Atoms (split panel with value prop), Replit (modal feel), Use.ai (social-first)
 * 
 * Design decisions:
 * - Split layout: left = form (white), right = value prop (branded gradient)
 * - OAuth buttons first (Google, GitHub) — matches developer audience
 * - Email/password below "or" divider
 * - Inline password validation on signup (Bubble pattern)
 * - Minimal fields: login = email + password, signup = name + email + password
 * - "Continue with" language (industry standard)
 * - Legal text always visible
 * - No marketing overload — the right panel handles that
 */

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
  const [processingToken, setProcessingToken] = useState(false);
  const [passwordFocused, setPasswordFocused] = useState(false);

  // Password validation rules (Bubble-inspired inline validation)
  const passwordChecks = [
    { label: 'At least 8 characters', met: formData.password.length >= 8 },
    { label: '1 uppercase letter', met: /[A-Z]/.test(formData.password) },
    { label: '1 number', met: /\d/.test(formData.password) },
    { label: '1 special character', met: /[!@#$%^&*(),.?":{}|<>]/.test(formData.password) },
  ];

  useEffect(() => {
    if (user) {
      const redirect = searchParams.get('redirect');
      navigate(redirect && redirect.startsWith('/') ? redirect : '/app');
      return;
    }
    const tokenFromUrl = searchParams.get('token');
    const errorFromUrl = searchParams.get('error');
    if (errorFromUrl) {
      setError(
        errorFromUrl === 'no_code' ? 'Google sign-in was cancelled.' :
        errorFromUrl === 'google_failed' ? 'Google sign-in failed. Try again.' :
        'Sign-in failed.'
      );
      return;
    }
    if (tokenFromUrl && loginWithToken && !processingToken) {
      setProcessingToken(true);
      setError('');
      loginWithToken(tokenFromUrl).catch((err) => {
        const msg = err?.response?.status === 401
          ? 'Session invalid. Please sign in again.'
          : err?.message?.includes('Network') || err?.code === 'ERR_NETWORK'
            ? 'Cannot reach server. Is the backend running?'
            : 'Sign-in failed. Please try again.';
        setError(msg);
        setProcessingToken(false);
      });
    }
  }, [user, searchParams, navigate, loginWithToken, processingToken]);

  const handleGoogleSignIn = () => {
    const backendUrl = API.replace('/api', '');
    const redirect = searchParams.get('redirect');
    const url = redirect
      ? `${backendUrl}/api/auth/google?redirect=${encodeURIComponent(redirect)}`
      : `${backendUrl}/api/auth/google`;
    window.location.href = url;
  };

  const handleGithubSignIn = () => {
    const backendUrl = API.replace('/api', '');
    const redirect = searchParams.get('redirect');
    const url = redirect
      ? `${backendUrl}/api/auth/github?redirect=${encodeURIComponent(redirect)}`
      : `${backendUrl}/api/auth/github`;
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

  // Processing token spinner
  if (processingToken) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FAFAF8]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-[#2563EB] border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-500 text-sm">Signing you in...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex" style={{ fontFamily: "'DM Sans', sans-serif" }}>
      {/* Left Panel — Form */}
      <div className="w-full lg:w-[480px] xl:w-[520px] flex flex-col bg-white relative">
        {/* Back button */}
        <div className="p-6">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-gray-400 hover:text-gray-700 transition text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Link>
        </div>

        {/* Form content */}
        <div className="flex-1 flex items-center justify-center px-8 pb-12">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="w-full max-w-[380px]"
          >
            {/* Logo */}
            <div className="mb-8">
              <Link to="/" className="inline-flex items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-br from-[#2563EB] to-[#7C3AED] rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">C</span>
                </div>
                <span className="text-xl font-bold tracking-tight text-gray-900">
                  Crucib<span className="text-[#2563EB]">AI</span>
                </span>
              </Link>
            </div>

            {/* Heading */}
            <h1 className="text-2xl font-bold text-gray-900 mb-1 tracking-tight">
              {mfaPending
                ? 'Two-factor authentication'
                : isLogin
                  ? 'Welcome back'
                  : 'Create your account'}
            </h1>
            <p className="text-gray-500 text-sm mb-8">
              {mfaPending
                ? 'Enter the 6-digit code from your authenticator app'
                : isLogin
                  ? 'Sign in to continue building'
                  : 'Start building with 50 free credits'}
            </p>

            {/* Error */}
            {error && (
              <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm flex items-start gap-2" data-testid="auth-error">
                <X className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* MFA Form */}
            {mfaPending ? (
              <form onSubmit={handleMfaSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Verification code</label>
                  <input
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/10 outline-none transition text-center text-2xl tracking-[0.5em] font-mono"
                    placeholder="000000"
                    maxLength={6}
                    autoFocus
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading || mfaCode.length !== 6}
                  className="w-full py-3 bg-[#2563EB] hover:bg-[#1D4ED8] disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed text-white rounded-lg font-medium transition text-sm"
                >
                  {loading ? <span className="inline-block w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : 'Verify'}
                </button>
                <button
                  type="button"
                  onClick={() => { setMfaPending(null); setMfaCode(''); setError(''); }}
                  className="w-full py-2 text-gray-500 hover:text-gray-700 text-sm transition"
                >
                  Back to sign in
                </button>
              </form>
            ) : (
              <>
                {/* OAuth Buttons — Primary actions */}
                <div className="space-y-3 mb-6">
                  <button
                    type="button"
                    onClick={handleGoogleSignIn}
                    className="w-full py-3 bg-white hover:bg-gray-50 border border-gray-200 rounded-lg font-medium transition flex items-center justify-center gap-3 text-gray-700 text-sm"
                    data-testid="auth-google-btn"
                  >
                    <svg className="w-5 h-5" viewBox="0 0 24 24">
                      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                    </svg>
                    Continue with Google
                  </button>

                  <button
                    type="button"
                    onClick={handleGithubSignIn}
                    className="w-full py-3 bg-[#24292F] hover:bg-[#1B1F23] border border-[#24292F] rounded-lg font-medium transition flex items-center justify-center gap-3 text-white text-sm"
                    data-testid="auth-github-btn"
                  >
                    <Github className="w-5 h-5" />
                    Continue with GitHub
                  </button>
                </div>

                {/* Divider */}
                <div className="relative mb-6">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-gray-200" />
                  </div>
                  <div className="relative flex justify-center text-xs">
                    <span className="px-3 bg-white text-gray-400 uppercase tracking-wider">or</span>
                  </div>
                </div>

                {/* Email/Password Form */}
                <form onSubmit={handleSubmit} className="space-y-4">
                  {!isLogin && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">Name</label>
                      <div className="relative">
                        <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                          type="text"
                          value={formData.name}
                          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                          className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/10 outline-none transition text-sm"
                          placeholder="Your name"
                          required={!isLogin}
                          data-testid="auth-name-input"
                        />
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Email</label>
                    <div className="relative">
                      <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/10 outline-none transition text-sm"
                        placeholder="you@example.com"
                        required
                        autoFocus={isLogin}
                        data-testid="auth-email-input"
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="block text-sm font-medium text-gray-700">Password</label>
                      {isLogin && (
                        <button type="button" className="text-xs text-[#2563EB] hover:text-[#1D4ED8] transition">
                          Forgot password?
                        </button>
                      )}
                    </div>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type={showPassword ? 'text' : 'password'}
                        value={formData.password}
                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                        onFocus={() => setPasswordFocused(true)}
                        onBlur={() => setPasswordFocused(false)}
                        className="w-full pl-10 pr-10 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/10 outline-none transition text-sm"
                        placeholder="••••••••"
                        required
                        minLength={6}
                        data-testid="auth-password-input"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition"
                        tabIndex={-1}
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>

                    {/* Inline password validation — signup only (Bubble-inspired) */}
                    {!isLogin && (passwordFocused || formData.password.length > 0) && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        className="mt-2 grid grid-cols-2 gap-1.5"
                      >
                        {passwordChecks.map((check) => (
                          <div key={check.label} className="flex items-center gap-1.5">
                            <div className={`w-3.5 h-3.5 rounded-full flex items-center justify-center ${check.met ? 'bg-green-500' : 'bg-gray-200'} transition-colors`}>
                              {check.met && <Check className="w-2.5 h-2.5 text-white" />}
                            </div>
                            <span className={`text-xs ${check.met ? 'text-green-600' : 'text-gray-400'} transition-colors`}>
                              {check.label}
                            </span>
                          </div>
                        ))}
                      </motion.div>
                    )}
                  </div>

                  {/* Submit */}
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-3 bg-[#2563EB] hover:bg-[#1D4ED8] disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed text-white rounded-lg font-medium transition text-sm flex items-center justify-center gap-2"
                    data-testid="auth-submit-btn"
                  >
                    {loading ? (
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      isLogin ? 'Sign in' : 'Start building'
                    )}
                  </button>
                </form>

                {/* Toggle login/signup */}
                <p className="mt-6 text-center text-gray-500 text-sm">
                  {isLogin ? "Don't have an account?" : 'Already have an account?'}{' '}
                  <button
                    onClick={() => { setIsLogin(!isLogin); setError(''); setFormData({ name: '', email: '', password: '' }); }}
                    className="text-[#2563EB] hover:text-[#1D4ED8] font-medium transition"
                    data-testid="auth-toggle-btn"
                  >
                    {isLogin ? 'Sign up' : 'Sign in'}
                  </button>
                </p>

                {/* Legal */}
                <p className="mt-6 text-center text-xs text-gray-400 leading-relaxed">
                  By continuing, you agree to our{' '}
                  <Link to="/terms" className="text-gray-500 hover:text-gray-700 underline" target="_blank" rel="noopener noreferrer">Terms of Service</Link>
                  {' '}and{' '}
                  <Link to="/privacy" className="text-gray-500 hover:text-gray-700 underline" target="_blank" rel="noopener noreferrer">Privacy Policy</Link>.
                </p>
              </>
            )}
          </motion.div>
        </div>
      </div>

      {/* Right Panel — Value Proposition (hidden on mobile) */}
      <div className="hidden lg:flex flex-1 bg-gradient-to-br from-[#1E3A5F] to-[#0F172A] relative overflow-hidden">
        {/* Subtle grid pattern */}
        <div className="absolute inset-0 opacity-[0.03]" style={{
          backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)',
          backgroundSize: '32px 32px'
        }} />

        <div className="relative z-10 flex flex-col justify-center w-full max-w-lg mx-auto px-12">
          {/* Main headline */}
          <h2 className="text-4xl font-bold text-white mb-4 tracking-tight leading-tight">
            {isLogin ? 'Pick up where you left off' : 'Turn ideas into apps that ship'}
          </h2>
          <p className="text-[#94A3B8] text-lg mb-10 leading-relaxed">
            {isLogin
              ? 'Your projects, agents, and builds are waiting.'
              : '120 AI agents plan, build, test, and deploy your app — while you watch every step.'}
          </p>

          {/* Benefits */}
          <div className="space-y-5 mb-12">
            {[
              { text: 'Plan-first architecture — no black boxes', check: true },
              { text: 'Full transparency into every agent decision', check: true },
              { text: 'Web, mobile, and automation — one platform', check: true },
              { text: '50 free credits, no credit card required', check: true },
            ].map((item, i) => (
              <motion.div
                key={item.text}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 + i * 0.1 }}
                className="flex items-center gap-3"
              >
                <div className="w-5 h-5 rounded-full bg-[#2563EB] flex items-center justify-center flex-shrink-0">
                  <Check className="w-3 h-3 text-white" />
                </div>
                <span className="text-white/90 text-sm">{item.text}</span>
              </motion.div>
            ))}
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-3 gap-6">
            {[
              { value: '120', label: 'AI agents' },
              { value: '99.2%', label: 'Success rate' },
              { value: '<72h', label: 'Delivery' },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 + i * 0.1 }}
              >
                <p className="text-2xl font-bold text-white">{stat.value}</p>
                <p className="text-xs text-[#64748B] uppercase tracking-wider mt-1">{stat.label}</p>
              </motion.div>
            ))}
          </div>

          {/* Testimonial */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="mt-12 p-5 bg-white/5 rounded-xl border border-white/10"
          >
            <p className="text-white/80 text-sm italic leading-relaxed">
              "We described our SaaS on Monday and had a working MVP by Thursday. The agent transparency is what sold us — we could see exactly what was being built."
            </p>
            <div className="mt-3 flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-[#2563EB]/20 flex items-center justify-center">
                <span className="text-[#60A5FA] text-xs font-bold">JM</span>
              </div>
              <div>
                <p className="text-white text-xs font-medium">Jordan M.</p>
                <p className="text-[#64748B] text-xs">Founder, SaaS startup</p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default AuthPage;
