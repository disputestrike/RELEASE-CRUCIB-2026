/**
 * Execution Target Selector Component
 * Intelligently shows/hides selector based on detection confidence
 * High confidence (>90%): Auto-confirm with single click
 * Low confidence (<70%): Show full selector with all options
 */

import React, { useEffect, useState } from 'react';
import useExecutionTargetDetection from '../../hooks/useExecutionTargetDetection';

const ExecutionTargetSelector = ({ userRequest, onTargetSelected, onConfirm }) => {
  const { detectTarget, targetSuggestion, loading, error, shouldShowSelector, shouldAutoConfirm } = useExecutionTargetDetection();
  const [selectedTarget, setSelectedTarget] = useState(null);

  // Auto-detect target when request changes
  useEffect(() => {
    if (userRequest && userRequest.trim().length > 10) {
      detectTarget(userRequest);
    }
  }, [userRequest, detectTarget]);

  // Auto-confirm if confidence > 90%
  useEffect(() => {
    if (targetSuggestion && shouldAutoConfirm(targetSuggestion)) {
      setSelectedTarget(targetSuggestion.primary_target);
      onConfirm?.(targetSuggestion.primary_target);
    }
  }, [targetSuggestion, shouldAutoConfirm, onConfirm]);

  const targets = [
    {
      id: 'fullstack-web',
      name: 'Full-stack Web',
      description: 'Vite + React + Node.js API',
      icon: '🌐'
    },
    {
      id: 'nextjs-app',
      name: 'Next.js App Router',
      description: 'Server-side rendering',
      icon: '▲'
    },
    {
      id: 'marketing-static',
      name: 'Marketing/Static',
      description: 'HTML/CSS/JS only',
      icon: '📄'
    },
    {
      id: 'api-backend-first',
      name: 'API & Backend',
      description: 'FastAPI/Node.js backend',
      icon: '⚙️'
    },
    {
      id: 'agents-automation',
      name: 'Agents & Automation',
      description: 'Intelligent workflows',
      icon: '🤖'
    }
  ];

  // Loading state
  if (loading) {
    return (
      <div className="p-4 border border-gray-300 rounded-lg bg-blue-50">
        <p className="text-sm text-gray-600">Analyzing your request...</p>
        <div className="mt-2 h-2 bg-gray-200 rounded">
          <div className="h-full bg-blue-500 rounded animate-pulse" style={{ width: '60%' }}></div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-4 border border-red-300 rounded-lg bg-red-50">
        <p className="text-sm text-red-600">⚠️ Could not analyze request: {error}</p>
        <p className="text-xs text-gray-500 mt-2">Please select a target manually below</p>
      </div>
    );
  }

  // High confidence - auto-confirmed (show confirmation only)
  if (targetSuggestion && shouldAutoConfirm(targetSuggestion)) {
    const suggested = targets.find(t => t.id === targetSuggestion.primary_target);
    return (
      <div className="p-4 border border-green-300 rounded-lg bg-green-50">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-green-900">✅ Ready to build</p>
            <p className="text-sm text-green-800 mt-1">
              {suggested?.icon} {suggested?.name}
            </p>
            <p className="text-xs text-green-700 mt-1">{targetSuggestion.reasoning}</p>
            {targetSuggestion.secondary_targets?.length > 0 && (
              <p className="text-xs text-gray-600 mt-2">
                + {targetSuggestion.secondary_targets.length} secondary target(s) available
              </p>
            )}
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-green-600">{Math.round(targetSuggestion.confidence)}%</div>
            <button
              onClick={() => onTargetSelected?.(targetSuggestion)}
              className="mt-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
            >
              Confirm
            </button>
            <button
              onClick={() => setSelectedTarget(null)}
              className="mt-2 ml-2 px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300 text-sm"
            >
              Adjust
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Medium-low confidence - show selector
  if (shouldShowSelector(targetSuggestion)) {
    return (
      <div className="space-y-3">
        {targetSuggestion && (
          <div className="p-3 border border-yellow-300 rounded-lg bg-yellow-50">
            <p className="text-sm text-yellow-900">
              <span className="font-semibold">{Math.round(targetSuggestion.confidence)}% confident:</span> {targetSuggestion.reasoning}
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-2">
          {targets.map(target => (
            <button
              key={target.id}
              onClick={() => {
                setSelectedTarget(target.id);
                onTargetSelected?.({
                  primary_target: target.id,
                  confidence: targetSuggestion?.confidence || 50,
                });
              }}
              className={`p-3 border-2 rounded-lg text-left transition ${
                selectedTarget === target.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center">
                <span className="text-lg mr-2">{target.icon}</span>
                <div className="flex-1">
                  <p className="font-semibold text-sm">{target.name}</p>
                  <p className="text-xs text-gray-600">{target.description}</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  // Fallback - no suggestion, show all targets
  return (
    <div className="grid grid-cols-1 gap-2">
      <p className="text-sm text-gray-600 mb-2">Select an execution target:</p>
      {targets.map(target => (
        <button
          key={target.id}
          onClick={() => {
            setSelectedTarget(target.id);
            onTargetSelected?.({
              primary_target: target.id,
              confidence: 50,
            });
          }}
          className={`p-3 border-2 rounded-lg text-left transition ${
            selectedTarget === target.id
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-200 hover:border-gray-300'
          }`}
        >
          <div className="flex items-center">
            <span className="text-lg mr-2">{target.icon}</span>
            <div className="flex-1">
              <p className="font-semibold text-sm">{target.name}</p>
              <p className="text-xs text-gray-600">{target.description}</p>
            </div>
          </div>
        </button>
      ))}
    </div>
  );
};

export default ExecutionTargetSelector;
