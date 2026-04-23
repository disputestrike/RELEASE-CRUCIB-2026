import React from 'react';
import { Flame, Clock, Zap } from 'lucide-react';

export default function SpeedProgressBar({ speedTier, progress, isBuilding }) {
  const speedConfigs = {
    lite: {
      label: 'Lite Mode — Cerebras sequential',
      flames: 1,
      color: 'text-gray-500',
      bgColor: 'bg-gray-100'
    },
    pro: {
      label: 'Pro Mode — Haiku parallel',
      flames: 2,
      color: 'text-orange-500',
      bgColor: 'bg-orange-100'
    },
    max: {
      label: 'Max Mode — Haiku full swarm — all 123 agents',
      flames: 3,
      color: 'text-red-500',
      bgColor: 'bg-red-100'
    }
  };

  const config = speedConfigs[speedTier] || speedConfigs.lite;

  return (
    <div className="w-full space-y-2">
      {/* Speed Mode Label */}
      <div className="flex items-center gap-2">
        {speedTier === 'lite' && <Clock className={`w-4 h-4 ${config.color}`} />}
        {speedTier === 'pro' && <Zap className={`w-4 h-4 ${config.color}`} />}
        {speedTier === 'max' && <Flame className={`w-4 h-4 ${config.color}`} />}
        <span className="text-sm font-medium text-stone-700">{config.label}</span>
      </div>

      {/* Flame Count Indicator */}
      <div className="flex gap-1">
        {[1, 2, 3].map((flame) => (
          <Flame
            key={flame}
            className={`w-4 h-4 ${
              flame <= config.flames ? config.color : 'text-stone-300'
            }`}
            fill={flame <= config.flames ? 'currentColor' : 'none'}
          />
        ))}
      </div>

      {/* Progress Bar */}
      <div className={`w-full h-2 rounded-full ${config.bgColor} overflow-hidden`}>
        <div
          className={`h-full transition-all duration-300 ${
            speedTier === 'lite' ? 'bg-gray-500' :
            speedTier === 'pro' ? 'bg-orange-500' :
            'bg-red-500'
          }`}
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>

      {/* Progress Text */}
      {isBuilding && (
        <div className="text-xs text-stone-600">
          Building... {Math.round(progress)}%
        </div>
      )}
    </div>
  );
}
