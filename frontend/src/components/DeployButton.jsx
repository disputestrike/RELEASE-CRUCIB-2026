import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download, ExternalLink, FileText, ChevronDown, Globe } from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';

const DEPLOY_INSTRUCTIONS = `# Deploy this project

## Vercel (recommended)
1. Go to https://vercel.com/new
2. Import this folder or upload the ZIP (Vercel will extract it).
3. Set build command: (leave default for Create React App)
4. Deploy.

## Netlify
1. Go to https://app.netlify.com/drop
2. Drag and drop this folder (or the ZIP).
3. Site deploys automatically.

## Railway
1. Go to https://railway.app/new
2. Create a new project, then "Deploy from GitHub repo" (push this folder to a repo first) or use "Empty project" and deploy via Railway CLI from this folder.
3. Add a service (e.g. Web Service for Node/React, or static site).
4. Deploy.

Generated with CrucibAI.`;

const RAILWAY_NEW_URL = 'https://railway.app/new';

export default function DeployButton({ projectId, variant = 'dropdown', onFeedback }) {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [deploying, setDeploying] = useState(null); // 'vercel' | 'netlify'
  const [showInstructions, setShowInstructions] = useState(false);
  const [instructionsCopied, setInstructionsCopied] = useState(false);
  const [open, setOpen] = useState(false);

  const notify = (msg, type = 'success') => {
    if (onFeedback) onFeedback({ type, msg });
    else if (typeof window !== 'undefined' && window.toast) window.toast(msg);
  };

  const handleDownloadZip = async () => {
    if (!projectId || !token) return;
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/projects/${projectId}/deploy/zip`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = 'crucibai-deploy.zip';
      a.click();
      window.URL.revokeObjectURL(url);
      notify('Deploy ZIP downloaded! Upload it to Vercel or Netlify.', 'deploy');
      setOpen(false);
    } catch (err) {
      const msg = err.response?.status === 404
        ? 'No deploy snapshot. Re-run build or use Deploy in Workspace.'
        : (err.response?.data?.detail || 'Download failed');
      notify(msg, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleOneClickDeploy = async (provider) => {
    if (!projectId || !token) return;
    setDeploying(provider);
    setOpen(false);
    try {
      const { data } = await axios.post(
        `${API}/projects/${projectId}/deploy/${provider}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const url = data?.url;
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer');
        notify(`Live on ${provider}! Opening ${url}`, 'deploy');
      } else {
        notify(`Deploy started on ${provider}. Check your dashboard.`, 'deploy');
      }
    } catch (err) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail || err.message;
      if (status === 402) {
        notify('Add your token in Settings → Deploy for one-click deploy.', 'error');
        navigate('/app/settings', { state: { openTab: 'deploy' } });
      } else {
        notify(detail || `Deploy to ${provider} failed`, 'error');
      }
    } finally {
      setDeploying(null);
    }
  };

  const handleCopyInstructions = async () => {
    try {
      await navigator.clipboard.writeText(DEPLOY_INSTRUCTIONS);
      setInstructionsCopied(true);
      notify('Deploy instructions copied to clipboard.');
      setTimeout(() => setInstructionsCopied(false), 2000);
    } catch {
      setShowInstructions(true);
    }
  };

  const buttonContent =
    variant === 'icon' ? (
      <Globe className="w-4 h-4" />
    ) : (
    <>
      <Download className="w-4 h-4" />
      <span>Deploy</span>
      {variant === 'dropdown' && <ChevronDown className="w-4 h-4 opacity-70" />}
    </>
  );

  const options = (
    <div className="flex flex-col gap-1 py-1 min-w-[200px]">
      <button
        type="button"
        onClick={handleDownloadZip}
        disabled={loading}
        className="flex items-center gap-2 w-full px-3 py-2 text-left text-sm hover:bg-white/10 rounded-lg disabled:opacity-60"
      >
        <Download className="w-4 h-4 shrink-0" />
        {loading ? 'Preparing…' : 'Download Deploy ZIP'}
      </button>
      <button
        type="button"
        onClick={() => handleOneClickDeploy('vercel')}
        disabled={deploying !== null}
        className="flex items-center gap-2 w-full px-3 py-2 text-left text-sm hover:bg-white/10 rounded-lg disabled:opacity-60"
      >
        <ExternalLink className="w-4 h-4 shrink-0" />
        {deploying === 'vercel' ? 'Deploying…' : 'One-click Deploy to Vercel'}
      </button>
      <button
        type="button"
        onClick={() => handleOneClickDeploy('netlify')}
        disabled={deploying !== null}
        className="flex items-center gap-2 w-full px-3 py-2 text-left text-sm hover:bg-white/10 rounded-lg disabled:opacity-60"
      >
        <ExternalLink className="w-4 h-4 shrink-0" />
        {deploying === 'netlify' ? 'Deploying…' : 'One-click Deploy to Netlify'}
      </button>
      <button
        type="button"
        onClick={() => { window.open(RAILWAY_NEW_URL, '_blank'); setOpen(false); notify('Open Railway, then connect a repo or use CLI with your ZIP.', 'deploy'); }}
        className="flex items-center gap-2 w-full px-3 py-2 text-left text-sm hover:bg-white/10 rounded-lg"
      >
        <ExternalLink className="w-4 h-4 shrink-0" />
        Deploy to Railway
      </button>
      <button
        type="button"
        onClick={() => { setShowInstructions(true); setOpen(false); }}
        className="flex items-center gap-2 w-full px-3 py-2 text-left text-sm hover:bg-white/10 rounded-lg"
      >
        <FileText className="w-4 h-4 shrink-0" />
        Get Deploy Instructions
      </button>
    </div>
  );

  return (
    <>
      {variant === 'dropdown' || variant === 'icon' ? (
        <div className="relative inline-block">
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            className={variant === 'icon'
              ? 'p-2 text-gray-500 hover:text-emerald-600 hover:bg-emerald-500/10 rounded-lg transition'
              : 'inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-[#1A1A1A] font-medium text-sm transition'
            }
            title="Deploy (ZIP, Vercel, Netlify)"
          >
            {buttonContent}
          </button>
          {open && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} aria-hidden="true" />
              <div className="absolute right-0 mt-1 z-20 py-1 px-1 rounded-lg border border-white/10 bg-[#0a0a0a] shadow-xl">
                {options}
              </div>
            </>
          )}
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleDownloadZip}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-[#1A1A1A] text-sm font-medium"
          >
            <Download className="w-4 h-4" />
            {loading ? 'Preparing…' : 'Download Deploy ZIP'}
          </button>
          <button
            type="button"
            onClick={() => handleOneClickDeploy('vercel')}
            disabled={deploying !== null}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-[#1A1A1A] text-sm font-medium"
          >
            <ExternalLink className="w-4 h-4" />
            {deploying === 'vercel' ? 'Deploying…' : 'One-click Vercel'}
          </button>
          <button
            type="button"
            onClick={() => handleOneClickDeploy('netlify')}
            disabled={deploying !== null}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-[#1A1A1A] text-sm font-medium"
          >
            <ExternalLink className="w-4 h-4" />
            {deploying === 'netlify' ? 'Deploying…' : 'One-click Netlify'}
          </button>
          <button
            type="button"
            onClick={() => setShowInstructions(true)}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-white/20 hover:bg-white/10 text-sm"
          >
            <FileText className="w-4 h-4" />
            Get instructions
          </button>
        </div>
      )}

      {showInstructions && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80" onClick={() => setShowInstructions(false)}>
          <div className="bg-[#0a0a0a] border border-white/10 rounded-xl max-w-lg w-full max-h-[80vh] overflow-hidden shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="p-4 border-b border-white/10 flex items-center justify-between">
              <h3 className="font-semibold">Deploy instructions</h3>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleCopyInstructions}
                  className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-sm"
                >
                  {instructionsCopied ? 'Copied!' : 'Copy'}
                </button>
                <button type="button" onClick={() => setShowInstructions(false)} className="p-1.5 rounded-lg hover:bg-white/10">×</button>
              </div>
            </div>
            <pre className="p-4 text-sm text-gray-300 whitespace-pre-wrap overflow-auto max-h-[60vh] font-mono">
              {DEPLOY_INSTRUCTIONS}
            </pre>
          </div>
        </div>
      )}
    </>
  );
}
