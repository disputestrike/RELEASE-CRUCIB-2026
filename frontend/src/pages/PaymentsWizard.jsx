import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CreditCard, Key, Code, CheckCircle } from 'lucide-react';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import axios from 'axios';

export default function PaymentsWizard() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [step, setStep] = useState(1);
  const [injecting, setInjecting] = useState(false);
  const [injectedCode, setInjectedCode] = useState('');

  const handleInjectBraintree = async () => {
    if (!token) {
      navigate('/app');
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
        `${API}/ai/inject-braintree`,
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
          <div className="p-3 rounded-xl bg-[#F3F1ED]">
            <CreditCard className="w-8 h-8 text-[#1A1A1A]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Add payments (Braintree)</h1>
            <p className="text-zinc-400">Wizard to add Braintree Checkout to your app</p>
          </div>
        </div>
        <div className="space-y-6">
          {step === 1 && (
            <>
              <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/50">
                <div className="flex items-start gap-4">
                  <Key className="w-6 h-6 text-zinc-400 shrink-0 mt-0.5" />
                  <div>
                    <h2 className="font-semibold mb-2">Step 1: Get your Braintree keys</h2>
                    <p className="text-sm text-zinc-400">Create a Braintree account, then add BRAINTREE_MERCHANT_ID, BRAINTREE_PUBLIC_KEY, BRAINTREE_PRIVATE_KEY, and BRAINTREE_ENVIRONMENT to your project env.</p>
                  </div>
                </div>
              </div>
              <button onClick={() => setStep(2)} className="px-4 py-2 rounded-lg bg-[#1A1A1A] text-white hover:bg-[#333]">Next</button>
            </>
          )}
          {step === 2 && (
            <>
              <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/50">
                <div className="flex items-start gap-4">
                  <Code className="w-6 h-6 text-zinc-400 shrink-0 mt-0.5" />
                  <div>
                    <h2 className="font-semibold mb-2">Step 2: Inject Braintree into your code</h2>
                    <p className="text-sm text-zinc-400">We'll add Braintree Checkout to your React app. Run this from the Workspace with your current App.js, or use the sample below.</p>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => setStep(1)} className="px-4 py-2 rounded-lg bg-zinc-800 text-zinc-300">Back</button>
                <button onClick={handleInjectBraintree} disabled={injecting} className="px-4 py-2 rounded-lg bg-[#F3F1ED] text-[#1A1A1A] hover:bg-[#333] disabled:opacity-50">
                  {injecting ? 'Injecting...' : 'Inject Braintree'}
                </button>
              </div>
            </>
          )}
          {step === 3 && (
            <>
              <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/50">
                <div className="flex items-start gap-4">
                  <CheckCircle className="w-6 h-6 text-[#1A1A1A] shrink-0 mt-0.5" />
                  <div>
                    <h2 className="font-semibold mb-2">Step 3: Use the code</h2>
                    <p className="text-sm text-zinc-400 mb-3">Copy the code below into your App.js in the Workspace, or start from a template that includes Braintree.</p>
                    <pre className="text-xs bg-zinc-900 p-3 rounded overflow-auto max-h-48 text-zinc-300">{injectedCode || '// No code generated'}</pre>
                  </div>
                </div>
              </div>
              <button onClick={() => navigate('/app/workspace')} className="px-4 py-2 rounded-lg bg-[#1A1A1A] text-white hover:bg-[#333]">Open Workspace</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
