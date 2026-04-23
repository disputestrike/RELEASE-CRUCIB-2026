import React from 'react';

const SUGGESTIONS = [
  { icon: '📊', label: 'Create slides', prompt: 'Create a presentation about...' },
  { icon: '🌐', label: 'Build website', prompt: 'Build a website for...' },
  { icon: '📱', label: 'Develop apps', prompt: 'Develop a mobile app for...' },
  { icon: '🎨', label: 'Design', prompt: 'Design a logo for...' },
  { icon: '📄', label: 'Landing page', prompt: 'Build a landing page with hero, features, and CTA...' },
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
