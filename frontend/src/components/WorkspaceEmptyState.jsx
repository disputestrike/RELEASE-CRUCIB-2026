/**
 * WorkspaceEmptyState
 *
 * Shown when the chat has no messages yet. Displays a greeting and
 * 3 contextual example prompts tailored to the detected project type
 * (or generic ones if no type is known).
 */
import { Sparkles } from 'lucide-react';

const PROMPT_SETS = {
  landing: [
    'Build a modern SaaS landing page with hero, features, pricing, and CTA',
    'Create a personal portfolio with animated sections and a contact form',
    'Build a product launch page with countdown timer and email capture',
  ],
  dashboard: [
    'Build an admin dashboard with charts, user table, and sidebar nav',
    'Create a project management board with drag-and-drop cards',
    'Build an analytics dashboard with line charts and KPI cards',
  ],
  mobile: [
    'Build a React Native todo app with push notifications',
    'Create a food delivery app with product grid and cart',
    'Build a fitness tracker with daily goals and progress charts',
  ],
  ecommerce: [
    'Build an e-commerce store with product catalog, cart, and Braintree checkout',
    'Create a marketplace with seller dashboard and buyer reviews',
    'Build a subscription box shop with recurring billing',
  ],
  saas: [
    'Build a SaaS MVP with auth, Braintree billing, and user dashboard',
    'Create a multi-tenant SaaS with team workspaces and role-based access',
    'Build an AI-powered writing tool with subscription tiers',
  ],
  default: [
    'Build a full-stack web app with user auth and a dashboard',
    'Create an AI chatbot with a custom knowledge base',
    'Build an e-commerce store with cart and Braintree checkout',
  ],
};

function detectType(projectType) {
  if (!projectType) return 'default';
  const t = projectType.toLowerCase();
  if (t.includes('land') || t.includes('portfolio')) return 'landing';
  if (t.includes('dash') || t.includes('admin')) return 'dashboard';
  if (t.includes('mobile') || t.includes('native') || t.includes('expo')) return 'mobile';
  if (t.includes('ecom') || t.includes('shop') || t.includes('store')) return 'ecommerce';
  if (t.includes('saas') || t.includes('subscript')) return 'saas';
  return 'default';
}

export default function WorkspaceEmptyState({ projectType, onPromptSelect, disabled }) {
  const type = detectType(projectType);
  const prompts = PROMPT_SETS[type] || PROMPT_SETS.default;

  return (
    <div className="flex flex-col items-center justify-center h-full gap-5 px-4 py-8">
      <div
        className="w-10 h-10 rounded-full flex items-center justify-center"
        style={{ background: 'var(--theme-input, #27272a)' }}
      >
        <Sparkles className="w-5 h-5" style={{ color: 'var(--theme-muted, #a1a1aa)' }} />
      </div>

      <div className="text-center space-y-1">
        <p className="text-sm font-medium" style={{ color: 'var(--theme-text, #e4e4e7)' }}>
          What would you like to build?
        </p>
        <p className="text-xs" style={{ color: 'var(--theme-muted, #71717a)' }}>
          Try one of these or describe your idea below
        </p>
      </div>

      <div className="flex flex-col gap-2 w-full max-w-sm">
        {prompts.map((prompt, i) => (
          <button
            key={i}
            type="button"
            disabled={disabled}
            onClick={() => onPromptSelect(prompt)}
            className="text-left px-4 py-3 rounded-xl text-xs transition hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              background: 'var(--theme-surface2, rgba(255,255,255,0.04))',
              border: '1px solid var(--theme-border, rgba(255,255,255,0.08))',
              color: 'var(--theme-muted, #a1a1aa)',
            }}
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
