import React from 'react';
import { Clock, Zap, Flame } from 'lucide-react';

export default function WorkspaceHeaderSpeed({ speedTier }) {
  const speedLabels = {
    lite: { label: 'Lite', icon: Clock, color: 'text-gray-500' },
    pro: { label: 'Pro', icon: Zap, color: 'text-orange-500' },
    max: { label: 'Max', icon: Flame, color: 'text-red-500' }
  };

  const config = speedLabels[speedTier] || speedLabels.lite;
  const Icon = config.icon;

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-stone-100 border border-stone-200">
      <Icon className={`w-4 h-4 ${config.color}`} />
      <span className="text-sm font-medium text-stone-700">
        CrucibAI — {config.label}
      </span>
    </div>
  );
}
