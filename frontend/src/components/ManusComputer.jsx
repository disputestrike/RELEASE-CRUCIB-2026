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
            className="bg-zinc-900/90 border border-blue-500/50 rounded-lg p-4 w-80 shadow-2xl backdrop-blur-sm"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-blue-500/20">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-blue-400 animate-pulse" />
                <span className="text-blue-400 font-bold">Manus Computer</span>
              </div>
              <button
                onClick={() => setIsExpanded(false)}
                className="text-gray-500 hover:text-[#1A1A1A] transition-colors"
              >
                <ChevronUp className="w-4 h-4" />
              </button>
            </div>

            {/* Step Counter */}
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-[#666666]">Progress</span>
                <span className="text-blue-400 font-bold">
                  {currentStep} / {totalSteps}
                </span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${stepPercentage}%` }}
                  transition={{ duration: 0.5 }}
                  className="h-full bg-gradient-to-r from-blue-500 to-cyan-400"
                />
              </div>
            </div>

            {/* Token Counter */}
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-[#666666] flex items-center gap-1">
                  <Zap className="w-3 h-3" /> Tokens
                </span>
                <span className="text-yellow-400 font-bold">
                  {tokensUsed.toLocaleString()} / {tokensTotal.toLocaleString()}
                </span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${tokenPercentage}%` }}
                  transition={{ duration: 0.5 }}
                  className="h-full bg-gradient-to-r from-yellow-500 to-orange-400"
                />
              </div>
            </div>

            {/* Thinking Process */}
            {thinking && (
              <div className="mb-3">
                <div className="flex items-center gap-2 mb-2">
                  <Eye className="w-3 h-3 text-green-400 animate-pulse" />
                  <span className="text-[#666666]">Thinking</span>
                </div>
                <div className="bg-gray-900/50 border border-green-500/20 rounded p-2 min-h-12 max-h-24 overflow-y-auto">
                  <p className="text-green-400/80 text-xs leading-relaxed">
                    {displayThinking}
                    {displayThinking.length < thinking.length && (
                      <span className="animate-pulse">▌</span>
                    )}
                  </p>
                </div>
              </div>
            )}

            {/* Footer */}
            <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-800">
              Real-time agent orchestration
            </div>
          </motion.div>
        ) : (
          <motion.button
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            onClick={() => setIsExpanded(true)}
            className="bg-gradient-to-br from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 text-[#1A1A1A] rounded-full p-3 shadow-lg hover:shadow-xl transition-all flex items-center justify-center w-12 h-12 border border-blue-400/30"
          >
            <Cpu className="w-5 h-5 animate-pulse" />
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ManusComputer;
