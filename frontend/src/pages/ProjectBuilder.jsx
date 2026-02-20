import { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Globe, Server, Database, Layers, Zap, ArrowRight, 
  ArrowLeft, Check, AlertCircle, Bot, Sparkles, Smartphone, Gamepad2, Cpu, TrendingUp
} from 'lucide-react';
import { useAuth, API } from '../App';
import axios from 'axios';

const ProjectBuilder = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { token, user, refreshUser } = useAuth();
  
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    project_type: searchParams.get('type') || '',
    requirements: {
      features: [],
      tech_stack: '',
      styling: '',
      auth: false,
      database: true,
      deployment: 'vercel'
    }
  });

  const projectTypes = [
    { id: 'fullstack', name: 'Full-Stack App', icon: Layers, desc: 'Web apps, dashboards, tools', tokens: 675000 },
    { id: 'website', name: 'Website', icon: Globe, desc: 'Landing pages, portfolios, blogs', tokens: 400000 },
    { id: 'mobile', name: 'Mobile App', icon: Smartphone, desc: 'React Native, Flutter, PWA', tokens: 600000 },
    { id: 'saas', name: 'SaaS', icon: Layers, desc: 'Subscriptions, billing, multi-tenant', tokens: 700000 },
    { id: 'bot', name: 'Bot', icon: Bot, desc: 'Slack, Discord, Telegram, webhooks', tokens: 350000 },
    { id: 'ai_agent', name: 'AI Agent', icon: Cpu, desc: 'Agents with tools, prompts, API', tokens: 500000 },
    { id: 'game', name: 'Game', icon: Gamepad2, desc: 'Browser, mobile, 2D/3D, scores', tokens: 600000 },
    { id: 'trading', name: 'Trading / Fintech', icon: TrendingUp, desc: 'Stocks, crypto, forex, orders, P&L, charts', tokens: 650000 },
    { id: 'any', name: 'Anything', icon: Sparkles, desc: 'No limit—we build whatever you describe', tokens: 675000 },
    { id: 'api', name: 'API Backend', icon: Server, desc: 'REST/GraphQL APIs', tokens: 350000 },
    { id: 'automation', name: 'Automation', icon: Bot, desc: 'Scripts, scrapers, workflows', tokens: 250000 }
  ];

  const selectedType = projectTypes.find(t => t.id === formData.project_type);

  const handleSubmit = async () => {
    setError('');
    setLoading(true);
    
    try {
      const payload = {
        ...formData,
        estimated_tokens: selectedType?.tokens,
        requirements: {
          ...formData.requirements,
          prompt: formData.description,
          build_kind: ['mobile', 'saas', 'bot', 'ai_agent', 'game', 'trading', 'any'].includes(formData.project_type)
            ? formData.project_type
            : formData.project_type === 'fullstack' ? 'fullstack' : 'fullstack'
        }
      };
      const res = await axios.post(`${API}/projects`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      await refreshUser();
      navigate(`/app/projects/${res.data.project.id}`);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  const canProceed = () => {
    if (step === 1) return !!formData.project_type;
    if (step === 2) return formData.name.length >= 3 && formData.description.length >= 10;
    return true;
  };

  return (
    <div className="max-w-4xl mx-auto" data-testid="project-builder">
      {/* Progress */}
      <div className="mb-8">
        <div className="flex items-center gap-4 mb-4">
          {[1, 2, 3].map(s => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-medium transition-all ${
                step > s ? 'bg-green-500 text-[#1A1A1A]' :
                step === s ? 'bg-orange-500 text-[#1A1A1A]' :
                'bg-white/10 text-gray-500'
              }`}>
                {step > s ? <Check className="w-4 h-4" /> : s}
              </div>
              {s < 3 && <div className={`w-12 h-0.5 ${step > s ? 'bg-green-500' : 'bg-white/10'}`}></div>}
            </div>
          ))}
        </div>
        <h2 className="text-sm text-gray-500">
          Step {step} of 3: {step === 1 ? 'Select Type' : step === 2 ? 'Project Details' : 'Review & Create'}
        </h2>
      </div>

      {/* Step 1: Project Type */}
      {step === 1 && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <h1 className="text-3xl font-bold mb-2">What would you like to build?</h1>
          <p className="text-[#666666] mb-8">Select the type of project you want to create.</p>
          
          <div className="grid md:grid-cols-2 gap-4">
            {projectTypes.map(type => (
              <button
                key={type.id}
                onClick={() => setFormData({ ...formData, project_type: type.id })}
                className={`p-6 rounded-xl border text-left transition-all ${
                  formData.project_type === type.id
                    ? 'bg-orange-500/10 border-orange-500/50'
                    : 'bg-[#0a0a0a] border-white/10 hover:border-white/20'
                }`}
                data-testid={`project-type-${type.id}`}
              >
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                    formData.project_type === type.id ? 'bg-orange-500/20' : 'bg-white/5'
                  }`}>
                    <type.icon className={`w-6 h-6 ${
                      formData.project_type === type.id ? 'text-orange-400' : 'text-[#666666]'
                    }`} />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold mb-1">{type.name}</h3>
                    <p className="text-sm text-gray-500 mb-2">{type.desc}</p>
                    <div className="flex items-center gap-2 text-xs">
                      <Zap className="w-3 h-3 text-yellow-500" />
                      <span className="text-[#666666]">~{(type.tokens / 1000).toFixed(0)}K tokens</span>
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </motion.div>
      )}

      {/* Step 2: Project Details */}
      {step === 2 && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <h1 className="text-3xl font-bold mb-2">Tell us about your project</h1>
          <p className="text-[#666666] mb-8">Describe what you want to build. The more detail, the better.</p>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2">Project Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none transition"
                placeholder="My Awesome App"
                data-testid="project-name-input"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={4}
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none transition resize-none"
                placeholder="Describe your project in detail. What features do you need? What's the purpose?"
                data-testid="project-description-input"
              />
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Styling Preference</label>
                <select
                  value={formData.requirements.styling}
                  onChange={(e) => setFormData({ 
                    ...formData, 
                    requirements: { ...formData.requirements, styling: e.target.value } 
                  })}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg focus:border-orange-500 outline-none"
                  data-testid="project-styling-select"
                >
                  <option value="">Select style</option>
                  <option value="modern">Modern & Minimal</option>
                  <option value="dark">Dark Mode</option>
                  <option value="corporate">Corporate</option>
                  <option value="playful">Playful & Colorful</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">Deployment</label>
                <select
                  value={formData.requirements.deployment}
                  onChange={(e) => setFormData({ 
                    ...formData, 
                    requirements: { ...formData.requirements, deployment: e.target.value } 
                  })}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg focus:border-orange-500 outline-none"
                  data-testid="project-deployment-select"
                >
                  <option value="vercel">Vercel</option>
                  <option value="railway">Railway</option>
                  <option value="aws">AWS</option>
                  <option value="manual">Manual Download</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-6">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.requirements.auth}
                  onChange={(e) => setFormData({ 
                    ...formData, 
                    requirements: { ...formData.requirements, auth: e.target.checked } 
                  })}
                  className="w-5 h-5 rounded border-white/20 bg-white/5 text-orange-500 focus:ring-orange-500"
                />
                <span>User Authentication</span>
              </label>
              
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.requirements.database}
                  onChange={(e) => setFormData({ 
                    ...formData, 
                    requirements: { ...formData.requirements, database: e.target.checked } 
                  })}
                  className="w-5 h-5 rounded border-white/20 bg-white/5 text-orange-500 focus:ring-orange-500"
                />
                <span>Database</span>
              </label>
            </div>
          </div>
        </motion.div>
      )}

      {/* Step 3: Review */}
      {step === 3 && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <h1 className="text-3xl font-bold mb-2">Review your project</h1>
          <p className="text-[#666666] mb-8">Make sure everything looks good before we start generating.</p>
          
          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
              <div className="flex items-center gap-3">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span>{error}</span>
              </div>
              {(error.includes('Acceptable Use') || error.toLowerCase().includes('violates')) && (
                <p className="mt-2 text-sm">
                  <Link to="/aup" className="text-orange-400 hover:underline">View Acceptable Use Policy</Link>
                  {' '}· Appeals: appeals@crucibai.com
                </p>
              )}
            </div>
          )}

          <div className="p-6 bg-[#0a0a0a] rounded-xl border border-white/10 space-y-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-orange-500/20 rounded-lg flex items-center justify-center">
                {selectedType && <selectedType.icon className="w-6 h-6 text-orange-400" />}
              </div>
              <div>
                <h3 className="text-xl font-semibold">{formData.name}</h3>
                <p className="text-[#666666]">{selectedType?.name}</p>
              </div>
            </div>
            
            <div className="border-t border-white/10 pt-4">
              <h4 className="text-sm font-medium text-gray-500 mb-2">Description</h4>
              <p className="text-gray-300">{formData.description}</p>
            </div>
            
            <div className="grid md:grid-cols-3 gap-4 border-t border-white/10 pt-4">
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1">Styling</h4>
                <p className="capitalize">{formData.requirements.styling || 'Default'}</p>
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1">Deployment</h4>
                <p className="capitalize">{formData.requirements.deployment}</p>
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1">Features</h4>
                <p>
                  {formData.requirements.auth && 'Auth, '}
                  {formData.requirements.database && 'Database'}
                  {!formData.requirements.auth && !formData.requirements.database && 'Basic'}
                </p>
              </div>
            </div>

            <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Zap className="w-5 h-5 text-yellow-500" />
                  <div>
                    <p className="font-medium">Estimated Token Cost</p>
                    <p className="text-sm text-[#666666]">~{((selectedType?.tokens || 0) / 1000).toFixed(0)}K tokens</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm text-[#666666]">Your balance</p>
                  <p className="font-bold text-lg">{user?.token_balance?.toLocaleString()}</p>
                </div>
              </div>
              {(user?.token_balance || 0) < (selectedType?.tokens || 0) && (
                <p className="mt-3 text-sm text-red-400">Insufficient tokens. Please purchase more.</p>
              )}
            </div>
          </div>
        </motion.div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between mt-8">
        <button
          onClick={() => setStep(Math.max(1, step - 1))}
          className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition ${
            step === 1 ? 'opacity-50 cursor-not-allowed' : 'bg-white/10 hover:bg-white/20'
          }`}
          disabled={step === 1}
        >
          <ArrowLeft className="w-5 h-5" />
          Back
        </button>
        
        {step < 3 ? (
          <button
            onClick={() => setStep(step + 1)}
            disabled={!canProceed()}
            className="flex items-center gap-2 px-6 py-3 bg-orange-500 hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg font-medium transition neon-orange"
            data-testid="next-step-btn"
          >
            Continue
            <ArrowRight className="w-5 h-5" />
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={loading || (user?.token_balance || 0) < (selectedType?.tokens || 0)}
            className="flex items-center gap-2 px-8 py-3 bg-green-500 hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg font-medium transition"
            data-testid="create-project-btn"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                Start Generation
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
};

export default ProjectBuilder;