import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Cpu, Zap, Eye } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * ManusComputer Widget
 * 
 * A small, expandable widget that shows:
 * - Current step counter (e.g., "Step 3 of 7")
 * - Thinking process (agent reasoning in real-time)
 * - Token consumption (real-time tracker)
 * 
 * Non-intrusive design - sits in bottom-right corner
 * Minimal footprint when collapsed
 */
const ManusComputer = ({ 
  currentStep = 0, 
  totalSteps = 0, 
  thinking = "", 
  tokensUsed = 0, 
  tokensTotal = 0,
  isActive = false 
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [displayThinking, setDisplayThinking] = useState("");

  // Simulate thinking text streaming effect
  useEffect(() => {
    if (thinking && thinking !== displayThinking) {
      const timer = setTimeout(() => {
        setDisplayThinking(thinking.substring(0, displayThinking.length + 1));
      }, 20);
      return () => clearTimeout(timer);
    }
  }, [thinking, displayThinking]);

  const tokenPercentage = tokensTotal > 0 ? (tokensUsed / tokensTotal) * 100 : 0;
  const stepPercentage = totalSteps > 0 ? (currentStep / totalSteps) * 100 : 0;

  // Only show if active (processing)
  if (!isActive && currentStep === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-6 right-6 z-40 font-mono text-xs">
      <AnimatePresence>
        {isExpanded ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ duration: 0.2 }}
            className="bg-white border border-gray-300 rounded-lg p-4 w-80 shadow-2xl backdrop-blur-sm"
          >
            {/* Header */}
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-300">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-black animate-pulse" />
                <span className="text-black font-bold">Manus Computer</span>
              </div>
              <button
                onClick={() => setIsExpanded(false)}
                className="text-gray-600 hover:text-black transition-colors"
              >
                <ChevronUp className="w-4 h-4" />
              </button>
            </div>

            {/* Step Counter */}
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-600">Progress</span>
                <span className="text-black font-bold">
                  {currentStep} / {totalSteps}
                </span>
              </div>
              <div className="w-full bg-gray-300 rounded-full h-2 overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${stepPercentage}%` }}
                  transition={{ duration: 0.5 }}
                  className="h-full bg-gradient-to-r from-black to-gray-700"
                />
              </div>
            </div>

            {/* Token Counter */}
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-600 flex items-center gap-1">
                  <Zap className="w-3 h-3" /> Tokens
                </span>
                <span className="text-gray-800 font-bold">
                  {tokensUsed.toLocaleString()} / {tokensTotal.toLocaleString()}
                </span>
              </div>
              <div className="w-full bg-gray-300 rounded-full h-2 overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${tokenPercentage}%` }}
                  transition={{ duration: 0.5 }}
                  className="h-full bg-gradient-to-r from-gray-700 to-black"
                />
              </div>
            </div>

            {/* Thinking Process */}
            {thinking && (
              <div className="mb-3">
                <div className="flex items-center gap-2 mb-2">
                  <Eye className="w-3 h-3 text-gray-700 animate-pulse" />
                  <span className="text-gray-600">Thinking</span>
                </div>
                <div className="bg-gray-100 border border-gray-400 rounded p-2 min-h-12 max-h-24 overflow-y-auto">
                  <p className="text-gray-800 text-xs leading-relaxed">
                    {displayThinking}
                    {displayThinking.length < thinking.length && (
                      <span className="animate-pulse">▌</span>
                    )}
                  </p>
                </div>
              </div>
            )}

            {/* Footer */}
            <div className="text-xs text-gray-600 text-center pt-2 border-t border-gray-300">
              Real-time agent orchestration
            </div>
          </motion.div>
        ) : (
          <motion.button
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            onClick={() => setIsExpanded(true)}
            className="bg-gradient-to-br from-black to-gray-800 hover:from-gray-900 hover:to-black text-white rounded-full p-3 shadow-lg hover:shadow-xl transition-all flex items-center justify-center w-12 h-12 border border-gray-600"
          >
            <Cpu className="w-5 h-5 animate-pulse text-white" />
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ManusComputer;
