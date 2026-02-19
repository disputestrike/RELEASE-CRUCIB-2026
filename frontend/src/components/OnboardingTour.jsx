import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, ChevronRight, ChevronLeft, Sparkles, MessageSquare, Code, Rocket, Layers, Search, Settings } from 'lucide-react';
import './OnboardingTour.css';

const TOUR_STEPS = [
  {
    id: 'welcome',
    title: 'Welcome to CrucibAI',
    description: 'The only platform where the same AI that builds your app runs inside your automations. Let\'s take a quick tour.',
    icon: Sparkles,
    target: null, // No highlight — full-screen welcome
    position: 'center',
  },
  {
    id: 'sidebar',
    title: 'Your Command Center',
    description: 'Search across everything, browse your tasks, and access the Engine Room for advanced tools. Press Ctrl+K to search instantly.',
    icon: Search,
    target: '.crucib-sidebar',
    position: 'right',
  },
  {
    id: 'workspace',
    title: 'The Workspace',
    description: 'Describe what you want to build. Our 120-agent swarm handles planning, code generation, testing, and deployment — all in one place.',
    icon: MessageSquare,
    target: null,
    position: 'center',
    navigateTo: '/app/workspace',
  },
  {
    id: 'preview',
    title: 'Live Preview',
    description: 'See your code running in real-time. Errors are auto-detected and fixed. Switch between Preview, Code, Terminal, and History tabs.',
    icon: Code,
    target: '.crucib-right-panel',
    position: 'left',
  },
  {
    id: 'agents',
    title: '120 Agents Working For You',
    description: 'Each build uses specialized agents — Frontend, Backend, Database, Security, Testing, Deployment — all orchestrated in a DAG pipeline.',
    icon: Layers,
    target: null,
    position: 'center',
    navigateTo: '/app/agents',
  },
  {
    id: 'deploy',
    title: 'One-Click Deploy',
    description: 'When your build is ready, deploy to Vercel, Netlify, or Railway with one click. Or download a deploy-ready ZIP.',
    icon: Rocket,
    target: null,
    position: 'center',
  },
  {
    id: 'settings',
    title: 'Make It Yours',
    description: 'Configure API keys, deploy tokens, themes, and more in Settings. Check the Engine Room in the sidebar for advanced tools.',
    icon: Settings,
    target: null,
    position: 'center',
    navigateTo: '/app/settings',
  },
  {
    id: 'ready',
    title: 'You\'re Ready!',
    description: 'Start by describing what you want to build in the Workspace. CrucibAI handles the rest. Welcome aboard.',
    icon: Sparkles,
    target: null,
    position: 'center',
    navigateTo: '/app/workspace',
  },
];

const STORAGE_KEY = 'crucibai_onboarding_complete';

export default function OnboardingTour({ forceShow = false, onComplete }) {
  const [active, setActive] = useState(false);
  const [step, setStep] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    if (forceShow) {
      setActive(true);
      setStep(0);
      return;
    }
    const done = localStorage.getItem(STORAGE_KEY);
    if (!done) {
      // Small delay so the app renders first
      const t = setTimeout(() => setActive(true), 1500);
      return () => clearTimeout(t);
    }
  }, [forceShow]);

  const currentStep = TOUR_STEPS[step];
  const isFirst = step === 0;
  const isLast = step === TOUR_STEPS.length - 1;

  const handleNext = useCallback(() => {
    if (isLast) {
      handleClose();
      return;
    }
    const nextStep = TOUR_STEPS[step + 1];
    if (nextStep.navigateTo) {
      navigate(nextStep.navigateTo);
    }
    setStep((s) => s + 1);
  }, [step, isLast, navigate]);

  const handlePrev = useCallback(() => {
    if (isFirst) return;
    const prevStep = TOUR_STEPS[step - 1];
    if (prevStep.navigateTo) {
      navigate(prevStep.navigateTo);
    }
    setStep((s) => s - 1);
  }, [step, isFirst, navigate]);

  const handleClose = useCallback(() => {
    setActive(false);
    localStorage.setItem(STORAGE_KEY, 'true');
    if (onComplete) onComplete();
  }, [onComplete]);

  const handleSkip = useCallback(() => {
    handleClose();
    navigate('/app/workspace');
  }, [handleClose, navigate]);

  // Keyboard navigation
  useEffect(() => {
    if (!active) return;
    const handler = (e) => {
      if (e.key === 'Escape') handleClose();
      if (e.key === 'ArrowRight' || e.key === 'Enter') handleNext();
      if (e.key === 'ArrowLeft') handlePrev();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [active, handleNext, handlePrev, handleClose]);

  if (!active) return null;

  const Icon = currentStep.icon;

  return (
    <div className="onboarding-overlay" onClick={handleClose}>
      {/* Spotlight effect for targeted steps */}
      {currentStep.target && (
        <SpotlightHighlight selector={currentStep.target} />
      )}

      <div
        className={`onboarding-card onboarding-card--${currentStep.position}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Progress bar */}
        <div className="onboarding-progress">
          {TOUR_STEPS.map((_, i) => (
            <div
              key={i}
              className={`onboarding-progress-dot ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}
            />
          ))}
        </div>

        {/* Icon */}
        <div className="onboarding-icon">
          <Icon size={28} />
        </div>

        {/* Content */}
        <h3 className="onboarding-title">{currentStep.title}</h3>
        <p className="onboarding-desc">{currentStep.description}</p>

        {/* Step counter */}
        <div className="onboarding-step-count">
          {step + 1} of {TOUR_STEPS.length}
        </div>

        {/* Actions */}
        <div className="onboarding-actions">
          {isFirst ? (
            <button className="onboarding-btn onboarding-btn--ghost" onClick={handleSkip}>
              Skip tour
            </button>
          ) : (
            <button className="onboarding-btn onboarding-btn--ghost" onClick={handlePrev}>
              <ChevronLeft size={16} /> Back
            </button>
          )}
          <button className="onboarding-btn onboarding-btn--primary" onClick={handleNext}>
            {isLast ? 'Start Building' : 'Next'} <ChevronRight size={16} />
          </button>
        </div>

        {/* Close */}
        <button className="onboarding-close" onClick={handleClose} title="Close tour">
          <X size={16} />
        </button>
      </div>
    </div>
  );
}

/** Spotlight highlight for a CSS selector */
function SpotlightHighlight({ selector }) {
  const [rect, setRect] = useState(null);

  useEffect(() => {
    const el = document.querySelector(selector);
    if (el) {
      const r = el.getBoundingClientRect();
      setRect({ top: r.top - 8, left: r.left - 8, width: r.width + 16, height: r.height + 16 });
    }
  }, [selector]);

  if (!rect) return null;

  return (
    <div
      className="onboarding-spotlight"
      style={{
        top: rect.top,
        left: rect.left,
        width: rect.width,
        height: rect.height,
      }}
    />
  );
}

/** Hook to trigger onboarding tour from anywhere */
export function useOnboardingTour() {
  const reset = () => localStorage.removeItem(STORAGE_KEY);
  const isComplete = () => localStorage.getItem(STORAGE_KEY) === 'true';
  return { reset, isComplete };
}
