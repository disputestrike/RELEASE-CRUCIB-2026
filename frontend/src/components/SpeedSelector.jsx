import React, { useState } from 'react';
import { Clock, Zap, Flame, ChevronDown, Lock } from 'lucide-react';

export default function SpeedSelector({ plan, selectedSpeed, onSpeedChange, userPlan }) {
  const [isOpen, setIsOpen] = useState(false);

  // Determine available speeds based on plan
  const getAvailableSpeeds = () => {
    const speedMap = {
      free: ['lite'],
      starter: ['lite', 'pro'],
      builder: ['lite', 'pro'],
      pro: ['lite', 'pro', 'max'],
      teams: ['lite', 'pro', 'max']
    };
    return speedMap[userPlan] || ['lite'];
  };

  const speedConfigs = {
    lite: {
      name: 'CrucibAI 1.0 Lite',
      description: 'A lightweight agent for everyday tasks.',
      time: '30-40s',
      multiplier: '1x',
      credits: '50',
      label: 'Sequential',
      icon: Clock,
      color: 'text-gray-500'
    },
    pro: {
      name: 'CrucibAI 1.0',
      description: 'Versatile agent capable of handling most tasks.',
      time: '12-16s',
      multiplier: '1.5x',
      credits: '100',
      label: 'Parallel',
      icon: Zap,
      color: 'text-orange-500',
      badge: 'POPULAR'
    },
    max: {
      name: 'CrucibAI 1.0 Max',
      description: 'High-performance agent designed for complex tasks.',
      time: '8-10s',
      multiplier: '2x',
      credits: '150',
      label: 'Full Swarm',
      icon: Flame,
      color: 'text-red-500',
      badge: 'FASTEST'
    }
  };

  const availableSpeeds = getAvailableSpeeds();
  const currentConfig = speedConfigs[selectedSpeed];
  const Icon = currentConfig?.icon || Clock;

  const isSpeedAvailable = (speed) => availableSpeeds.includes(speed);

  const getLockedMessage = (speed) => {
    if (speed === 'pro') {
      return 'Pro and Max speeds are available on paid plans only. Upgrade to Starter or higher.';
    }
    if (speed === 'max') {
      return 'Max speed is available on Pro and Teams plans only. Upgrade to Pro or higher.';
    }
    return 'This speed tier is not available on your plan.';
  };

  return (
    <div className="w-full">
      {/* Speed Selector Button */}
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full px-4 py-3 rounded-lg bg-white border border-stone-200 hover:border-stone-300 text-left flex items-center justify-between transition-colors"
        >
          <div className="flex items-center gap-3">
            <Icon className={`w-5 h-5 ${currentConfig?.color}`} />
            <div>
              <div className="text-sm font-medium text-stone-900">{currentConfig?.name}</div>
              <div className="text-xs text-stone-500">{currentConfig?.label}</div>
            </div>
          </div>
          <ChevronDown className={`w-5 h-5 text-stone-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {/* Dropdown Menu */}
        {isOpen && (
          <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-stone-200 rounded-lg shadow-lg z-50">
            {Object.entries(speedConfigs).map(([speedKey, config]) => {
              const available = isSpeedAvailable(speedKey);
              const Icon = config.icon;

              return (
                <div key={speedKey}>
                  {available ? (
                    <button
                      onClick={() => {
                        onSpeedChange(speedKey);
                        setIsOpen(false);
                      }}
                      className={`w-full px-4 py-3 text-left border-b border-stone-100 last:border-b-0 hover:bg-stone-50 transition-colors ${
                        selectedSpeed === speedKey ? 'bg-orange-50' : ''
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <Icon className={`w-5 h-5 ${config.color} mt-0.5 flex-shrink-0`} />
                        <div className="flex-1">
                          <div className="font-medium text-stone-900 flex items-center gap-2">
                            {config.name}
                            {config.badge && (
                              <span className="text-xs font-bold text-orange-600 bg-orange-100 px-2 py-0.5 rounded">
                                {config.badge}
                              </span>
                            )}
                            {selectedSpeed === speedKey && (
                              <span className="text-orange-600">✓</span>
                            )}
                          </div>
                          <div className="text-sm text-stone-600 mt-1">{config.description}</div>
                          <div className="flex gap-4 mt-2 text-xs text-stone-500">
                            <span>⏱ {config.time}</span>
                            <span>💾 {config.credits} credits</span>
                            <span>⚡ {config.multiplier}</span>
                          </div>
                        </div>
                      </div>
                    </button>
                  ) : (
                    <div className="px-4 py-3 border-b border-stone-100 last:border-b-0 bg-stone-50 opacity-60">
                      <div className="flex items-start gap-3">
                        <Lock className="w-5 h-5 text-stone-400 mt-0.5 flex-shrink-0" />
                        <div className="flex-1">
                          <div className="font-medium text-stone-600 flex items-center gap-2">
                            {config.name}
                            {config.badge && (
                              <span className="text-xs font-bold text-stone-400 bg-stone-200 px-2 py-0.5 rounded">
                                {config.badge}
                              </span>
                            )}
                          </div>
                          <div className="text-sm text-stone-500 mt-1">{config.description}</div>
                          <div className="text-xs text-stone-500 mt-2 italic">{getLockedMessage(speedKey)}</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Real-time Cost Estimate */}
      <div className="mt-3 p-3 bg-stone-50 rounded-lg border border-stone-200">
        <div className="text-xs text-stone-600">
          <span className="font-medium">Estimated cost:</span>
          <span className="ml-2">{currentConfig?.credits} credits per build</span>
        </div>
        <div className="text-xs text-stone-500 mt-1">
          Build time: {currentConfig?.time}
        </div>
      </div>

      {/* Close dropdown when clicking outside */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}
