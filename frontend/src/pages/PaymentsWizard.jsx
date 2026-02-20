import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CreditCard, Key, Code, CheckCircle } from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';

export default function PaymentsWizard() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [step, setStep] = useState(1);
  const [injecting, setInjecting] = useState(false);
  const [injectedCode, setInjectedCode] = useState('');

  const handleInjectStripe = async () => {
    if (!token) {
      navigate('/auth');
      return;
    }
    setInjecting(true);
    try {
      const sampleCode = `export default function App() {
  return (
    <div className="p-8">
      <h1>My App</h1>
      <button>Buy now</button>
    </div>
  );
}`;
      const res = await axios.post(
        `${API}/ai/inject-stripe`,
        { code: sampleCode, target: 'checkout' },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setInjectedCode(res.data.code || '');
      setStep(3);
    } catch (e) {
      setInjectedCode(`// Error: ${e.message}`);
      setStep(3);
    } finally {
      setInjecting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A] p-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-3 rounded-xl bg-gray-500/20">
            <CreditCard className="w-8 h-8 text-gray-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Add payments (Stripe)</h1>
            <p className="text-gray-400">Wizard to add Stripe Checkout to your app</p>
          </div>
        </div>
        <div className="space-y-6">
          {step === 1 && (
            <>
              <div className="p-5 rounded-xl border border-gray-800 bg-gray-900/50">
                <div className="flex items-start gap-4">
                  <Key className="w-6 h-6 text-gray-400 shrink-0 mt-0.5" />
                  <div>
                    <h2 className="font-semibold mb-2">Step 1: Get your Stripe keys</h2>
                    <p className="text-sm text-gray-400">Sign up at stripe.com, get your Publishable key and Secret key from the Dashboard. Add them to your project env (e.g. in Workspace Env panel).</p>
                  </div>
                </div>
              </div>
              <button onClick={() => setStep(2)} className="px-4 py-2 rounded-lg bg-gray-200/20 text-gray-500 hover:bg-gray-200/30">Next</button>
            </>
          )}
          {step === 2 && (
            <>
              <div className="p-5 rounded-xl border border-gray-800 bg-gray-900/50">
                <div className="flex items-start gap-4">
                  <Code className="w-6 h-6 text-gray-400 shrink-0 mt-0.5" />
                  <div>
                    <h2 className="font-semibold mb-2">Step 2: Inject Stripe into your code</h2>
                    <p className="text-sm text-gray-400">We'll add Stripe Checkout to your React app. Run this from the Workspace with your current App.js, or use the sample below.</p>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => setStep(1)} className="px-4 py-2 rounded-lg bg-gray-800 text-gray-300">Back</button>
                <button onClick={handleInjectStripe} disabled={injecting} className="px-4 py-2 rounded-lg bg-gray-500/20 text-gray-400 hover:bg-gray-500/30 disabled:opacity-50">
                  {injecting ? 'Injecting...' : 'Inject Stripe'}
                </button>
              </div>
            </>
          )}
          {step === 3 && (
            <>
              <div className="p-5 rounded-xl border border-gray-800 bg-gray-900/50">
                <div className="flex items-start gap-4">
                  <CheckCircle className="w-6 h-6 text-gray-400 shrink-0 mt-0.5" />
                  <div>
                    <h2 className="font-semibold mb-2">Step 3: Use the code</h2>
                    <p className="text-sm text-gray-400 mb-3">Copy the code below into your App.js in the Workspace, or start from a template that includes Stripe.</p>
                    <pre className="text-xs bg-gray-900 p-3 rounded overflow-auto max-h-48 text-gray-300">{injectedCode || '// No code generated'}</pre>
                  </div>
                </div>
              </div>
              <button onClick={() => navigate('/workspace')} className="px-4 py-2 rounded-lg bg-gray-200/20 text-gray-500 hover:bg-gray-200/30">Open Workspace</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
