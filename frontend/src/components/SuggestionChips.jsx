import React from 'react';

const SUGGESTIONS = [
  { icon: '🌐', label: 'Build website', prompt: 'Build a multi-page website with hero, features, pricing, and contact sections' },
  { icon: '⚙️', label: 'Develop app', prompt: 'Build a full-stack web app with user authentication and dashboard' },
  { icon: '📱', label: 'Mobile app', prompt: 'Build a React Native mobile app with navigation and multiple screens' },
  { icon: '🛒', label: 'E-commerce store', prompt: 'Build an e-commerce store with product catalog, cart, and PayPal checkout' },
  { icon: '🤖', label: 'AI chatbot', prompt: 'Build an AI chatbot with a knowledge base and multi-agent support' },
  { icon: '📊', label: 'SaaS MVP', prompt: 'Build a SaaS MVP with authentication, PayPal billing, and user dashboard' },
  { icon: '⚡', label: 'Automation', prompt: 'Build an automation that runs daily and sends results to Slack or email' },
  { icon: '🛠️', label: 'Internal tool', prompt: 'Build an internal admin tool with data tables, forms, and approval workflows' },
];

const SuggestionChips = ({ onSelect, disabled }) => {
  return (
    <div className="flex flex-wrap gap-3 justify-center mt-5 px-4">
      {SUGGESTIONS.map((s, i) => (
        <button
          key={i}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(s.prompt)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-[#f8f9fa] border border-[#e5e7eb] rounded-full text-sm font-medium text-[#374151] hover:bg-[#e5e7eb] hover:border-[#d1d5db] transition-all duration-200 hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
        >
          <span className="text-base">{s.icon}</span>
          <span className="whitespace-nowrap">{s.label}</span>
        </button>
      ))}
    </div>
  );
};

export default SuggestionChips;
